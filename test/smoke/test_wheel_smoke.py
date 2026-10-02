"""Stdlib smoke harness; Docker copies it outside the checkout to test the installed wheel."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

SMOKE_DIRECTORY = Path(__file__).resolve().parent
PROCESS_TIMEOUT_SECONDS = 45


class WheelSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="loaddensity-smoke-")
        cls.directory = Path(cls.temporary.name)
        cls.environment = os.environ.copy()
        source = SMOKE_DIRECTORY.parents[1]
        if (source / "je_load_density").is_dir():
            cls.environment["PYTHONPATH"] = str(source) + os.pathsep + cls.environment.get("PYTHONPATH", "")
        ready = cls.directory / "ready.json"
        cls.server = subprocess.Popen(
            [sys.executable, str(SMOKE_DIRECTORY / "server.py"), str(ready)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=cls.directory,
        )
        deadline = time.monotonic() + 10
        while not ready.exists() and cls.server.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if not ready.exists():
            cls.tearDownClass()
            raise RuntimeError("Local smoke server did not become ready")
        cls.url = f"http://127.0.0.1:{json.loads(ready.read_text(encoding='utf-8'))['port']}"

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "url") and cls.server.poll() is None:
            try:
                with urlopen(Request(cls.url + "/shutdown", method="POST"), timeout=2):
                    pass
            except (URLError, OSError):
                cls.server.terminate()
        elif cls.server.poll() is None:
            cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait(timeout=5)
        cls.temporary.cleanup()

    def command(self, *arguments: str, input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, *arguments], input=input_text, capture_output=True, text=True,
            encoding="utf-8", errors="replace", env=self.environment, cwd=self.directory,
            timeout=PROCESS_TIMEOUT_SECONDS, check=False,
        )

    def actions(self, endpoint: str, *, failed_gate: bool = False) -> list[list[object]]:
        definitions = [
            {"LD_start_test": {"user_detail_dict": {"user": "http_user"}, "user_count": 1,
                               "spawn_rate": 10, "test_time": 3,
                               "tasks": {"get": {"request_url": self.url + endpoint}}}},
            {"LD_generate_summary_report": {"report_name": "summary"}},
            {"LD_generate_json_report": {"json_file_name": "records"}},
            {"LD_generate_junit_report": {"report_name": "junit"}},
            {"LD_persist_records": {"database_path": "records.sqlite"}},
            {"LD_assert_sla": {"rules": [{"type": "failure_rate", "op": "lte", "value": 0},
                                        {"type": "requests", "op": "gte",
                                         "value": 1000000 if failed_gate else 1}]}},
        ]
        return [[name, parameters] for definition in definitions for name, parameters in definition.items()]

    def execute_actions(self, actions: list[list[object]], *, legacy: bool = False) -> subprocess.CompletedProcess:
        path = self.directory / "actions.json"
        path.write_text(json.dumps({"load_density": actions}), encoding="utf-8")
        return self.command("-m", "je_load_density", "--execute_file" if legacy else "run", str(path))

    def test_cli_load_reports_sqlite_and_passing_sla(self) -> None:
        result = self.execute_actions(self.actions("/ok"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads((self.directory / "summary.json").read_text(encoding="utf-8"))
        self.assertGreater(summary["totals"]["requests"], 0, result.stdout + result.stderr)
        self.assertEqual(summary["totals"]["failures"], 0)
        self.assertIn("p95_ms", summary["latency_overall"])
        records = json.loads((self.directory / "records_success.json").read_text(encoding="utf-8"))
        self.assertGreater(len(records), 0)
        suite = ElementTree.parse(self.directory / "junit.xml").getroot()
        self.assertGreater(int(suite.attrib["tests"]), 0)
        with closing(sqlite3.connect(self.directory / "records.sqlite")) as connection:
            self.assertGreater(connection.execute("SELECT COUNT(*) FROM load_density_records").fetchone()[0], 0)

    def test_legacy_cli_and_failed_sla_signal_failure(self) -> None:
        result = self.execute_actions(self.actions("/fail"), legacy=True)
        self.assertNotEqual(result.returncode, 0, "A failed SLA gate must fail the CLI process")
        summary = json.loads((self.directory / "summary.json").read_text(encoding="utf-8"))
        self.assertGreater(summary["totals"]["failures"], 0)

    def test_failed_gate_on_successful_requests_signals_failure(self) -> None:
        result = self.execute_actions(self.actions("/ok", failed_gate=True))
        self.assertNotEqual(result.returncode, 0, "A failed capacity gate must fail the CLI process")

    def test_mcp_handshake(self) -> None:
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                              "clientInfo": {"name": "smoke", "version": "1"}}}
        result = self.command("-m", "je_load_density.mcp_server", input_text=json.dumps(request) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout.splitlines()[0])
        self.assertEqual(response["id"], 1)
        self.assertIn("protocolVersion", response["result"])

    def test_async_bench_executes_real_requests(self) -> None:
        result = self.command("-m", "je_load_density", "bench", self.url + "/ok",
                              "--users", "1", "--duration", "0.25")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(result.stdout)
        self.assertGreater(summary["totals"]["requests"], 0)
        self.assertEqual(summary["totals"]["failures"], 0)

    def test_dashboard_json_and_sse(self) -> None:
        result = self.command(str(SMOKE_DIRECTORY / "dashboard_probe.py"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["content_type"], "text/event-stream")
        self.assertEqual(output["snapshot"]["totals"]["requests"], 1)
        self.assertEqual(output["event"]["totals"]["requests"], 1)


if __name__ == "__main__":
    unittest.main()

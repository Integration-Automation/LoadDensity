"""
One-liner benchmark CLI::

    loaddensity bench https://api/x --rps 100 --duration 30
    loaddensity bench https://api/x --users 50 --duration 30 --http2
"""

import argparse
import asyncio
import json
import sys
from typing import List, Optional

from je_load_density.engine.asyncio_engine import run_async_load
from je_load_density.utils.generate_report.generate_summary_report import build_summary


def _build_tasks(url: str, method: str, body: Optional[str]) -> List[dict]:
    task = {"method": method, "request_url": url}
    if body:
        try:
            task["json"] = json.loads(body)
        except json.JSONDecodeError:
            task["json"] = body
    return [task]


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="loaddensity bench")
    parser.add_argument("url")
    parser.add_argument("--method", default="get")
    parser.add_argument("--body", default=None)
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--http2", action="store_true")
    parser.add_argument("--max-in-flight", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    asyncio.run(run_async_load(
        tasks=_build_tasks(args.url, args.method, args.body),
        users=args.users,
        duration_seconds=args.duration,
        http2=args.http2,
        max_in_flight=args.max_in_flight,
    ))
    summary = build_summary()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

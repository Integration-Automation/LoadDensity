import json
import re
import shutil
import subprocess

import pytest

from je_load_density.utils.dashboard.live_dashboard import _HTML


def test_dashboard_renders_bands_and_untrusted_names_as_text():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for browser-script DOM contract checks")
    script = re.search(r"<script>(.*?)</script>", _HTML, re.DOTALL).group(1)
    harness = r"""
const vm = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
class Element {
  constructor(tag='div') { this.tag=tag; this.children=[]; this.attributes={}; this.textContent=''; }
  set innerHTML(_) { throw Error('Dynamic innerHTML is forbidden'); }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...items) { this.children=items; }
  setAttribute(name, value) { this.attributes[name]=String(value); }
}
const nodes={};
const document={getElementById:id=>(nodes[id]??=new Element()),
  createElement:tag=>new Element(tag), createElementNS:(_,tag)=>new Element(tag)};
let source;
class EventSource { constructor() { source=this; } }
const context=vm.createContext({document,EventSource,Date,console});
vm.runInContext(input.script,context);
source.onopen();
source.onmessage({data:JSON.stringify(input.data)});
console.log(JSON.stringify({name:nodes.tbody.children[0].children[0].textContent,
  bands:nodes.latency.children.filter(n=>n.attributes['data-band']).length,
  status:nodes.connection.textContent, failure:nodes.failures.textContent}));
"""
    name = '<img src="x" onerror="throw Error(1)">'
    window = {"duration_seconds": 1, "count": 1, "rps": 1, "p50_ms": 10, "p95_ms": 20, "p99_ms": 30}
    data = {"totals": {"requests": 3, "failures": 1, "failure_rate": 1 / 3},
            "rps": 0.3, "avg_ms": 20, "ts": 100,
            "latency_overall": {"p50_ms": 10, "p95_ms": 20, "p99_ms": 30},
            "per_name": {name: {"count": 3, "mean_ms": 20, "p95_ms": 20}},
            "latency_windows": [{**window, "start_time": 0},
                                {**window, "start_time": 1, "p50_ms": None, "p95_ms": None, "p99_ms": None},
                                {**window, "start_time": 2}]}
    completed = subprocess.run([node, "-e", harness], input=json.dumps({"script": script, "data": data}),
                               text=True, encoding="utf-8", capture_output=True, timeout=10, check=False)
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output == {"name": name, "bands": 4, "status": "Connected", "failure": "1"}

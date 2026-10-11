"""Responsive telemetry page with bounded SVG bands and text-only dynamic names."""

HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LoadDensity Live</title><style>
:root{color-scheme:dark;--bg:#0b1220;--panel:#121d30;--line:#26364e;--text:#e5edf8;--muted:#95a7bf;--blue:#38bdf8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui,sans-serif}
main{max-width:1440px;margin:auto;padding:32px}header{display:flex;align-items:center;justify-content:space-between;gap:16px}
h1{font-size:28px;letter-spacing:-1px;margin:0}h2{font-size:16px;margin:0 0 16px}p{color:var(--muted);margin:8px 0 24px}
.eyebrow{color:var(--blue);font-size:11px;letter-spacing:2px;font-weight:700;margin-bottom:8px}
.badge{padding:8px 12px;border:1px solid var(--line);border-radius:20px;color:var(--muted);white-space:nowrap}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:12px;margin:24px 0}
.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px}
.label{font-size:12px;color:var(--muted)}.value{font-size:30px;font-variant-numeric:tabular-nums;margin-top:8px;font-weight:650}
.value small{font-size:12px;color:var(--muted);font-weight:400}.danger{color:#fb7185}
.charts{display:grid;grid-template-columns:2fr 1fr;gap:16px;margin-bottom:16px}
svg{display:block;width:100%;height:240px}.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.legend span:before{content:'';display:inline-block;width:10px;height:10px;background:var(--blue);
margin-right:6px;border-radius:2px}
.legend .middle:before{background:#38bdf866}.legend .tail:before{background:#a78bfa55}
.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--muted);font-weight:500;text-align:left}th,td{padding:12px 8px;border-bottom:1px solid var(--line)}
td:first-child{overflow-wrap:anywhere;max-width:650px}th:not(:first-child),td:not(:first-child){text-align:right}
.footnote{font-size:12px;color:var(--muted);margin:16px 0 0}
@media(max-width:850px){main{padding:20px}.charts{grid-template-columns:1fr}header{align-items:flex-start}h1{font-size:24px}}
@media(max-width:480px){main{padding:12px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.card{padding:14px}}
</style></head><body><main>
<header><div><div class="eyebrow">LOADDENSITY / OBSERVABILITY</div><h1>Live performance</h1></div>
<span class="badge" id="connection" role="status">Connecting…</span></header>
<p>Capacity, latency and failures from the current record stream.</p>
<section class="metrics" aria-label="Run metrics">
<div class="card"><div class="label">Requests</div><div class="value" id="total">0</div></div>
<div class="card"><div class="label">Recent throughput</div>
<div class="value"><span id="rps">0</span> <small>req/s</small></div></div>
<div class="card"><div class="label">Failure rate</div><div class="value danger" id="failure-rate">0%</div></div>
<div class="card"><div class="label">Overall p50</div>
<div class="value"><span id="p50">0</span> <small>ms</small></div></div>
<div class="card"><div class="label">Overall p95</div>
<div class="value"><span id="p95">0</span> <small>ms</small></div></div>
<div class="card"><div class="label">Overall p99</div>
<div class="value"><span id="p99">0</span> <small>ms</small></div></div>
<div class="card"><div class="label">Failures</div><div class="value danger" id="failures">0</div></div>
</section>
<section class="charts" aria-label="Performance charts">
<div class="panel"><h2>Latency distribution <small>· milliseconds</small></h2>
<svg id="latency" viewBox="0 0 800 240" role="img" aria-label="p50 line with p50 to p95 and p95 to p99 bands"></svg>
<div class="legend"><span>p50</span><span class="middle">p50–p95</span><span class="tail">p95–p99</span></div></div>
<div class="panel"><h2>Throughput <small>· requests / second</small></h2>
<svg id="throughput" viewBox="0 0 800 240" role="img" aria-label="Request rate over time"></svg>
<div class="footnote">Each bucket uses its actual duration. Empty latency windows remain disconnected.</div></div>
</section>
<section class="panel"><h2>Request groups</h2><div class="table-wrap">
<table><thead><tr><th scope="col">Name</th><th scope="col">Count</th><th scope="col">Mean ms</th>
<th scope="col">p95 ms</th></tr></thead><tbody id="tbody"></tbody></table></div>
<div class="footnote">Group statistics cover successful requests. Showing up to 100 groups.</div></section>
<p class="footnote">Recent one-second windows include successful and failed requests. Empty windows are gaps.
<span id="updated"></span></p>
<script>
const es = new EventSource('/events');
const put = (id, value) => { document.getElementById(id).textContent = String(value); };
es.onopen = () => put('connection', 'Connected');
es.onerror = () => put('connection', 'Reconnecting…');
const numeric = value => typeof value === 'number' && Number.isFinite(value);
function element(tag, attributes, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function segments(windows) {
  const chunks = []; let current = [];
  for (const sample of windows) {
    if (numeric(sample.p50_ms) && numeric(sample.p95_ms) && numeric(sample.p99_ms)) current.push(sample);
    else if (current.length) { chunks.push(current); current = []; }
  }
  if (current.length) chunks.push(current);
  return chunks;
}
function axes(svg, maximum, span, width) {
  for (let tick = 0; tick <= 3; tick++) {
    const y = 202 - tick * 58;
    svg.appendChild(element('line', {x1:58,y1:y,x2:width-14,y2:y,stroke:'#26364e'}));
    svg.appendChild(element('text', {x:48,y:y+4,fill:'#95a7bf','font-size':12,'text-anchor':'end'},
      (maximum * tick / 3).toFixed(maximum < 10 ? 1 : 0)));
  }
  svg.appendChild(element('text', {x:58,y:230,fill:'#95a7bf','font-size':12}, `${span.toFixed(0)}s ago`));
  svg.appendChild(element('text', {x:width-14,y:230,fill:'#95a7bf','font-size':12,'text-anchor':'end'}, 'now'));
}
function chart(id, windows, latency) {
  const svg = document.getElementById(id); svg.replaceChildren();
  if (!windows.length) return;
  const width = Math.max(280, svg.clientWidth || 800);
  svg.setAttribute('viewBox', `0 0 ${width} 240`);
  const first = windows[0].start_time;
  const last = windows[windows.length-1];
  const span = Math.max(1, last.start_time + last.duration_seconds - first);
  const maximum = Math.max(1, ...windows.map(w => latency ? (w.p99_ms ?? 0) : w.rps)) * 1.1;
  const point = (w, key) => `${58 + (w.start_time-first)/span*(width-72)},${202-w[key]/maximum*174}`;
  axes(svg, maximum, span, width);
  const chunks = latency ? segments(windows) : [windows];
  for (const chunk of chunks) {
    if (latency) {
      for (const [low,high,color] of [['p50_ms','p95_ms','#38bdf866'],['p95_ms','p99_ms','#a78bfa55']]) {
        const points = [...chunk.map(w => point(w,low)), ...[...chunk].reverse().map(w => point(w,high))];
        svg.appendChild(element('polygon', {points:points.join(' '),fill:color,'data-band':`${low}-${high}`}));
      }
    }
    const key = latency ? 'p50_ms' : 'rps';
    const points = chunk.map(w => point(w,key)).join(' ');
    svg.appendChild(element('polyline', {points,fill:'none',stroke:'#38bdf8','stroke-width':2}));
    if (chunk.length === 1) {
      const [cx,cy] = point(chunk[0],key).split(',');
      svg.appendChild(element('circle', {cx,cy,r:3,fill:'#38bdf8'}));
    }
  }
}
function groups(values) {
  const tbody = document.getElementById('tbody'); tbody.replaceChildren();
  for (const [name, stats] of Object.entries(values).slice(0,100)) {
    const row = document.createElement('tr');
    for (const value of [name,stats.count,stats.mean_ms.toFixed(1),stats.p95_ms.toFixed(1)]) {
      const cell = document.createElement('td'); cell.textContent = String(value); row.appendChild(cell);
    }
    tbody.appendChild(row);
  }
}
es.onmessage = event => {
  const data = JSON.parse(event.data);
  put('total', data.totals.requests); put('failures', data.totals.failures);
  put('failure-rate', (data.totals.failure_rate*100).toFixed(1) + '%'); put('rps', data.rps.toFixed(1));
  for (const key of ['p50','p95','p99']) put(key, data.latency_overall[key + '_ms'].toFixed(0));
  chart('latency', data.latency_windows ?? [], true); chart('throughput', data.latency_windows ?? [], false);
  groups(data.per_name); put('updated', 'Updated ' + new Date(data.ts*1000).toLocaleTimeString());
};
</script></main></body></html>
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import json
from collections import defaultdict

LOG = Path("logs/monitoring.jsonl")

# Only show the two endpoints currently monitored.
CURRENT_TARGETS = {"Test Service 2", "Web Service Test"}

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Network Operations Dashboard</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1120;color:#e5edf8;font:15px Arial,sans-serif}
header{padding:26px 5%;background:#111c30;border-bottom:1px solid #26344c}
h1{margin:0 0 8px;font-size:25px}header p{color:#9fb0c9;margin:0}
main{max-width:1200px;margin:28px auto;padding:0 20px}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.card,.panel{background:#121e32;border:1px solid #27364e;border-radius:12px;padding:20px}
.label{font-size:13px;color:#9fb0c9}.value{font-size:29px;font-weight:bold;margin-top:12px}
h2{font-size:18px;margin:0 0 18px}.panel{margin-top:20px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:13px 9px;border-bottom:1px solid #27364e}
th{color:#9fb0c9;font-size:12px;text-transform:uppercase}
.pill{display:inline-block;border-radius:20px;padding:5px 10px;font-size:12px;font-weight:bold}
.UP{background:#123c32;color:#6ee7b7}.DOWN{background:#48242e;color:#fda4af}
small,.muted{color:#9fb0c9}canvas{width:100%;height:220px;display:block}
#events{line-height:1.9;overflow-wrap:anywhere}.incident{padding:10px 0;border-bottom:1px solid #27364e}
footer{padding:25px;color:#9fb0c9;text-align:center;font-size:12px}
@media(max-width:750px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:0 12px}.card,.panel{padding:14px}table{font-size:12px}}
</style>
</head>
<body>
<header><h1>Network Operations Dashboard</h1>
<p>Network Monitoring &amp; Incident Detection · Live local monitoring</p></header>
<main>
<div class="cards">
<div class="card"><div class="label">Monitored Endpoints</div><div class="value" id="total">—</div></div>
<div class="card"><div class="label">Endpoints UP / Total</div><div class="value" id="up">—</div></div>
<div class="card"><div class="label">Active Incidents</div><div class="value" id="active">—</div></div>
<div class="card"><div class="label">Average TCP Connect Time</div><div class="value" id="latency">—</div></div>
</div>
<section class="panel"><h2>Endpoint Health</h2>
<table><thead><tr><th>Endpoint</th><th>Address</th><th>Status</th><th>Connect time</th><th>Last checked</th></tr></thead>
<tbody id="targets"><tr><td colspan="5">Waiting for monitoring data…</td></tr></tbody></table></section>
<section class="panel"><h2>Response Time History</h2><canvas id="chart" width="1000" height="240"></canvas><small>Recent successful TCP connection checks; time shown in milliseconds.</small></section>
<section class="panel"><h2>Incident &amp; Recovery History</h2><div id="events" class="muted">No recorded events yet.</div></section>
<p class="muted">Refreshes automatically every 3 seconds. Availability is calculated from checks recorded during the current log history.</p>
</main><footer>Network Monitoring &amp; Incident Detection System · Local demonstration</footer>
<script>
function formatTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

async function refresh() {
  try {
    const r = await fetch('/api', {cache: 'no-store'});
    if (!r.ok) throw new Error('API returned HTTP ' + r.status);
    const d = await r.json();

    document.getElementById('total').textContent = d.targets.length;
    document.getElementById('up').textContent =
      d.targets.filter(t => t.status === 'UP').length + ' / ' + d.targets.length;
    document.getElementById('active').textContent = d.active;

    const vals = d.targets
      .filter(t => t.status === 'UP' && Number.isFinite(t.latency_ms))
      .map(t => t.latency_ms);

    document.getElementById('latency').textContent = vals.length
      ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2) + ' ms'
      : '—';

    document.getElementById('targets').innerHTML = d.targets.map(t =>
      `<tr><td>${t.name}</td><td>${t.host}:${t.port}</td>
      <td><span class="pill ${t.status}">${t.status}</span></td>
      <td>${t.latency_ms == null ? '—' : t.latency_ms + ' ms'}</td>
      <td>${formatTime(t.timestamp)}</td></tr>`
    ).join('') ||
      '<tr><td colspan="5">Waiting for monitoring data…</td></tr>';

    document.getElementById('events').innerHTML = d.events.length
      ? d.events.map(e =>
        `<div class="incident"><b>${e.event}</b> · ${e.name} · ${e.status}
        <br><small>${formatTime(e.timestamp)}</small></div>`
      ).join('')
      : 'No recorded incidents or recovery events yet.';

    draw(d.history);
  } catch (e) {
    document.getElementById('events').textContent =
      'Dashboard update error: ' + e.message;
  }
}

function draw(history) {
  const c = document.getElementById('chart');
  const x = c.getContext('2d'), w = c.width, h = c.height;
  x.clearRect(0, 0, w, h);

  const left = 78, right = 25, top = 38, bottom = 55;
  const pw = w - left - right, ph = h - top - bottom;
  const series = Object.entries(history);
  const colors = ['#6ee7b7', '#93c5fd', '#fbbf24', '#c4b5fd'];

  x.font = '13px Arial';
  x.fillStyle = '#e5edf9';
  x.textAlign = 'left';
  x.fillText('TCP connection time by service', left, 19);

  const all = series.flatMap(([name, values]) =>
    values.map(v => v.latency_ms).filter(v => Number.isFinite(v))
  );

  if (!all.length) {
    x.fillStyle = '#9fb0c9';
    x.fillText('Waiting for successful connection checks…', left, top + ph / 2);
    return;
  }

  const max = Math.max(10, ...all) * 1.15;
  x.font = '12px Arial';
  x.textAlign = 'right';
  x.textBaseline = 'middle';

  for (let i = 0; i <= 4; i++) {
    const value = max * (1 - i / 4);
    const y = top + i * ph / 4;
    x.strokeStyle = '#293851';
    x.beginPath();
    x.moveTo(left, y);
    x.lineTo(w - right, y);
    x.stroke();
    x.fillStyle = '#c2cee0';
    x.fillText(value.toFixed(1), left - 10, y);
  }

  x.strokeStyle = '#8191aa';
  x.beginPath();
  x.moveTo(left, top);
  x.lineTo(left, top + ph);
  x.lineTo(w - right, top + ph);
  x.stroke();

  const maxSamples = Math.max(1, ...series.map(([name, values]) => values.length));
  [0, Math.floor((maxSamples - 1) / 2), maxSamples - 1]
    .filter((v, i, a) => a.indexOf(v) === i)
    .forEach(i => {
      const px = left + (maxSamples < 2 ? 0 : i * pw / (maxSamples - 1));
      x.fillStyle = '#c2cee0';
      x.textAlign = 'center';
      x.textBaseline = 'top';
      x.fillText(String(i + 1), px, top + ph + 7);
    });

  x.save();
  x.translate(19, top + ph / 2);
  x.rotate(-Math.PI / 2);
  x.fillStyle = '#e5edf9';
  x.textAlign = 'center';
  x.textBaseline = 'middle';
  x.fillText('TCP connect time (ms)', 0, 0);
  x.restore();

  x.fillStyle = '#e5edf9';
  x.textAlign = 'center';
  x.textBaseline = 'top';
  x.fillText('Check number (oldest → newest)', left + pw / 2, h - 20);

  series.forEach(([name, values], idx) => {
    const color = colors[idx % colors.length];
    x.strokeStyle = color;
    x.lineWidth = 2;
    x.beginPath();
    let started = false;

    values.forEach((v, i) => {
      if (!Number.isFinite(v.latency_ms)) return;
      const px = left + (maxSamples < 2 ? 0 : i * pw / (maxSamples - 1));
      const py = top + ph * (1 - v.latency_ms / max);
      if (!started) {
        x.moveTo(px, py);
        started = true;
      } else {
        x.lineTo(px, py);
      }
    });
    x.stroke();

    const legendY = top + idx * 18;
    x.fillStyle = color;
    x.fillRect(left + pw - 210, legendY - 7, 12, 3);
    x.fillStyle = '#e5edf9';
    x.textAlign = 'left';
    x.textBaseline = 'middle';
    x.fillText(name, left + pw - 192, legendY);
  });
}

refresh();
setInterval(refresh, 3000);
</script>
</body></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api":
            rows = []
            if LOG.exists():
                for line in LOG.read_text().splitlines():
                    try: rows.append(json.loads(line))
                    except json.JSONDecodeError: pass
            latest, history, state, events = {}, defaultdict(list), {}, []
            for e in rows:
                name = e.get("name", "Unknown")

                # Keep historical records, but hide obsolete endpoints
                # from the current dashboard.
                if name not in CURRENT_TARGETS:
                    continue

                if e.get("status") in ("UP", "DOWN"):
                    latest[name] = e
                    state[name] = e["status"]
                    if e["status"] == "UP" and e.get("latency_ms") is not None:
                        history[name].append({"latency_ms": e["latency_ms"]})
                        history[name] = history[name][-30:]
                if e.get("event") in ("INCIDENT", "RECOVERY"):
                    events.append(e)
            active = sum(1 for name, status in state.items() if status == "DOWN")
            data = {"targets": list(latest.values()), "history": dict(history),
                    "events": events[::-1][:20], "active": active}
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/" or self.path.startswith("/?"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)
    def log_message(self, *args): pass

print("Dashboard available at http://127.0.0.1:8000")
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

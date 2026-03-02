"""Interactive demo server with per-client isolation for WinbackFlow."""

from __future__ import annotations

import base64
import json
import os
import sys
import threading
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from openclaw_winback import WinbackFlowPipeline

try:
    from tools.experiment_summary import load_events, summarize
except ModuleNotFoundError:
    from experiment_summary import load_events, summarize

DEFAULT_CUSTOMERS_CSV = Path("data/poc/customers.csv")
DEFAULT_ORDERS_CSV = Path("data/poc/orders.csv")
CLIENTS_ROOT = Path("runtime/clients")
HOST = os.environ.get("DEMO_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", os.environ.get("DEMO_PORT", "8010")))
DEMO_USER = os.environ.get("DEMO_USER", "demo")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "")
# Serialize write operations in this threaded demo server.
# This prevents lost updates when multiple POST actions happen close together.
POST_ACTION_LOCK = threading.Lock()


def _safe_client_id(raw: str | None) -> str:
    value = (raw or "demo").strip().lower()
    value = "".join(ch for ch in value if ch.isalnum() or ch in {"-", "_"})
    return value or "demo"


def _client_dir(client_id: str) -> Path:
    return CLIENTS_ROOT / client_id


def _paths(client_id: str) -> dict:
    root = _client_dir(client_id)
    return {
        "root": root,
        "config": root / "config.json",
        "pending": root / "analytics/pending_run.json",
        "summary": root / "analytics/poc_summary.json",
        "events": root / "analytics/events.jsonl",
        "state": root / "state.json",
        "customers": root / "uploads/customers.csv",
        "orders": root / "uploads/orders.csv",
    }


def _ensure_seed_files(client_id: str) -> None:
    p = _paths(client_id)
    p["customers"].parent.mkdir(parents=True, exist_ok=True)
    p["summary"].parent.mkdir(parents=True, exist_ok=True)
    if not p["customers"].exists():
        p["customers"].write_text(DEFAULT_CUSTOMERS_CSV.read_text(encoding="utf-8"), encoding="utf-8")
    if not p["orders"].exists():
        p["orders"].write_text(DEFAULT_ORDERS_CSV.read_text(encoding="utf-8"), encoding="utf-8")
    if not p["config"].exists():
        p["config"].write_text(json.dumps({"platform": "custom"}, indent=2), encoding="utf-8")


def load_pending(client_id: str) -> dict | None:
    p = _paths(client_id)["pending"]
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save_pending(client_id: str, payload: dict) -> None:
    p = _paths(client_id)["pending"]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_state(client_id: str) -> dict:
    p = _paths(client_id)["state"]
    if not p.exists():
        return {"message": "", "error": ""}
    return json.loads(p.read_text(encoding="utf-8"))


def load_config(client_id: str) -> dict:
    p = _paths(client_id)["config"]
    if not p.exists():
        return {"platform": "custom"}
    cfg = json.loads(p.read_text(encoding="utf-8"))
    platform = str(cfg.get("platform", "custom")).strip().lower()
    if platform not in {"custom", "shopify"}:
        platform = "custom"
    return {"platform": platform}


def save_config(client_id: str, platform: str) -> None:
    normalized = (platform or "custom").strip().lower()
    if normalized not in {"custom", "shopify"}:
        normalized = "custom"
    p = _paths(client_id)["config"]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"platform": normalized}, indent=2), encoding="utf-8")


def save_state(client_id: str, message: str = "", error: str = "") -> None:
    p = _paths(client_id)["state"]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"message": message, "error": error}, indent=2), encoding="utf-8")


def load_summary(client_id: str) -> dict:
    p = _paths(client_id)["summary"]
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def refresh_summary(client_id: str) -> dict:
    p = _paths(client_id)
    data = summarize(load_events(events_file=p["events"]))
    p["summary"].parent.mkdir(parents=True, exist_ok=True)
    p["summary"].write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def _table_row_cells(values: list[str]) -> str:
    return "<tr>" + "".join(f"<td>{escape(v)}</td>" for v in values) + "</tr>"


def render_dashboard(client_id: str) -> str:
    _ensure_seed_files(client_id)
    pending = load_pending(client_id)
    summary = load_summary(client_id)
    state = load_state(client_id)
    config = load_config(client_id)
    selected_platform = config.get("platform", "custom")
    targeted = pending.get("targeted_profiles", []) if pending else []
    recs = pending.get("recommendations", []) if pending else []
    decisions = pending.get("decisions", {}) if pending else {}
    summary_pre = escape(json.dumps(summary, indent=2))

    targeted_rows = "".join(
        _table_row_cells(
            [
                str(p.get("user_id", "")),
                str(p.get("email", "")),
                str(p.get("days_since_last_order", "")),
                str(p.get("engagement_score", "")),
            ]
        )
        for p in targeted
    ) or "<tr><td colspan='4'>No pending targeted customers</td></tr>"

    rec_rows = []
    for rec in recs:
        rid = str(rec.get("recommendation_id", ""))
        decision = decisions.get(rid, "pending")
        row = (
            f"<tr><td>{escape(str(rec.get('user_id','')))}</td>"
            f"<td>{escape(str(rec.get('action','')))}</td>"
            f"<td>{escape(str(rec.get('confidence','')))}</td>"
            f"<td>{escape(str(rec.get('offer_code','')))}</td>"
            f"<td>{escape(decision)}</td>"
            f"<td>"
            f"<form method='POST' action='/decision' style='display:inline;'>"
            f"<input type='hidden' name='client' value='{escape(client_id)}' />"
            f"<input type='hidden' name='recommendation_id' value='{escape(rid)}' />"
            f"<input type='hidden' name='decision' value='approved' />"
            f"<button class='ok'>Approve</button></form> "
            f"<form method='POST' action='/decision' style='display:inline;'>"
            f"<input type='hidden' name='client' value='{escape(client_id)}' />"
            f"<input type='hidden' name='recommendation_id' value='{escape(rid)}' />"
            f"<input type='hidden' name='decision' value='rejected' />"
            f"<button class='warn'>Reject</button></form>"
            f"</td></tr>"
        )
        rec_rows.append(row)
    recommendations_rows = "".join(rec_rows) or "<tr><td colspan='6'>No pending recommendations</td></tr>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WinbackFlow Beta Console</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background:#0f172a; color:#e2e8f0; }}
    h1,h2 {{ margin: 0 0 12px; }}
    .actions {{ display:flex; gap:10px; margin:12px 0 18px; flex-wrap:wrap; }}
    form {{ display:inline; }}
    button {{ border:1px solid #334155; background:#1e293b; color:#e2e8f0; padding:8px 12px; border-radius:8px; cursor:pointer; }}
    button:hover {{ border-color:#60a5fa; }}
    .ok {{ border-color:#22c55e; }}
    .warn {{ border-color:#f59e0b; }}
    .card {{ background:#1e293b; border-radius:10px; padding:14px; margin:12px 0; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
    .label {{ color:#94a3b8; font-size:13px; }}
    .value {{ font-size:26px; font-weight:bold; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ border-bottom:1px solid #334155; padding:8px; text-align:left; font-size:13px; }}
    th {{ color:#94a3b8; }}
    pre {{ background:#020617; padding:12px; border-radius:8px; overflow:auto; }}
    textarea {{ width:100%; height:130px; background:#0b1220; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:8px; }}
    input[type=text], select {{ background:#0b1220; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:7px; }}
    .msg {{ margin: 8px 0; padding: 8px; border-radius: 8px; }}
    .okmsg {{ background:#052e16; border:1px solid #14532d; }}
    .errmsg {{ background:#3f1212; border:1px solid #7f1d1d; }}
  </style>
</head>
<body>
  <h1>WinbackFlow Beta Console</h1>

  <div class="card">
    <h2>Client Workspace</h2>
    <form method="GET" action="/">
      <label>Client ID:</label>
      <input type="text" name="client" value="{escape(client_id)}" />
      <button>Switch</button>
    </form>
    <form method="POST" action="/settings" style="margin-top:8px;">
      <input type="hidden" name="client" value="{escape(client_id)}" />
      <label>Platform:</label>
      <select name="platform">
        <option value="custom" {"selected" if selected_platform == "custom" else ""}>Custom Website</option>
        <option value="shopify" {"selected" if selected_platform == "shopify" else ""}>Shopify</option>
      </select>
      <button>Save Platform</button>
    </form>
    {f"<div class='msg okmsg'>{escape(state.get('message',''))}</div>" if state.get('message') else ""}
    {f"<div class='msg errmsg'>{escape(state.get('error',''))}</div>" if state.get('error') else ""}
  </div>

  <div class="card">
    <h2>Data Upload (CSV paste)</h2>
    <form method="POST" action="/upload">
      <input type="hidden" name="client" value="{escape(client_id)}" />
      <div class="label">customers.csv content</div>
      <textarea name="customers_csv"></textarea>
      <div class="label" style="margin-top:8px;">orders.csv content</div>
      <textarea name="orders_csv"></textarea>
      <div style="margin-top:8px;"><button>Save Uploaded CSV</button></div>
    </form>
  </div>

  <div class="actions">
    <form method="POST" action="/generate"><input type="hidden" name="client" value="{escape(client_id)}" /><button>1) Generate Recommendations</button></form>
    <form method="POST" action="/apply"><input type="hidden" name="client" value="{escape(client_id)}" /><button class="ok">2) Apply Selected Decisions</button></form>
    <form method="POST" action="/approve"><input type="hidden" name="client" value="{escape(client_id)}" /><button class="ok">Approve All</button></form>
    <form method="POST" action="/reject"><input type="hidden" name="client" value="{escape(client_id)}" /><button class="warn">Reject All</button></form>
    <form method="POST" action="/refresh"><input type="hidden" name="client" value="{escape(client_id)}" /><button>Refresh KPI Summary</button></form>
    <form method="POST" action="/reset"><input type="hidden" name="client" value="{escape(client_id)}" /><button class="warn">Reset To Sample CSV</button></form>
  </div>

  <div class="card">
    <h2>Pending Approval Queue</h2>
    <div>Total targeted: <b>{len(targeted)}</b> | Pending recommendations: <b>{len(recs)}</b></div>
  </div>

  <div class="card">
    <h2>Targeted Customers</h2>
    <table>
      <thead><tr><th>User ID</th><th>Email</th><th>Days Since Last Order</th><th>Engagement Score</th></tr></thead>
      <tbody>{targeted_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Pending Recommendations</h2>
    <table>
      <thead><tr><th>User ID</th><th>Action</th><th>Confidence</th><th>Offer Code</th><th>Decision</th><th>Action</th></tr></thead>
      <tbody>{recommendations_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Latest KPI Summary</h2>
    <div class="grid">
      <div><div class="label">Targeted Customers</div><div class="value">{summary.get('targeted_customers', 0)}</div></div>
      <div><div class="label">Manager Approved</div><div class="value">{summary.get('manager_approved_count', 0)}</div></div>
      <div><div class="label">Manager Rejected</div><div class="value">{summary.get('manager_rejected_count', 0)}</div></div>
      <div><div class="label">Customer Accepted (post-delivery)</div><div class="value">{summary.get('accepted_recommendations', 0)}</div></div>
      <div><div class="label">Customer Rejected (post-delivery)</div><div class="value">{summary.get('rejected_recommendations', 0)}</div></div>
      <div><div class="label">Action Rate (customer accepted / shown)</div><div class="value">{summary.get('recommendation_action_rate', 0):.2%}</div></div>
      <div><div class="label">Delivery Success</div><div class="value">{summary.get('delivery_success_rate', 0):.2%}</div></div>
      <div><div class="label">P95 Latency (ms)</div><div class="value">{summary.get('p95_delivery_latency_ms', 0)}</div></div>
    </div>
    <pre>{summary_pre}</pre>
  </div>
</body>
</html>
"""


class DemoHandler(BaseHTTPRequestHandler):
    def _read_form(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        data = parse_qs(raw)
        return {k: v[0] for k, v in data.items()}

    def _check_auth(self) -> bool:
        if not DEMO_PASSWORD:
            return True
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
            user, password = decoded.split(":", 1)
            return user == DEMO_USER and password == DEMO_PASSWORD
        except Exception:
            return False

    def _require_auth(self) -> bool:
        if self._check_auth():
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="WinbackFlow Beta"')
        self.end_headers()
        return False

    def _redirect(self, client_id: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/?" + urlencode({"client": client_id}))
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            body = b"OK"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if not self._require_auth():
            return
        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        query = parse_qs(parsed.query)
        client_id = _safe_client_id(query.get("client", ["demo"])[0])
        body = render_dashboard(client_id).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if not self._require_auth():
            return

        parsed = urlparse(self.path)
        form = self._read_form()
        client_id = _safe_client_id(form.get("client"))
        _ensure_seed_files(client_id)
        p = _paths(client_id)
        pipeline = WinbackFlowPipeline()
        with POST_ACTION_LOCK:
            old_telemetry = os.environ.get("WINBACK_TELEMETRY_FILE")
            os.environ["WINBACK_TELEMETRY_FILE"] = str(p["events"])

            try:
                if parsed.path == "/upload":
                    customers_csv = form.get("customers_csv", "").strip()
                    orders_csv = form.get("orders_csv", "").strip()
                    if customers_csv:
                        p["customers"].write_text(_resolve_csv_input(customers_csv), encoding="utf-8")
                    if orders_csv:
                        p["orders"].write_text(_resolve_csv_input(orders_csv), encoding="utf-8")
                    save_state(client_id, message="CSV uploaded for this client workspace.", error="")
                elif parsed.path == "/generate":
                    platform = load_config(client_id).get("platform", "custom")
                    generated = pipeline.generate(
                        customers_csv=p["customers"],
                        orders_csv=p["orders"],
                        pending_file=p["pending"],
                        platform=platform,
                    )
                    pending = load_pending(client_id) or {}
                    pending["decisions"] = {r["recommendation_id"]: "pending" for r in generated.get("recommendations", [])}
                    save_pending(client_id, pending)
                    save_state(client_id, message="Recommendations generated and queued for approval.", error="")
                elif parsed.path == "/settings":
                    platform = form.get("platform", "custom")
                    save_config(client_id, platform)
                    save_state(client_id, message=f"Platform saved: {platform}.", error="")
                elif parsed.path == "/approve":
                    platform = load_config(client_id).get("platform", "custom")
                    pipeline.approve(approved=True, pending_file=p["pending"], platform=platform)
                    refresh_summary(client_id)
                    save_state(client_id, message="All recommendations approved and delivered.", error="")
                elif parsed.path == "/reject":
                    platform = load_config(client_id).get("platform", "custom")
                    pipeline.approve(approved=False, pending_file=p["pending"], platform=platform)
                    refresh_summary(client_id)
                    save_state(client_id, message="All recommendations rejected (no delivery).", error="")
                elif parsed.path == "/decision":
                    rid = form.get("recommendation_id", "")
                    decision = form.get("decision", "")
                    if rid and decision in {"approved", "rejected"}:
                        pending = load_pending(client_id) or {}
                        decisions = pending.get("decisions", {})
                        decisions[rid] = decision
                        pending["decisions"] = decisions
                        save_pending(client_id, pending)
                        save_state(client_id, message=f"Decision saved for {rid[:8]}: {decision}.", error="")
                elif parsed.path == "/apply":
                    pending = load_pending(client_id) or {}
                    decisions = pending.get("decisions", {})
                    if decisions:
                        platform = load_config(client_id).get("platform", "custom")
                        pipeline.approve(decisions=decisions, pending_file=p["pending"], platform=platform)
                        refresh_summary(client_id)
                        save_state(client_id, message="Selected decisions applied and KPI summary refreshed.", error="")
                elif parsed.path == "/refresh":
                    refresh_summary(client_id)
                    save_state(client_id, message="KPI summary refreshed.", error="")
                elif parsed.path == "/reset":
                    p["customers"].write_text(DEFAULT_CUSTOMERS_CSV.read_text(encoding="utf-8"), encoding="utf-8")
                    p["orders"].write_text(DEFAULT_ORDERS_CSV.read_text(encoding="utf-8"), encoding="utf-8")
                    save_state(client_id, message="Reset complete: sample CSV restored.", error="")
                else:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return
            except Exception as e:
                save_state(client_id, message="", error=f"{type(e).__name__}: {e}")
            finally:
                if old_telemetry is None:
                    os.environ.pop("WINBACK_TELEMETRY_FILE", None)
                else:
                    os.environ["WINBACK_TELEMETRY_FILE"] = old_telemetry

        self._redirect(client_id)

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> None:
    _ensure_seed_files("demo")
    refresh_summary("demo")
    server = ThreadingHTTPServer((HOST, PORT), DemoHandler)
    print(f"WinbackFlow beta console running at http://{HOST}:{PORT}")
    server.serve_forever()


def _resolve_csv_input(raw_text: str) -> str:
    """Allow paste of CSV content or an absolute .csv file path."""
    text = raw_text.strip()
    if "\n" not in text and text.lower().endswith(".csv"):
        path = Path(text)
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
    return text


if __name__ == "__main__":
    main()

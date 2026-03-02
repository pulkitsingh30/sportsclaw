"""Generate a local HTML dashboard from PoC summary JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

try:
    from tools.experiment_summary import load_events, latest_session_events
except ModuleNotFoundError:
    from experiment_summary import load_events, latest_session_events

SUMMARY_PATH = Path("analytics/poc_summary.json")
DASHBOARD_PATH = Path("dashboard/index.html")


def load_summary(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Summary file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_detail_sets() -> Dict[str, List[dict]]:
    events = latest_session_events(load_events())
    targeted: Dict[str, dict] = {}
    accepted: List[dict] = []
    rejected: List[dict] = []

    for event in events:
        event_name = event.get("event_name")
        user_id = event.get("user_id")
        if event_name == "recommendation_shown" and user_id and user_id != "system":
            targeted[user_id] = {
                "user_id": user_id,
                "action": event.get("action", ""),
                "confidence": event.get("confidence", ""),
                "channel": event.get("channel", ""),
            }
        elif event_name == "feedback_received":
            row = {
                "user_id": user_id,
                "accepted": event.get("accepted", False),
                "channel": event.get("channel", ""),
            }
            if row["accepted"]:
                accepted.append(row)
            else:
                rejected.append(row)

    return {
        "targeted": list(targeted.values()),
        "accepted": accepted,
        "rejected": rejected,
    }


def render_html(summary: dict, details: Dict[str, List[dict]]) -> str:
    accepted_pct = summary.get("accepted_rejected_split", {}).get("accepted_pct", 0.0) * 100
    rejected_pct = summary.get("accepted_rejected_split", {}).get("rejected_pct", 0.0) * 100
    details_json = json.dumps(details)
    targeted_rows = _table_html(details.get("targeted", []))
    accepted_rows = _table_html(details.get("accepted", []))
    rejected_rows = _table_html(details.get("rejected", []))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WinbackFlow PoC Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #0f172a; color: #e2e8f0; }}
    h1 {{ margin: 0 0 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
    .card {{ background: #1e293b; border-radius: 10px; padding: 14px; }}
    .card.clickable {{ cursor: pointer; border: 1px solid #334155; }}
    .card.clickable:hover {{ border-color: #60a5fa; }}
    .cardLink {{ color: inherit; text-decoration: none; display: block; }}
    .label {{ color: #94a3b8; font-size: 13px; }}
    .value {{ font-size: 28px; font-weight: bold; margin-top: 4px; }}
    .bar-wrap {{ background: #334155; border-radius: 8px; overflow: hidden; height: 22px; margin-top: 8px; }}
    .bar-acc {{ background: #22c55e; height: 22px; float: left; }}
    .bar-rej {{ background: #ef4444; height: 22px; float: left; }}
    pre {{ background: #020617; padding: 12px; border-radius: 8px; overflow: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #334155; padding: 8px; text-align: left; font-size: 13px; }}
    th {{ color: #94a3b8; }}
    #detailsTitle {{ margin: 0 0 10px; }}
    .nav {{ display:flex; gap:10px; margin: 10px 0 16px; flex-wrap: wrap; }}
    .nav a {{ color: #93c5fd; text-decoration:none; background:#1e293b; border:1px solid #334155; padding:6px 10px; border-radius:8px; font-size: 13px; }}
    .nav a:hover {{ border-color:#60a5fa; }}
  </style>
</head>
<body>
  <h1>WinbackFlow KPI Dashboard</h1>
  <div class="nav">
    <a href="#detail-targeted">Jump: Targeted</a>
    <a href="#detail-accepted">Jump: Accepted</a>
    <a href="#detail-rejected">Jump: Rejected</a>
    <a href="#top-kpis">Jump: KPI Cards</a>
    <a href="#raw-summary">Jump: Raw Summary</a>
  </div>
  <div id="top-kpis"></div>
  <div class="grid">
    <div class="card clickable" data-detail="targeted"><a class="cardLink" href="#detail-targeted"><div class="label">Targeted Customers</div><div class="value">{summary.get("targeted_customers", 0)}</div></a></div>
    <div class="card"><div class="label">Recommendation Action Rate</div><div class="value">{summary.get("recommendation_action_rate", 0):.2%}</div></div>
    <div class="card clickable" data-detail="accepted"><a class="cardLink" href="#detail-accepted"><div class="label">Accepted Recommendations</div><div class="value">{summary.get("accepted_recommendations", 0)}</div></a></div>
    <div class="card clickable" data-detail="rejected"><a class="cardLink" href="#detail-rejected"><div class="label">Rejected Recommendations</div><div class="value">{summary.get("rejected_recommendations", 0)}</div></a></div>
    <div class="card"><div class="label">Delivery Success Rate</div><div class="value">{summary.get("delivery_success_rate", 0):.2%}</div></div>
    <div class="card"><div class="label">Approval Blocked Count</div><div class="value">{summary.get("approval_blocked_count", 0)}</div></div>
    <div class="card"><div class="label">P95 Delivery Latency (ms)</div><div class="value">{summary.get("p95_delivery_latency_ms", 0)}</div></div>
    <div class="card"><div class="label">Projected Recovered Revenue</div><div class="value">${summary.get("projected_recovered_revenue", 0):,.2f}</div></div>
  </div>
  <div class="card" id="detail-targeted" style="margin-top: 14px;">
    <h3 style="margin: 0 0 10px;">Drill-down: Targeted Customers</h3>
    {targeted_rows}
  </div>
  <div class="card" id="detail-accepted" style="margin-top: 14px;">
    <h3 style="margin: 0 0 10px;">Drill-down: Accepted Recommendations</h3>
    {accepted_rows}
  </div>
  <div class="card" id="detail-rejected" style="margin-top: 14px;">
    <h3 style="margin: 0 0 10px;">Drill-down: Rejected Recommendations</h3>
    {rejected_rows}
  </div>
  <div class="card" style="margin-top: 14px;">
    <div class="label">Accepted vs Rejected Split</div>
    <div class="bar-wrap">
      <div class="bar-acc" style="width:{accepted_pct:.2f}%"></div>
      <div class="bar-rej" style="width:{rejected_pct:.2f}%"></div>
    </div>
    <div style="margin-top:8px;">Accepted: {accepted_pct:.2f}% | Rejected: {rejected_pct:.2f}%</div>
  </div>
  <div class="card" style="margin-top: 14px;">
    <h3 id="detailsTitle">Details: Click a card to inspect</h3>
    <div id="detailsBody">Select `Targeted Customers`, `Accepted Recommendations`, or `Rejected Recommendations`.</div>
  </div>
  <div class="card" id="raw-summary" style="margin-top: 14px;">
    <div class="label">Raw Summary</div>
    <pre>{json.dumps(summary, indent=2)}</pre>
  </div>
  <script>
    const detailSets = {details_json};
    const detailsTitle = document.getElementById("detailsTitle");
    const detailsBody = document.getElementById("detailsBody");

    function renderTable(rows) {{
      if (!rows || rows.length === 0) {{
        detailsBody.innerHTML = "No rows available for this selection.";
        return;
      }}
      const columns = Object.keys(rows[0]);
      let html = "<table><thead><tr>";
      columns.forEach(c => html += `<th>${{c}}</th>`);
      html += "</tr></thead><tbody>";
      rows.forEach(r => {{
        html += "<tr>";
        columns.forEach(c => html += `<td>${{String(r[c])}}</td>`);
        html += "</tr>";
      }});
      html += "</tbody></table>";
      detailsBody.innerHTML = html;
    }}

    document.querySelectorAll(".card.clickable").forEach(card => {{
      card.addEventListener("click", () => {{
        const key = card.getAttribute("data-detail");
        if (key === "targeted") detailsTitle.textContent = "Details: Targeted Customers";
        if (key === "accepted") detailsTitle.textContent = "Details: Accepted Recommendations";
        if (key === "rejected") detailsTitle.textContent = "Details: Rejected Recommendations";
        renderTable(detailSets[key] || []);
      }});
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    summary = load_summary(SUMMARY_PATH)
    details = build_detail_sets()
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_PATH.write_text(render_html(summary, details), encoding="utf-8")
    print(f"Dashboard generated: {DASHBOARD_PATH}")


def _table_html(rows: List[dict]) -> str:
    if not rows:
        return "No rows available."
    columns = list(rows[0].keys())
    head = "".join(f"<th>{c}</th>" for c in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{str(row.get(c, ''))}</td>" for c in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    body = "".join(body_rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


if __name__ == "__main__":
    main()

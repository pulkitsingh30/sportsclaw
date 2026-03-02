# WinbackFlow

Investor-demo PoC for low-engagement customer reactivation using OpenClaw-style skills orchestration.

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## PoC Scope (Shopify/CSV)

This repo includes a deterministic end-to-end PoC:

- Workflow: low-engagement customer reactivation
- Core skills:
  - `data_ingest_skill`
  - `recommendation_skill`
  - `explanation_skill`
  - `delivery_skill`
  - `feedback_capture_skill`
- Pipeline entrypoint: `openclaw_winback/pipeline.py`
- Demo runner: `run_poc_demo.py`

Run the PoC demo:

```bash
python3 run_poc_demo.py --mode generate
python3 run_poc_demo.py --mode approve --approved true
```

Single command (generate + approve):

```bash
python3 run_poc_demo.py --mode full --approved true
```

## Interactive approval demo (recommended for client calls)

Start local interactive console:

```bash
python3 tools/demo_server.py
```

Open:

```text
http://127.0.0.1:8010
```

Client isolation:

- Switch workspace using query param, e.g. `/?client=acme`
- Each client has separate files under `runtime/clients/<client_id>/`

Use buttons in order:
1. Generate Recommendations
2. Approve or Reject individual rows
3. Apply Selected Decisions
4. Refresh KPI Summary (optional)

Platform support in demo:
- Set `Platform` in Client Workspace before generating (`Custom Website` or `Shopify`).
- Acceptance logic is platform-aware via connectors:
  - Shopify: discounted online/shopify orders imply conversion.
  - Custom: online/web conversion signals (discount or order value threshold) imply conversion.

## Render hosting (beta)

Start command:

```bash
python3 tools/demo_server.py
```

Recommended environment variables:

```text
DEMO_USER=admin
DEMO_PASSWORD=change-me
PORT=10000
```

If `DEMO_PASSWORD` is set, the app uses HTTP Basic Auth.

Generate and view dashboard:

```bash
python3 tools/generate_dashboard.py
python3 -m http.server 8000
```

Then open `http://localhost:8000/dashboard/index.html`.

Telemetry events are recorded to:

```text
analytics/events.jsonl
```

The command above also prints KPI summary and writes:

```text
analytics/poc_summary.json
```

## Documentation

- `docs/fresh_start/workflow_scope.md`
- `docs/fresh_start/kpis.md`
- `docs/fresh_start/launch_experiment.md`
- `docs/fresh_start/b2b_pilot_pack.md`
- `docs/poc/architecture.md`
- `docs/poc/value_case.md`
- `docs/poc/demo_script.md`

"""Summarize telemetry into core validation metrics."""

from __future__ import annotations

import json
import pathlib
import argparse
from collections import defaultdict

EVENTS_FILE = pathlib.Path("analytics/events.jsonl")
DEFAULT_OUTPUT_FILE = pathlib.Path("analytics/poc_summary.json")


def load_events(events_file: pathlib.Path | None = None) -> list[dict]:
    events_file = events_file or EVENTS_FILE
    if not events_file.exists():
        return []
    events: list[dict] = []
    with events_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def summarize(events: list[dict], latest_session_only: bool = True) -> dict:
    if latest_session_only:
        events = latest_session_events(events)

    weekly_users = set()
    targeted_customers = set()
    shown = 0
    accepted = 0
    rejected = 0
    delivered = 0
    blocked = 0
    manager_rejected = 0
    manager_approved = 0
    latencies = []
    by_event = defaultdict(int)

    for e in events:
        event_name = e.get("event_name", "unknown")
        by_event[event_name] += 1
        user_id = e.get("user_id")
        if user_id and user_id != "system":
            weekly_users.add(user_id)
        if event_name == "recommendation_shown":
            shown += 1
            if user_id and user_id != "system":
                targeted_customers.add(user_id)
        elif event_name == "recommendation_accepted":
            accepted += 1
        elif event_name == "recommendation_rejected":
            rejected += 1
        elif event_name == "recommendation_delivered":
            delivered += 1
            if isinstance(e.get("latency_ms"), int):
                latencies.append(e["latency_ms"])
        elif event_name == "delivery_blocked_by_policy":
            blocked += 1
        elif event_name == "manager_rejected":
            manager_rejected += 1
        elif event_name == "approval_applied":
            # Surface manager decisions separately from customer outcomes.
            extra = e if isinstance(e, dict) else {}
            approved_count = extra.get("approved_recommendations")
            rejected_count = extra.get("rejected_recommendations")
            if isinstance(approved_count, int):
                manager_approved += approved_count
            if isinstance(rejected_count, int):
                manager_rejected += rejected_count

    rar = (accepted / shown) if shown else 0.0
    delivery_success_rate = (delivered / shown) if shown else 0.0
    p95 = percentile(latencies, 95)
    projected_recovered_revenue = projected_revenue(accepted_count=accepted, assumed_avg_order_value=90.0, assumed_gross_margin=0.35)
    return {
        "targeted_customers": len(targeted_customers),
        "wau": len(weekly_users),
        "recommendation_action_rate": round(rar, 4),
        "accepted_recommendations": accepted,
        "rejected_recommendations": rejected,
        "accepted_rejected_split": split(accepted, rejected),
        "delivery_count": delivered,
        "approval_blocked_count": blocked,
        "manager_approved_count": manager_approved,
        "manager_rejected_count": manager_rejected,
        "delivery_success_rate": round(delivery_success_rate, 4),
        "p95_delivery_latency_ms": p95,
        "projected_recovered_revenue": projected_recovered_revenue,
        "revenue_assumption": {
            "assumed_avg_order_value": 90.0,
            "assumed_gross_margin": 0.35,
            "formula": "accepted_recommendations * assumed_avg_order_value * assumed_gross_margin",
        },
        "event_counts": dict(by_event),
    }


def percentile(values: list[int], p: int) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    idx = int(round((p / 100) * (len(sorted_values) - 1)))
    return sorted_values[idx]


def split(accepted: int, rejected: int) -> dict:
    total = accepted + rejected
    if total == 0:
        return {"accepted_pct": 0.0, "rejected_pct": 0.0}
    return {
        "accepted_pct": round(accepted / total, 4),
        "rejected_pct": round(rejected / total, 4),
    }


def projected_revenue(accepted_count: int, assumed_avg_order_value: float, assumed_gross_margin: float) -> float:
    value = accepted_count * assumed_avg_order_value * assumed_gross_margin
    return round(value, 2)


def latest_session_events(events: list[dict]) -> list[dict]:
    session_completed = [e for e in events if e.get("event_name") == "session_completed" and e.get("session_id")]
    if not session_completed:
        return events
    latest_session_id = session_completed[-1]["session_id"]
    return [e for e in events if e.get("session_id") == latest_session_id]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PoC telemetry for investor demo.")
    parser.add_argument(
        "--write-sample",
        choices=["true", "false"],
        default="true",
        help="Write deterministic summary to analytics/poc_summary.json",
    )
    parser.add_argument(
        "--output-file",
        default=str(DEFAULT_OUTPUT_FILE),
        help="Summary output path when --write-sample=true",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    events = load_events()
    summary = summarize(events)
    print(json.dumps(summary, indent=2))
    if args.write_sample == "true":
        output_file = pathlib.Path(args.output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

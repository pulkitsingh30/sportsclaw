"""Run the WinbackFlow PoC pipeline demo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from openclaw_winback import WinbackFlowPipeline
from tools.experiment_summary import DEFAULT_OUTPUT_FILE, load_events, summarize


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WinbackFlow CSV-based PoC demo")
    parser.add_argument(
        "--mode",
        choices=["full", "generate", "approve"],
        default="full",
        help="Workflow stage to run",
    )
    parser.add_argument("--customers", default="data/poc/customers.csv", help="Path to customers CSV")
    parser.add_argument("--orders", default="data/poc/orders.csv", help="Path to orders CSV")
    parser.add_argument("--approved", choices=["true", "false"], default="true", help="Approval gate toggle")
    parser.add_argument(
        "--with-summary",
        choices=["true", "false"],
        default="true",
        help="Print KPI summary and write analytics/poc_summary.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    approved = args.approved.lower() == "true"
    pipeline = WinbackFlowPipeline()
    if args.mode == "generate":
        result = pipeline.generate(customers_csv=Path(args.customers), orders_csv=Path(args.orders))
    elif args.mode == "approve":
        result = pipeline.approve(approved=approved)
    else:
        result = pipeline.run(
            customers_csv=Path(args.customers),
            orders_csv=Path(args.orders),
            approved=approved,
        )
    print(json.dumps(result, indent=2))
    print(
        "\n".join(
            [
                "",
                "---- WinbackFlow Delivery Summary ----",
                f"Run mode: {args.mode}",
                f"Profiles loaded: {len(result.get('profiles', []))}",
                f"Targeted low-engagement customers: {len(result.get('targeted_profiles', []))}",
                f"Recommendations generated: {len(result.get('recommendations', []))}",
                f"Deliveries sent: {len(result.get('deliveries', []))}",
                f"Approval mode: {'ON' if approved else 'OFF'}",
            ]
        )
    )
    if args.with_summary == "true" and args.mode != "generate":
        summary = summarize(load_events())
        print(
            "\n".join(
                [
                    "",
                    "---- WinbackFlow KPI Summary ----",
                    json.dumps(summary, indent=2),
                ]
            )
        )
        DEFAULT_OUTPUT_FILE.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    elif args.with_summary == "true":
        print("\nSkipping KPI summary in generate-only mode. Run approve/full to finalize a session.")


if __name__ == "__main__":
    main()

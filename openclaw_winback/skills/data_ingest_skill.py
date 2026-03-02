"""Data ingest skill for customer profiles."""

from __future__ import annotations

from pathlib import Path
from typing import List

from openclaw_winback.models import CustomerProfile, WorkflowContext
from openclaw_winback.poc_csv_ingest import parse_customers_csv
from openclaw_winback.telemetry import elapsed_ms, record_event, start_timer


class DataIngestSkill:
    """Loads deterministic PoC customer records from CSV."""

    def run(self, context: WorkflowContext, customers_csv: Path) -> List[CustomerProfile]:
        started = start_timer()
        ingest = parse_customers_csv(customers_csv)
        profiles = ingest.profiles
        for profile in profiles:
            record_event(
                context=context,
                event_name="data_ingested",
                user_id=profile.user_id,
                channel=profile.channel,
                latency_ms=elapsed_ms(started),
                extra={
                    "primary_category": profile.primary_category,
                    "days_since_last_order": profile.days_since_last_order,
                },
            )
        return profiles

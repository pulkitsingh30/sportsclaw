"""CSV ingest and validation for WinbackFlow PoC."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List

from openclaw_winback.models import CustomerProfile

REQUIRED_CUSTOMER_COLUMNS = {
    "customer_id",
    "email",
    "first_name",
    "last_name",
    "last_order_date",
    "total_orders",
    "total_spend",
    "avg_order_value",
    "email_engagement_score",
    "sms_engagement_score",
    "preferred_channel",
    "primary_category",
}


@dataclass
class IngestResult:
    profiles: List[CustomerProfile]
    raw_rows: int
    valid_rows: int
    invalid_rows: int


def parse_customers_csv(path: Path, reference_date: date | None = None) -> IngestResult:
    reference_date = reference_date or date(2026, 3, 1)
    profiles: List[CustomerProfile] = []
    raw_rows = 0
    invalid_rows = 0

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        _validate_columns(reader.fieldnames or [])
        for row in reader:
            raw_rows += 1
            try:
                profile = _to_profile(row, reference_date)
                profiles.append(profile)
            except Exception:
                invalid_rows += 1

    return IngestResult(
        profiles=profiles,
        raw_rows=raw_rows,
        valid_rows=len(profiles),
        invalid_rows=invalid_rows,
    )


def parse_orders_csv(path: Path) -> List[dict]:
    """Parse orders data for future extensions; not required in scoring yet."""
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _validate_columns(columns: Iterable[str]) -> None:
    got = set(columns)
    missing = REQUIRED_CUSTOMER_COLUMNS - got
    if missing:
        raise ValueError(f"Missing required customer columns: {sorted(missing)}")


def _to_profile(row: dict, reference_date: date) -> CustomerProfile:
    last_order = date.fromisoformat(row["last_order_date"])
    days_since = max((reference_date - last_order).days, 0)
    email_engagement = float(row["email_engagement_score"])
    sms_engagement = float(row["sms_engagement_score"])
    engagement_score = round((email_engagement * 0.65) + (sms_engagement * 0.35), 3)
    total_orders = int(row["total_orders"])
    total_spend = float(row["total_spend"])
    avg_order_value = float(row["avg_order_value"])

    purchase_score = round(min(total_spend / 1000.0, 1.0), 3)
    full_name = f"{row['first_name']} {row['last_name']}".strip()

    return CustomerProfile(
        user_id=row["customer_id"],
        email=row["email"],
        full_name=full_name,
        days_since_last_order=days_since,
        total_orders=total_orders,
        total_spend=total_spend,
        avg_order_value=avg_order_value,
        purchase_score=purchase_score,
        engagement_score=engagement_score,
        primary_category=row["primary_category"],
        channel=row["preferred_channel"],
    )

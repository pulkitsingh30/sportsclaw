"""Segmentation rules for low-engagement customers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from openclaw_winback.models import CustomerProfile


@dataclass
class SegmentationThresholds:
    inactive_days: int = 90
    low_engagement_score: float = 0.25
    low_order_count: int = 2


def select_low_engagement_customers(
    profiles: Iterable[CustomerProfile],
    thresholds: SegmentationThresholds | None = None,
) -> List[CustomerProfile]:
    thresholds = thresholds or SegmentationThresholds()
    selected: List[CustomerProfile] = []
    for profile in profiles:
        if _is_low_engagement(profile, thresholds):
            selected.append(profile)
    return selected


def _is_low_engagement(profile: CustomerProfile, thresholds: SegmentationThresholds) -> bool:
    return (
        profile.days_since_last_order >= thresholds.inactive_days
        or profile.engagement_score < thresholds.low_engagement_score
        or profile.total_orders <= thresholds.low_order_count
    )

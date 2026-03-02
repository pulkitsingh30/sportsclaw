"""Shared models for the WinbackFlow reactivation workflow."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CustomerProfile:
    user_id: str
    email: str
    full_name: str
    days_since_last_order: int
    total_orders: int
    total_spend: float
    avg_order_value: float
    purchase_score: float
    engagement_score: float
    primary_category: str
    channel: str = "email"


@dataclass
class Recommendation:
    recommendation_id: str
    user_id: str
    action: str
    confidence: float
    rationale: List[str]
    offer_code: str
    suggested_message: str


@dataclass
class WorkflowContext:
    workflow_id: str = "customer_reactivation_v1"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at_utc: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, str] = field(default_factory=dict)

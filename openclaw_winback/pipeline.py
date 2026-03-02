"""End-to-end workflow orchestration for the WinbackFlow PoC."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from openclaw_winback.models import CustomerProfile, Recommendation, WorkflowContext
from openclaw_winback.poc_csv_ingest import parse_orders_csv
from openclaw_winback.segmentation import select_low_engagement_customers
from openclaw_winback.skills import (
    DataIngestSkill,
    DeliverySkill,
    ExplanationSkill,
    FeedbackCaptureSkill,
    RecommendationSkill,
)
from openclaw_winback.telemetry import elapsed_ms, record_event, start_timer

PENDING_RUN_FILE = Path("analytics/pending_run.json")


class WinbackFlowPipeline:
    """OpenClaw-style orchestrator that composes reusable skills."""

    def __init__(self) -> None:
        self.data_ingest = DataIngestSkill()
        self.recommend = RecommendationSkill()
        self.explain = ExplanationSkill()
        self.deliver = DeliverySkill()
        self.feedback = FeedbackCaptureSkill()

    def generate(
        self,
        customers_csv: Path,
        orders_csv: Path,
        pending_file: Path = PENDING_RUN_FILE,
        platform: str = "custom",
    ) -> Dict[str, List[dict]]:
        context = WorkflowContext()
        context.metadata["platform"] = platform
        pipeline_start = start_timer()
        record_event(context, "session_started", user_id="system", channel="pipeline")

        profiles = self.data_ingest.run(context, customers_csv=customers_csv)
        orders = parse_orders_csv(orders_csv)
        selected = select_low_engagement_customers(profiles)

        recommendations = self.recommend.run(context, selected)
        recommendations = self.explain.run(context, selected, recommendations)
        record_event(
            context,
            event_name="recommendations_pending_approval",
            user_id="system",
            channel="pipeline",
            latency_ms=elapsed_ms(pipeline_start),
            extra={"pending_recommendations": len(recommendations)},
        )

        pending_payload = {
            "context": context.__dict__,
            "profiles": [p.__dict__ for p in profiles],
            "targeted_profiles": [p.__dict__ for p in selected],
            "recommendations": [r.__dict__ for r in recommendations],
            "orders": orders,
            "orders_sample_count": len(orders),
            "generated_latency_ms": elapsed_ms(pipeline_start),
        }
        pending_file.parent.mkdir(parents=True, exist_ok=True)
        pending_file.write_text(json.dumps(pending_payload, indent=2), encoding="utf-8")

        return {
            "stage": "generated",
            "pending_file": str(pending_file),
            "profiles": pending_payload["profiles"],
            "targeted_profiles": pending_payload["targeted_profiles"],
            "recommendations": pending_payload["recommendations"],
            "orders_sample_count": pending_payload["orders_sample_count"],
        }

    def approve(
        self,
        approved: bool = True,
        pending_file: Path = PENDING_RUN_FILE,
        decisions: dict | None = None,
        platform: str | None = None,
    ) -> Dict[str, List[dict]]:
        if not pending_file.exists():
            raise FileNotFoundError(f"Pending file not found: {pending_file}")

        payload = json.loads(pending_file.read_text(encoding="utf-8"))
        ctx_raw = payload["context"]
        context = WorkflowContext(
            workflow_id=ctx_raw["workflow_id"],
            session_id=ctx_raw["session_id"],
            started_at_utc=ctx_raw["started_at_utc"],
            metadata=ctx_raw.get("metadata", {}),
        )
        selected = [self._profile_from_dict(p) for p in payload.get("targeted_profiles", [])]
        recommendations = [self._recommendation_from_dict(r) for r in payload.get("recommendations", [])]
        orders = payload.get("orders", [])
        configured_platform = platform or ctx_raw.get("metadata", {}).get("platform", "custom")
        pipeline_start = start_timer()

        approved_recommendations = recommendations
        rejected_recommendations: list[Recommendation] = []
        approval_mode = "bulk"
        if decisions:
            approval_mode = "per_recommendation"
            approved_recommendations = [r for r in recommendations if decisions.get(r.recommendation_id) == "approved"]
            rejected_recommendations = [r for r in recommendations if decisions.get(r.recommendation_id) == "rejected"]

        record_event(
            context,
            event_name="approval_applied",
            user_id="system",
            channel="pipeline",
            latency_ms=elapsed_ms(pipeline_start),
            extra={
                "approved": approved,
                "approval_mode": approval_mode,
                "approved_recommendations": len(approved_recommendations),
                "rejected_recommendations": len(rejected_recommendations),
            },
        )

        deliveries = self.deliver.run(
            context,
            selected,
            approved_recommendations if decisions else recommendations,
            approved=approved if not decisions else True,
        )
        if decisions:
            for rec in rejected_recommendations:
                record_event(
                    context,
                    event_name="manager_rejected",
                    user_id=rec.user_id,
                    channel="pipeline",
                    extra={"recommendation_id": rec.recommendation_id},
                )
        feedback = self.feedback.run(context, deliveries, orders=orders, platform=configured_platform)

        record_event(
            context,
            event_name="session_completed",
            user_id="system",
            channel="pipeline",
            latency_ms=elapsed_ms(pipeline_start),
            extra={
                "targeted_profiles": len(selected),
                "recommendations": len(recommendations),
                "deliveries": len(deliveries),
                "feedback_records": len(feedback),
                "approved": approved,
                "approval_mode": approval_mode,
                "platform": configured_platform,
            },
        )

        return {
            "stage": "approved" if approved else "blocked",
            "pending_file": str(pending_file),
            "targeted_profiles": payload.get("targeted_profiles", []),
            "recommendations": payload.get("recommendations", []),
            "deliveries": deliveries,
            "feedback": feedback,
            "approved_recommendations_count": len(approved_recommendations),
            "rejected_recommendations_count": len(rejected_recommendations),
            "approval_mode": approval_mode,
            "orders_sample_count": payload.get("orders_sample_count", 0),
        }

    def run(self, customers_csv: Path, orders_csv: Path, approved: bool = True, platform: str = "custom") -> Dict[str, List[dict]]:
        generated = self.generate(customers_csv=customers_csv, orders_csv=orders_csv, platform=platform)
        approved_result = self.approve(approved=approved, platform=platform)
        return {
            "stage": "full",
            "pending_file": generated["pending_file"],
            "profiles": generated["profiles"],
            "targeted_profiles": generated["targeted_profiles"],
            "recommendations": generated["recommendations"],
            "deliveries": approved_result["deliveries"],
            "feedback": approved_result["feedback"],
            "orders_sample_count": generated["orders_sample_count"],
        }

    def _profile_from_dict(self, raw: dict) -> CustomerProfile:
        return CustomerProfile(**raw)

    def _recommendation_from_dict(self, raw: dict) -> Recommendation:
        return Recommendation(**raw)

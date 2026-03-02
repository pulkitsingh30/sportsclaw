"""Feedback capture skill for recommendation outcomes."""

from __future__ import annotations

from typing import Iterable, List

from openclaw_winback.connectors import get_connector
from openclaw_winback.models import WorkflowContext
from openclaw_winback.telemetry import elapsed_ms, record_event, start_timer


class FeedbackCaptureSkill:
    """Captures acceptance/rejection as structured telemetry."""

    def run(
        self,
        context: WorkflowContext,
        deliveries: Iterable[dict],
        orders: Iterable[dict] | None = None,
        platform: str = "custom",
    ) -> List[dict]:
        started = start_timer()
        feedback: List[dict] = []
        deliveries_list = list(deliveries)
        orders_list = list(orders or [])
        connector = get_connector(platform)
        accepted_ids = connector.accepted_recommendation_ids(deliveries_list, orders_list)

        for item in deliveries_list:
            user_id = item["user_id"]
            recommendation_id = item["recommendation_id"]
            accepted = recommendation_id in accepted_ids
            feedback_item = {
                "user_id": user_id,
                "recommendation_id": recommendation_id,
                "accepted": accepted,
                "comment": "Looks useful" if accepted else "Not relevant this week",
            }
            feedback.append(feedback_item)
            record_event(
                context=context,
                event_name="feedback_received",
                user_id=user_id,
                channel=item["channel"],
                latency_ms=elapsed_ms(started),
                extra={"accepted": accepted, "connector": connector.name},
            )
            record_event(
                context=context,
                event_name="recommendation_accepted" if accepted else "recommendation_rejected",
                user_id=user_id,
                channel=item["channel"],
                latency_ms=elapsed_ms(started),
            )
        return feedback

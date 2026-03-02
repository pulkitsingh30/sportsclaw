"""Delivery skill with explicit approval gate."""

from __future__ import annotations

from typing import Iterable, List

from openclaw_winback.models import CustomerProfile, Recommendation, WorkflowContext
from openclaw_winback.telemetry import elapsed_ms, record_event, start_timer


class DeliverySkill:
    """Delivers recommendations only when approval is true."""

    def run(
        self,
        context: WorkflowContext,
        profiles: Iterable[CustomerProfile],
        recommendations: Iterable[Recommendation],
        approved: bool,
    ) -> List[dict]:
        started = start_timer()
        profile_by_user = {p.user_id: p for p in profiles}
        deliveries: List[dict] = []

        for rec in recommendations:
            profile = profile_by_user[rec.user_id]
            if not approved:
                record_event(
                    context=context,
                    event_name="delivery_blocked_by_policy",
                    user_id=rec.user_id,
                    channel=profile.channel,
                    latency_ms=elapsed_ms(started),
                    extra={"recommendation_id": rec.recommendation_id},
                )
                continue

            message = rec.suggested_message
            delivery = {
                "user_id": rec.user_id,
                "action": rec.action,
                "confidence": rec.confidence,
                "channel": profile.channel,
                "message": message,
                "recommendation_id": rec.recommendation_id,
            }
            deliveries.append(delivery)
            record_event(
                context=context,
                event_name="recommendation_delivered",
                user_id=rec.user_id,
                channel=profile.channel,
                latency_ms=elapsed_ms(started),
                extra={"recommendation_id": rec.recommendation_id},
            )
        return deliveries

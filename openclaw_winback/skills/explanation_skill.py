"""Explanation skill for recommendation transparency."""

from __future__ import annotations

from typing import Iterable, List

from openclaw_winback.models import CustomerProfile, Recommendation, WorkflowContext
from openclaw_winback.telemetry import elapsed_ms, record_event, start_timer


class ExplanationSkill:
    """Attaches concise reasoning to each recommendation."""

    def run(
        self,
        context: WorkflowContext,
        profiles: Iterable[CustomerProfile],
        recommendations: Iterable[Recommendation],
    ) -> List[Recommendation]:
        started = start_timer()
        profile_by_user = {p.user_id: p for p in profiles}
        output: List[Recommendation] = []

        for rec in recommendations:
            profile = profile_by_user[rec.user_id]
            rec.rationale = [
                f"Last order was {profile.days_since_last_order} days ago.",
                f"Engagement score is {profile.engagement_score:.2f}.",
                f"Purchase score is {profile.purchase_score:.2f} from lifetime spend.",
                f"Primary category affinity: {profile.primary_category}.",
                f"Action selected: {rec.action}.",
            ]
            output.append(rec)
            record_event(
                context=context,
                event_name="explanation_generated",
                user_id=rec.user_id,
                channel=profile.channel,
                latency_ms=elapsed_ms(started),
                extra={"recommendation_id": rec.recommendation_id},
            )
        return output

"""Recommendation skill for low-engagement customer reactivation."""

from __future__ import annotations

from typing import Iterable, List
import hashlib

from openclaw_winback.models import CustomerProfile, Recommendation, WorkflowContext
from openclaw_winback.telemetry import elapsed_ms, record_event, start_timer


class RecommendationSkill:
    """Creates one next-best-action recommendation per customer."""

    def run(self, context: WorkflowContext, profiles: Iterable[CustomerProfile]) -> List[Recommendation]:
        started = start_timer()
        output: List[Recommendation] = []
        for profile in profiles:
            confidence = self._confidence(profile)
            action = self._action(profile)
            offer_code = self._offer_code(profile)
            recommendation = Recommendation(
                recommendation_id=self._recommendation_id(profile, action),
                user_id=profile.user_id,
                action=action,
                confidence=confidence,
                rationale=[],
                offer_code=offer_code,
                suggested_message=self._suggested_message(profile, action, offer_code),
            )
            output.append(recommendation)
            record_event(
                context=context,
                event_name="recommendation_shown",
                user_id=profile.user_id,
                channel=profile.channel,
                latency_ms=elapsed_ms(started),
                extra={"confidence": confidence, "action": action},
            )
        return output

    def _confidence(self, profile: CustomerProfile) -> float:
        inactivity_factor = min(profile.days_since_last_order / 120.0, 1.0)
        score = (0.5 * inactivity_factor) + (0.3 * (1 - profile.engagement_score)) + (0.2 * (1 - profile.purchase_score))
        return round(min(max(score, 0.05), 0.95), 2)

    def _action(self, profile: CustomerProfile) -> str:
        if profile.days_since_last_order >= 90:
            return "send_winback_discount_offer"
        if profile.engagement_score < 0.3:
            return "send_personalized_product_nudge"
        return "send_replenishment_reminder"

    def _offer_code(self, profile: CustomerProfile) -> str:
        category_code = profile.primary_category.replace(" ", "").upper()[:4]
        return f"{category_code}-WIN10"

    def _recommendation_id(self, profile: CustomerProfile, action: str) -> str:
        seed = f"{profile.user_id}:{action}".encode("utf-8")
        return hashlib.sha1(seed).hexdigest()[:12]

    def _suggested_message(self, profile: CustomerProfile, action: str, offer_code: str) -> str:
        if action == "send_winback_discount_offer":
            return (
                f"Hi {profile.full_name.split(' ')[0]}, we saved a comeback offer for you. "
                f"Use {offer_code} for 10% off your next order."
            )
        if action == "send_personalized_product_nudge":
            return (
                f"Hi {profile.full_name.split(' ')[0]}, new picks in {profile.primary_category} match your history. "
                f"Your code: {offer_code}."
            )
        return (
            f"Hi {profile.full_name.split(' ')[0]}, it might be time to restock your favorites. "
            f"Use {offer_code} today."
        )

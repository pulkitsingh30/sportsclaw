"""Connector protocol for platform-specific conversion attribution."""

from __future__ import annotations

from typing import Iterable


class ConversionConnector:
    """Maps delivered recommendations to conversion outcomes."""

    name: str = "base"

    def accepted_recommendation_ids(self, deliveries: Iterable[dict], orders: Iterable[dict]) -> set[str]:
        raise NotImplementedError

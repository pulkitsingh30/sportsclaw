"""Generic custom-site conversion attribution rules."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .base import ConversionConnector


class CustomConnector(ConversionConnector):
    name = "custom"

    def accepted_recommendation_ids(self, deliveries: Iterable[dict], orders: Iterable[dict]) -> set[str]:
        orders_by_customer: dict[str, list[dict]] = defaultdict(list)
        for order in orders:
            cid = str(order.get("customer_id", ""))
            if cid:
                orders_by_customer[cid].append(order)

        accepted: set[str] = set()
        for item in deliveries:
            rec_id = str(item.get("recommendation_id", ""))
            cid = str(item.get("user_id", ""))
            if not rec_id or not cid:
                continue
            if self._has_conversion_signal(orders_by_customer.get(cid, [])):
                accepted.add(rec_id)
        return accepted

    def _has_conversion_signal(self, orders: list[dict]) -> bool:
        for order in orders:
            channel = str(order.get("purchase_channel", "")).strip().lower()
            total = float(order.get("order_total", 0) or 0)
            discount = str(order.get("discount_used", "")).strip().lower() in {"1", "true", "yes", "y"}
            if channel in {"online", "web", "website", "custom"} and (discount or total >= 75):
                return True
        return False

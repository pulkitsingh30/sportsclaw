"""Shopify-oriented conversion attribution using discounted orders."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .base import ConversionConnector


class ShopifyConnector(ConversionConnector):
    name = "shopify"

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
            if self._has_discounted_online_order(orders_by_customer.get(cid, [])):
                accepted.add(rec_id)
        return accepted

    def _has_discounted_online_order(self, orders: list[dict]) -> bool:
        for order in orders:
            discount = str(order.get("discount_used", "")).strip().lower() in {"1", "true", "yes", "y"}
            channel = str(order.get("purchase_channel", "")).strip().lower()
            if discount and channel in {"online", "shopify"}:
                return True
        return False

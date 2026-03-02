"""Platform connector abstractions for conversion attribution."""

from .base import ConversionConnector
from .custom_connector import CustomConnector
from .shopify_connector import ShopifyConnector


def get_connector(platform: str | None) -> ConversionConnector:
    key = (platform or "custom").strip().lower()
    if key == "shopify":
        return ShopifyConnector()
    return CustomConnector()


__all__ = ["ConversionConnector", "CustomConnector", "ShopifyConnector", "get_connector"]

"""Build ASCII SMS body for an order."""

from __future__ import annotations

from .parse_order import ParsedOrder


def build_sms_text(
    order: ParsedOrder,
    *,
    ig_contact_url: str = "https://ig.me/m/dimkava.georgia",
) -> str:
    return (
        f"DIM KAVA: Order #{order.order_id} received!\n"
        f"Date: {order.order_date}\n"
        f"Total: {order.total} GEL.\n"
        f"Our manager will call you shortly.\n"
        f"Contact us: {ig_contact_url}"
    )

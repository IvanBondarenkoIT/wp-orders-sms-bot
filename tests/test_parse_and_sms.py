from __future__ import annotations

from pathlib import Path

import pytest

from wp_orders_sms_bot.parse_order import parse_order_message
from wp_orders_sms_bot.phone import mask_phone, normalize_phone
from wp_orders_sms_bot.sms_text import build_sms_text

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_order_9111_with_plus_995() -> None:
    result = parse_order_message(_load("order_9111.txt"))
    assert result.skip_reason is None
    assert result.order is not None
    order = result.order
    assert order.order_id == "9111"
    assert order.order_date == "24 Oct 2026, 5:03 am"
    assert order.total == "379"
    assert "+995599228754" in order.phone_raw or "995599228754" in order.phone_raw

    phone = normalize_phone(order.phone_raw)
    assert phone == "995599228754"

    sms = build_sms_text(order)
    assert sms == (
        "DIM KAVA: Order #9111 received!\n"
        "Date: 24 Oct 2026, 5:03 am\n"
        "Total: 379 GEL.\n"
        "Our manager will call you shortly.\n"
        "Contact us: https://ig.me/m/dimkava.georgia"
    )
    assert mask_phone(phone) == "995***8754"


def test_parse_order_local_9_digit_phone() -> None:
    result = parse_order_message(_load("order_local_phone.txt"))
    assert result.skip_reason is None
    assert result.order is not None
    order = result.order
    assert order.order_id == "9001"
    assert order.total == "45.50"
    assert normalize_phone(order.phone_raw) == "995591348802"

    sms = build_sms_text(order)
    assert "Order #9001" in sms
    assert "Total: 45.50 GEL." in sms
    assert "Date: 25 Oct 2026, 2:15 pm" in sms


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+995599228754", "995599228754"),
        ("+995 599 228 754", "995599228754"),
        ("591348802", "995591348802"),
        ("00995599123456", "995599123456"),
        ("0591348802", "995591348802"),
        ("+79161234567", None),
        ("+12025550123", None),
        ("99559922875", None),  # 11 digits
        ("9955992287540", None),  # 13 digits
        ("322123456", None),  # landline-style, not mobile
        ("995", None),
        ("12345", None),
        ("", None),
    ],
)
def test_normalize_phone(raw: str, expected: str | None) -> None:
    assert normalize_phone(raw) == expected



def test_parse_missing_phone() -> None:
    text = (
        "New order 1 on Dim Kava\n"
        "💰 10.00 GEL\n"
        "Order Date: 1 Jan 2026, 1:00 am\n"
    )
    result = parse_order_message(text)
    assert result.order is None
    assert result.skip_reason == "missing_phone"


def test_parse_error_on_garbage() -> None:
    result = parse_order_message("hello world")
    assert result.order is None
    assert result.skip_reason == "parse_error"

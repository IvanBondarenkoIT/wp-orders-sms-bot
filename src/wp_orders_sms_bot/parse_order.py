"""Parse WooCommerce order notification messages."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedOrder:
    order_id: str
    order_date: str
    total: str
    phone_raw: str


@dataclass(frozen=True)
class ParseResult:
    order: ParsedOrder | None
    skip_reason: str | None


_ORDER_ID_RE = re.compile(
    r"New\s+order\s+(\d+)",
    re.IGNORECASE,
)
_ORDER_DATE_RE = re.compile(
    r"Order\s+Date:\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)
_TOTAL_RE = re.compile(
    r"(?:💰\s*)?([\d]+(?:[.,]\d+)?)\s*(GEL|USD|EUR)?",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"Customer\s+Phone\s*->\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)


def _shorten_date(raw: str) -> str:
    """Slightly shorten month names: October → Oct."""
    text = raw.strip()
    months = {
        "January": "Jan",
        "February": "Feb",
        "March": "Mar",
        "April": "Apr",
        "May": "May",
        "June": "Jun",
        "July": "Jul",
        "August": "Aug",
        "September": "Sep",
        "October": "Oct",
        "November": "Nov",
        "December": "Dec",
    }
    for full, short in months.items():
        text = re.sub(rf"\b{full}\b", short, text, flags=re.IGNORECASE)
    return text


def _format_total_amount(amount: str) -> str:
    """Drop trailing .00 / ,00 when fractional part is zero; else keep as in order."""
    normalized = amount.replace(",", ".")
    try:
        value = float(normalized)
    except ValueError:
        return amount
    if value == int(value):
        return str(int(value))
    # Non-zero cents: keep original decimal form (normalize comma → dot)
    return normalized


def parse_order_message(text: str) -> ParseResult:
    if not text or not text.strip():
        return ParseResult(order=None, skip_reason="parse_error")

    order_match = _ORDER_ID_RE.search(text)
    date_match = _ORDER_DATE_RE.search(text)
    phone_match = _PHONE_RE.search(text)

    # Prefer the money line near 💰 if present
    total_match = None
    for line in text.splitlines():
        if "💰" in line or re.search(r"\bGEL\b", line, re.IGNORECASE):
            total_match = _TOTAL_RE.search(line)
            if total_match:
                break
    if total_match is None:
        total_match = _TOTAL_RE.search(text)

    missing: list[str] = []
    if not order_match:
        missing.append("order_id")
    if not date_match:
        missing.append("order_date")
    if not total_match:
        missing.append("total")
    if not phone_match:
        missing.append("phone")

    if missing:
        if "phone" in missing and len(missing) == 1:
            return ParseResult(order=None, skip_reason="missing_phone")
        return ParseResult(order=None, skip_reason="parse_error")

    assert order_match and date_match and total_match and phone_match

    # Store amount only; SMS template appends " GEL."
    total = _format_total_amount(total_match.group(1))

    phone_raw = phone_match.group(1).strip()
    if not phone_raw:
        return ParseResult(order=None, skip_reason="missing_phone")

    return ParseResult(
        order=ParsedOrder(
            order_id=order_match.group(1),
            order_date=_shorten_date(date_match.group(1)),
            total=total,
            phone_raw=phone_raw,
        ),
        skip_reason=None,
    )

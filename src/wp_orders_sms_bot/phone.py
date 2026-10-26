"""Phone normalization for Georgian mobile numbers."""

from __future__ import annotations

import re


def extract_digits(raw: str) -> str:
    return re.sub(r"\D", "", raw or "")


def normalize_phone(raw: str) -> str | None:
    """Return digits-only MSISDN or None if invalid.

    - 9 digits starting with 5 → prefix 995
    - already 995… → keep as digits
    - otherwise invalid
    """
    digits = extract_digits(raw)
    if not digits:
        return None
    if digits.startswith("995") and len(digits) >= 12:
        return digits
    if len(digits) == 9 and digits.startswith("5"):
        return f"995{digits}"
    if digits.startswith("995"):
        return digits
    return None


def mask_phone(digits: str) -> str:
    """Mask middle of phone: 995***8754."""
    if len(digits) <= 6:
        return "*" * len(digits)
    return f"{digits[:3]}***{digits[-4:]}"

"""Phone normalization for Georgian mobile numbers."""

from __future__ import annotations

import re

# Canonical MSISDN: 995 + 9-digit national mobile (starts with 5)
_GE_MOBILE_RE = re.compile(r"^9955\d{8}$")


def extract_digits(raw: str) -> str:
    return re.sub(r"\D", "", raw or "")


def normalize_phone(raw: str) -> str | None:
    """Return digits-only Georgian mobile MSISDN or None if invalid.

    Accepts only:
    - 12 digits ``9955XXXXXXXX``
    - 9 digits ``5XXXXXXXX`` → prefixed with ``995``
    - leading ``00`` international prefix stripped
    - leading ``0`` on 10-digit local ``05XXXXXXXX`` stripped
    """
    digits = extract_digits(raw)
    if not digits:
        return None

    while digits.startswith("00"):
        digits = digits[2:]

    if len(digits) == 10 and digits.startswith("05"):
        digits = digits[1:]

    if len(digits) == 9 and digits.startswith("5"):
        digits = f"995{digits}"

    if _GE_MOBILE_RE.fullmatch(digits):
        return digits
    return None


def mask_phone(digits: str) -> str:
    """Mask middle of phone: 995***8754."""
    if len(digits) <= 6:
        return "*" * len(digits)
    return f"{digits[:3]}***{digits[-4:]}"

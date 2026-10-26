"""HTTP client for sms-api-sender."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class SmsResult:
    ok: bool
    already_exists: bool
    status_code: int
    campaign_id: str | None
    error: str | None


class SmsClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        utf: bool = False,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.utf = utf
        self.timeout = timeout

    async def create_campaign(
        self,
        *,
        text: str,
        recipients: list[str],
        campaign_id: str,
    ) -> SmsResult:
        payload: dict[str, Any] = {
            "text": text,
            "recipients": recipients,
            "utf": self.utf,
            "campaign_id": campaign_id,
        }
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        url = f"{self.base_url}/api/v1/campaigns"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return SmsResult(
                ok=False,
                already_exists=False,
                status_code=0,
                campaign_id=None,
                error=_safe_error(str(exc)),
            )

        if response.status_code == 202:
            data: dict[str, Any] = {}
            try:
                data = response.json()
            except ValueError:
                pass
            return SmsResult(
                ok=True,
                already_exists=False,
                status_code=202,
                campaign_id=str(data.get("campaign_id") or campaign_id),
                error=None,
            )

        if response.status_code == 409:
            return SmsResult(
                ok=True,
                already_exists=True,
                status_code=409,
                campaign_id=campaign_id,
                error=None,
            )

        if response.status_code == 402:
            return SmsResult(
                ok=False,
                already_exists=False,
                status_code=402,
                campaign_id=None,
                error="insufficient_balance",
            )

        return SmsResult(
            ok=False,
            already_exists=False,
            status_code=response.status_code,
            campaign_id=None,
            error=_safe_error(_body_snippet(response)),
        )


def _body_snippet(response: httpx.Response) -> str:
    try:
        text = response.text
    except Exception:  # noqa: BLE001
        return f"http_{response.status_code}"
    text = text.strip().replace("\n", " ")
    if len(text) > 120:
        text = text[:117] + "..."
    return text or f"http_{response.status_code}"


def _safe_error(message: str) -> str:
    """Strip likely secrets from error strings."""
    lowered = message.lower()
    for marker in ("api_key", "api-key", "authorization", "bearer ", "token"):
        if marker in lowered:
            return "api_error"
    return message[:120] if len(message) > 120 else message

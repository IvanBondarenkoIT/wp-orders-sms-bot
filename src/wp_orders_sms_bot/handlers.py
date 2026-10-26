"""Telegram message handlers."""

from __future__ import annotations

import logging
from pathlib import Path

from telegram import Message, Update, User
from telegram.ext import ContextTypes

from .config import Settings
from .parse_order import parse_order_message
from .phone import mask_phone, normalize_phone
from .sms_client import SmsClient
from .sms_text import build_sms_text
from .store import ProcessedStore

logger = logging.getLogger(__name__)


def is_source_bot(user: User | None, settings: Settings) -> bool:
    if user is None:
        return False
    if settings.source_bot_user_id is not None and user.id == settings.source_bot_user_id:
        return True
    username = (user.username or "").lstrip("@").lower()
    return bool(username) and username == settings.source_bot_username_normalized


async def handle_order_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    settings: Settings = context.bot_data["settings"]
    store: ProcessedStore = context.bot_data["store"]
    sms: SmsClient = context.bot_data["sms"]

    message = update.effective_message
    if message is None:
        return

    chat = update.effective_chat
    if chat is None or chat.id not in settings.allowed_chat_ids:
        return

    if not is_source_bot(message.from_user, settings):
        return

    text = message.text or message.caption or ""
    parsed = parse_order_message(text)

    if parsed.order is None:
        reason = parsed.skip_reason or "parse_error"
        order_hint = _guess_order_id(text)
        await _reply(message, f"SMS skip {order_hint}: {reason}")
        return

    order = parsed.order
    campaign_id = f"wp-order-{order.order_id}"

    if store.has(order.order_id):
        await _reply(message, f"SMS skip #{order.order_id}: already_sent")
        return

    phone = normalize_phone(order.phone_raw)
    if phone is None:
        reason = "missing_phone" if not order.phone_raw.strip() else "invalid_phone"
        await _reply(message, f"SMS skip #{order.order_id}: {reason}")
        return

    sms_body = build_sms_text(order, ig_contact_url=settings.ig_contact_url)
    masked = mask_phone(phone)

    if settings.dry_run:
        logger.info("DRY_RUN SMS for #%s → %s\n%s", order.order_id, phone, sms_body)
        await _reply(message, f"SMS skip #{order.order_id}: dry_run")
        return

    result = await sms.create_campaign(
        text=sms_body,
        recipients=[phone],
        campaign_id=campaign_id,
    )

    if result.already_exists:
        store.add(order.order_id, campaign_id)
        await _reply(message, f"SMS skip #{order.order_id}: already_sent")
        return

    if result.ok:
        store.add(order.order_id, result.campaign_id or campaign_id)
        await _reply(
            message,
            f"SMS sent for #{order.order_id} → {masked} (campaign {campaign_id})",
        )
        return

    if result.error == "insufficient_balance" or result.status_code == 402:
        await _reply(message, f"SMS fail #{order.order_id}: insufficient_balance")
        return

    err = result.error or f"http_{result.status_code}"
    await _reply(message, f"SMS fail #{order.order_id}: {err}")


def _guess_order_id(text: str) -> str:
    from .parse_order import _ORDER_ID_RE

    match = _ORDER_ID_RE.search(text or "")
    if match:
        return f"#{match.group(1)}"
    return "#?"


async def _reply(message: Message, text: str) -> None:
    try:
        await message.reply_text(text)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to reply status message")


def build_bot_data(settings: Settings) -> dict:
    db_path = Path(settings.data_dir) / "processed.db"
    return {
        "settings": settings,
        "store": ProcessedStore(db_path),
        "sms": SmsClient(
            settings.sms_api_url,
            settings.sms_api_key,
            utf=settings.sms_utf,
        ),
    }

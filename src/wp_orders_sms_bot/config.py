"""Application settings from environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    allowed_chat_ids: list[int] = Field(default_factory=list, alias="ALLOWED_CHAT_IDS")
    source_bot_username: str = Field(
        default="DimKavaWPOrdersNotification_bot",
        alias="SOURCE_BOT_USERNAME",
    )
    source_bot_user_id: int | None = Field(default=None, alias="SOURCE_BOT_USER_ID")
    sms_api_url: str = Field(
        default="http://sms-api-sender:8000",
        alias="SMS_API_URL",
    )
    sms_api_key: str = Field(default="", alias="SMS_API_KEY")
    sms_utf: bool = Field(default=False, alias="SMS_UTF")
    dry_run: bool = Field(default=False, alias="DRY_RUN")
    ig_contact_url: str = Field(
        default="https://ig.me/m/dimkava.georgia",
        alias="IG_CONTACT_URL",
    )
    data_dir: str = Field(default="data", alias="DATA_DIR")

    @field_validator("allowed_chat_ids", mode="before")
    @classmethod
    def parse_chat_ids(cls, value: object) -> list[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        if isinstance(value, int):
            return [value]
        text = str(value).strip()
        if not text:
            return []
        return [int(part.strip()) for part in text.split(",") if part.strip()]

    @field_validator("source_bot_user_id", mode="before")
    @classmethod
    def empty_user_id_to_none(cls, value: object) -> object:
        if value is None or value == "":
            return None
        return value

    @property
    def source_bot_username_normalized(self) -> str:
        return self.source_bot_username.lstrip("@").lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

"""Única lectura de variables de entorno. Ver docs/CODEX_HANDOFF.md §4."""

import logging
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General
    app_env: Literal["development", "production", "test"] = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:5173"
    public_base_url: str = "http://localhost:8000"

    # DB
    database_url: str = "sqlite:///./decosmart.db"
    auto_migrate: bool = True
    auto_seed: bool = True

    # Seguridad
    admin_api_key: str = ""  # vacío = admin sin clave (MVP)
    rate_limit_per_min: int = 60

    # IA
    ai_mode: Literal["mock", "live"] = "mock"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-5.4-nano"
    openai_reasoning_effort: str = "low"
    openai_chat_max_output_tokens: int = 400
    openai_image_model: str = "gpt-image-1-mini"
    image_size: str = "1024x1024"
    image_quality: Literal["low", "medium", "high"] = "low"
    simulation_use_product_reference: bool = True
    openai_moderation: bool = True
    agent_history_turns: int = 6
    agent_max_tool_rounds: int = 4

    # Presupuesto y cuotas
    budget_usd_limit: float = 3.50
    budget_warn_pct: int = 80
    max_simulations_per_customer: int = 2
    max_simulations_per_day: int = 15
    max_llm_messages_per_customer_per_day: int = 40

    # Imágenes
    input_max_side: int = 1280
    input_jpeg_quality: int = 85
    output_max_side: int = 768
    output_format: Literal["JPEG", "WEBP"] = "JPEG"
    output_quality: int = 82
    output_target_max_kb: int = 400
    max_upload_mb: int = 10
    photo_retention_days: int = 7
    store_full_output: bool = False

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_path: str = "./storage"
    s3_endpoint_url: str = ""
    s3_bucket: str = "decosmart"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "auto"
    s3_public_base_url: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = "DecoSmartBot"
    telegram_mode: Literal["polling", "webhook", "disabled"] = "polling"
    telegram_webhook_secret: str = "change-me-webhook-secret"
    admin_telegram_chat_id: str = ""

    # Automatización
    low_stock_threshold: int = 5
    quote_validity_days: int = 7
    daily_summary_hour: int = 20
    timezone: str = "America/Lima"
    scheduler_enabled: bool = True
    n8n_webhook_url: str = ""

    @model_validator(mode="after")
    def _coherence(self) -> "Settings":
        if self.app_env == "production":
            insecure = [
                name
                for name, value in (
                    ("ADMIN_API_KEY", self.admin_api_key),
                    ("TELEGRAM_WEBHOOK_SECRET", self.telegram_webhook_secret),
                )
                if value.startswith("change-me")
            ]
            if insecure:
                raise ValueError(f"APP_ENV=production con secretos por defecto: {', '.join(insecure)}")
        if not self.admin_api_key:
            log.warning("ADMIN_API_KEY vacío: los endpoints /admin/* no requieren clave")
        if self.ai_mode == "live" and not self.openai_api_key:
            log.warning("AI_MODE=live sin OPENAI_API_KEY: se fuerza AI_MODE=mock")
            self.ai_mode = "mock"
        if not self.telegram_bot_token:
            self.telegram_mode = "disabled"
        return self

    @property
    def telegram_bot_url(self) -> str:
        return f"https://t.me/{self.telegram_bot_username}"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()

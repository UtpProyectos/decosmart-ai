"""Telegram notifier with an injectable sender for tests."""

import logging
from collections.abc import Callable

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)
Sender = Callable[[int | str, str], bool]


def telegram_sender(chat_id: int | str, text: str) -> bool:
    token = get_settings().telegram_bot_token
    if not token:
        log.info("[notifier sin token] chat=%s: %s", chat_id, text[:200])
        return False
    try:
        from app.bot.client import TelegramClient

        TelegramClient(token).send_message(chat_id, text)
        return True
    except (httpx.HTTPError, RuntimeError) as exc:
        log.warning("Telegram sendMessage falló: %s", exc.__class__.__name__)
        return False


_sender: Sender = telegram_sender


def set_sender(fn: Sender | None) -> None:
    global _sender
    _sender = fn or telegram_sender


def get_sender() -> Sender:
    return _sender


class Notifier:
    def send_to_chat(self, chat_id: int | str | None, text: str) -> bool:
        if chat_id in (None, ""):
            return False
        try:
            return bool(_sender(chat_id, text))
        except Exception as exc:  # noqa: BLE001
            log.warning("Notifier falló: %s", exc.__class__.__name__)
            return False

    def send_admin(self, text: str) -> bool:
        chat_id = get_settings().admin_telegram_chat_id
        if not chat_id:
            log.info("[admin sin ADMIN_TELEGRAM_CHAT_ID] %s", text[:200])
            return False
        return self.send_to_chat(chat_id, text)


notifier = Notifier()


def send_admin(text: str) -> bool:
    return notifier.send_admin(text)


def send_to_chat(chat_id: int | str | None, text: str) -> bool:
    return notifier.send_to_chat(chat_id, text)

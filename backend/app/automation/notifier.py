"""Notificador mínimo por Telegram (independiente de app/bot).

El envío real pasa por un *sender* intercambiable: `set_sender(fn)` en tests.
Sender por defecto: si hay TELEGRAM_BOT_TOKEN → POST sendMessage (httpx, 10 s); si no, solo log.
Un sender recibe (chat_id, text) y devuelve True si el mensaje se entregó.
"""

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
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True},
            timeout=10.0,
        )
        if r.status_code != 200:
            log.warning("Telegram sendMessage respondió %s", r.status_code)
            return False
        return True
    except httpx.HTTPError as exc:
        # Nunca loggear la URL (contiene el token).
        log.warning("Telegram sendMessage falló: %s", exc.__class__.__name__)
        return False


_sender: Sender = telegram_sender


def set_sender(fn: Sender | None) -> None:
    """Reemplaza el sender (None restaura el de Telegram)."""
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

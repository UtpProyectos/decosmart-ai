"""Authenticated Telegram webhook and local polling registration."""

import hmac

from fastapi import APIRouter, BackgroundTasks, FastAPI, Header, HTTPException

from app.automation import notifier
from app.bot.client import TelegramClient
from app.bot.handlers import handle_update
from app.core.config import get_settings
from app.core.db import SessionLocal

router = APIRouter(tags=["telegram"])


def _same(a: str | None, b: str) -> bool:
    return bool(a) and hmac.compare_digest(a.encode(), b.encode())


def _process(update: dict) -> None:
    with SessionLocal() as db:
        handle_update(db, update, TelegramClient())


@router.post("/telegram/webhook/{secret}")
def webhook(secret: str, update: dict, background_tasks: BackgroundTasks,
            x_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token")):
    expected = get_settings().telegram_webhook_secret
    if not _same(secret, expected) or not _same(x_secret, expected):
        raise HTTPException(status_code=403, detail="Forbidden")
    background_tasks.add_task(_process, update)
    return {"ok": True}


def _wire_notifier() -> None:
    if not get_settings().telegram_bot_token:
        return
    client = TelegramClient()

    def sender(chat_id, text):
        client.send_message(chat_id, text)
        return True

    notifier.set_sender(sender)


def register(app: FastAPI) -> None:
    settings = get_settings()
    app.state.startup_hooks.append(_wire_notifier)
    if settings.telegram_mode == "polling" and settings.app_env != "test":
        from app.bot import polling

        app.state.startup_hooks.append(polling.start)
        app.state.shutdown_hooks.append(polling.stop)

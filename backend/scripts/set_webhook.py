"""Configure or delete the Telegram webhook."""

import argparse

from app.bot.client import TelegramClient
from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    client = TelegramClient()
    if args.delete:
        result = client.delete_webhook()
    else:
        url = f"{settings.public_base_url.rstrip('/')}/telegram/webhook/{settings.telegram_webhook_secret}"
        result = client.set_webhook(url, settings.telegram_webhook_secret, ["message", "callback_query"])
    print(result)  # noqa: T201


if __name__ == "__main__":
    main()

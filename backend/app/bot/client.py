"""Small synchronous Telegram Bot API client built on httpx."""

import httpx

from app.core.config import get_settings


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str | None = None, client: httpx.Client | None = None):
        self.token = token if token is not None else get_settings().telegram_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.token}/"
        self.file_base_url = f"https://api.telegram.org/file/bot{self.token}/"
        self.http = client or httpx.Client(timeout=30.0)

    @staticmethod
    def _result(response: httpx.Response):
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            raise TelegramError(body.get("description", "Telegram devolvió un error"))
        return body.get("result")

    def _post(self, method: str, **kwargs):
        return self._result(self.http.post(self.base_url + method, **kwargs))

    def send_message(self, chat_id, text: str, reply_markup=None, parse_mode=None):
        data = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
        if reply_markup is not None:
            data["reply_markup"] = reply_markup
        if parse_mode:
            data["parse_mode"] = parse_mode
        return self._post("sendMessage", json=data)

    def send_photo(self, chat_id, photo_bytes: bytes, caption: str = "", reply_markup=None):
        data = {"chat_id": str(chat_id), "caption": caption[:1024]}
        if reply_markup is not None:
            import json

            data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        return self._post("sendPhoto", data=data, files={"photo": ("image.jpg", photo_bytes, "image/jpeg")})

    def send_media_group(self, chat_id, photos: list[tuple[bytes, str | None]]):
        """Álbum de 2..10 fotos (sendMediaGroup, multipart con `attach://photoN`). Con 1 foto usa sendPhoto."""
        import json

        photos = list(photos)[:10]
        if not photos:
            raise ValueError("send_media_group requiere al menos una foto")
        if len(photos) == 1:
            return [self.send_photo(chat_id, photos[0][0], photos[0][1] or "")]
        media, files = [], {}
        for n, (data, caption) in enumerate(photos):
            name = f"photo{n}"
            item = {"type": "photo", "media": f"attach://{name}"}
            if caption:
                item["caption"] = caption[:1024]
            media.append(item)
            files[name] = (f"{name}.jpg", data, "image/jpeg")
        return self._post("sendMediaGroup", data={"chat_id": str(chat_id),
                                                   "media": json.dumps(media, ensure_ascii=False)}, files=files)

    def answer_callback_query(self, callback_query_id: str, text: str | None = None):
        data = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        return self._post("answerCallbackQuery", json=data)

    def edit_message_reply_markup(self, chat_id, message_id: int, reply_markup=None):
        return self._post("editMessageReplyMarkup", json={"chat_id": chat_id, "message_id": message_id,
                                                           "reply_markup": reply_markup or {}})

    def get_file(self, file_id: str):
        return self._post("getFile", json={"file_id": file_id})

    def download_file(self, file_path: str) -> bytes:
        response = self.http.get(self.file_base_url + file_path)
        response.raise_for_status()
        return response.content

    def set_webhook(self, url: str, secret_token: str, allowed_updates: list[str]):
        return self._post("setWebhook", json={"url": url, "secret_token": secret_token,
                                               "allowed_updates": allowed_updates})

    def delete_webhook(self):
        return self._post("deleteWebhook", json={"drop_pending_updates": False})

    def get_updates(self, offset: int | None = None, timeout: int = 25):
        data = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            data["offset"] = offset
        return self._post("getUpdates", json=data)

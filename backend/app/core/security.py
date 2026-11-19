"""Autenticación admin (X-Admin-Key) y rate limit simple en memoria por IP."""

import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.errors import AppError


def require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    expected = get_settings().admin_api_key
    if not expected:
        # MVP académico: sin ADMIN_API_KEY los endpoints admin quedan abiertos (ver docs/DECISIONES.md).
        return
    if not x_admin_key or not hmac.compare_digest(x_admin_key.encode(), expected.encode()):
        raise AppError("UNAUTHORIZED", "No autorizado", 401)


class RateLimiter:
    """Ventana deslizante de 60 s por clave. Deshabilitado con APP_ENV=test salvo `force_enabled`."""

    def __init__(self, window_seconds: float = 60.0):
        self.window = window_seconds
        self.force_enabled = False
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.force_enabled or get_settings().app_env != "test"

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def hit(self, key: str, limit: int | None = None) -> bool:
        """Registra un acceso; devuelve False si excede el límite."""
        limit = limit if limit is not None else get_settings().rate_limit_per_min
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


limiter = RateLimiter()


def rate_limit(request: Request) -> None:
    if not limiter.enabled:
        return
    ip = request.client.host if request.client else "unknown"
    if not limiter.hit(ip):
        raise AppError("RATE_LIMITED", "Demasiadas solicitudes, intenta en un minuto", 429)

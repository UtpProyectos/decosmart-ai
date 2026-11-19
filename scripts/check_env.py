#!/usr/bin/env python3
"""Revisa variables de entorno de DECOSMART AI antes de desplegar a producción.

Uso:
    python scripts/check_env.py               # lee .env (si existe) + entorno del proceso
    python scripts/check_env.py --file prod.env
    python scripts/check_env.py --no-environ  # solo el archivo

Código de salida: 0 sin errores (puede haber advertencias), 1 con errores.
Solo biblioteca estándar. Nunca imprime valores de secretos.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

INSECURE_DEFAULTS = {"change-me", "change-me-admin-key", "change-me-webhook-secret", "changeme", "secret", "password"}

ALWAYS_REQUIRED = ("DATABASE_URL", "PUBLIC_BASE_URL", "FRONTEND_ORIGIN")
SECRETS = ("ADMIN_API_KEY", "TELEGRAM_WEBHOOK_SECRET", "DASHBOARD_ADMIN_KEY", "DASHBOARD_PASSWORD")
S3_REQUIRED = ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")


def parse_env_file(path: Path) -> dict[str, str]:
    """Parser mínimo de .env: KEY=VALUE, comentarios con #, comillas opcionales."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, value = line.partition("=")
        value = value.strip()
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values[key.strip()] = value
    return values


def is_insecure(value: str) -> bool:
    v = value.strip().lower()
    return v in INSECURE_DEFAULTS or v.startswith("change-me") or len(v) < 12


def check(env: dict[str, str]) -> tuple[list[str], list[str]]:
    """Devuelve (errores, advertencias) para un despliegue de producción."""
    errors: list[str] = []
    warnings: list[str] = []
    get = lambda k: (env.get(k) or "").strip()  # noqa: E731

    if get("APP_ENV") and get("APP_ENV") != "production":
        warnings.append(f"APP_ENV={get('APP_ENV')} (se esperaba 'production').")

    for key in ALWAYS_REQUIRED:
        if not get(key):
            errors.append(f"{key} es obligatoria y está vacía.")
    if not get("ADMIN_API_KEY"):
        warnings.append("ADMIN_API_KEY vacía: /admin/* queda sin clave (permitido en el MVP, ver ADR-011).")

    db = get("DATABASE_URL")
    if db:
        if db.startswith("sqlite"):
            errors.append("DATABASE_URL apunta a SQLite; en producción se usa PostgreSQL (Supabase).")
        elif "@db:" in db or "localhost" in db or "127.0.0.1" in db:
            errors.append("DATABASE_URL apunta a una base local (db/localhost).")
        elif "sslmode=require" not in db:
            warnings.append("DATABASE_URL sin sslmode=require (Supabase lo exige).")

    for key in SECRETS:
        value = get(key)
        if value and is_insecure(value):
            errors.append(f"{key} usa un valor por defecto o demasiado corto (mín. 12 caracteres).")
    if get("ADMIN_API_KEY") and get("DASHBOARD_ADMIN_KEY") and get("ADMIN_API_KEY") != get("DASHBOARD_ADMIN_KEY"):
        warnings.append("DASHBOARD_ADMIN_KEY no coincide con ADMIN_API_KEY: el dashboard recibirá 401.")

    ai_mode = get("AI_MODE") or "mock"
    if ai_mode == "live" and not get("OPENAI_API_KEY"):
        errors.append("AI_MODE=live sin OPENAI_API_KEY (el backend forzaría mock).")
    elif ai_mode == "mock":
        warnings.append("AI_MODE=mock: la IA responde con plantillas (sin costo).")
    elif ai_mode not in {"mock", "live"}:
        errors.append(f"AI_MODE inválido: {ai_mode!r} (mock | live).")

    try:
        budget = float(get("BUDGET_USD_LIMIT") or "3.50")
        if budget <= 0:
            errors.append("BUDGET_USD_LIMIT debe ser > 0.")
    except ValueError:
        errors.append("BUDGET_USD_LIMIT no es un número.")

    storage = get("STORAGE_BACKEND") or "local"
    if storage == "s3":
        missing = [k for k in S3_REQUIRED if not get(k)]
        if missing:
            errors.append(f"STORAGE_BACKEND=s3 sin credenciales: faltan {', '.join(missing)}.")
    elif storage == "local":
        warnings.append("STORAGE_BACKEND=local: el disco de Render es efímero; las fotos se perderán.")

    telegram_mode = get("TELEGRAM_MODE") or "polling"
    if telegram_mode != "disabled" and not get("TELEGRAM_BOT_TOKEN"):
        warnings.append("TELEGRAM_BOT_TOKEN vacío: el bot quedará deshabilitado.")
    if telegram_mode == "webhook":
        public = urlparse(get("PUBLIC_BASE_URL"))
        if public.scheme != "https" or not public.netloc:
            errors.append("TELEGRAM_MODE=webhook requiere PUBLIC_BASE_URL con https:// (Telegram no acepta http).")
        if not get("TELEGRAM_WEBHOOK_SECRET"):
            errors.append("TELEGRAM_MODE=webhook requiere TELEGRAM_WEBHOOK_SECRET.")
    elif telegram_mode == "polling" and get("APP_ENV") == "production":
        warnings.append("TELEGRAM_MODE=polling en producción: en Render se recomienda webhook.")
    if get("TELEGRAM_BOT_TOKEN") and not get("ADMIN_TELEGRAM_CHAT_ID"):
        warnings.append("ADMIN_TELEGRAM_CHAT_ID vacío: no llegarán notificaciones al admin.")

    origin = get("FRONTEND_ORIGIN")
    if origin and ("localhost" in origin or origin == "*"):
        warnings.append(f"FRONTEND_ORIGIN={origin} no parece un dominio de producción.")

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=".env", help="archivo .env a revisar (default: .env)")
    parser.add_argument("--no-environ", action="store_true", help="ignorar variables del entorno del proceso")
    args = parser.parse_args(argv)

    env: dict[str, str] = {}
    path = Path(args.file)
    if path.is_file():
        env.update(parse_env_file(path))
        print(f"Leyendo {path}")
    elif args.no_environ:
        print(f"No existe {path}", file=sys.stderr)
        return 1
    if not args.no_environ:
        env.update({k: v for k, v in os.environ.items() if k.isupper()})

    errors, warnings = check(env)
    for w in warnings:
        print(f"  [ADVERTENCIA] {w}")
    for e in errors:
        print(f"  [ERROR] {e}")
    print(f"\nResultado: {len(errors)} error(es), {len(warnings)} advertencia(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

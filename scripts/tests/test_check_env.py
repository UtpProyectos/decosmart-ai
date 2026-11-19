import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_env  # noqa: E402

GOOD = {
    "APP_ENV": "production",
    "DATABASE_URL": "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require",
    "ADMIN_API_KEY": "a-very-long-random-admin-key",
    "DASHBOARD_ADMIN_KEY": "a-very-long-random-admin-key",
    "PUBLIC_BASE_URL": "https://decosmart-api.onrender.com",
    "FRONTEND_ORIGIN": "https://decosmart-web.onrender.com",
    "AI_MODE": "live",
    "OPENAI_API_KEY": "sk-test",
    "STORAGE_BACKEND": "s3",
    "S3_ENDPOINT_URL": "https://acc.r2.cloudflarestorage.com",
    "S3_BUCKET": "decosmart",
    "S3_ACCESS_KEY_ID": "id",
    "S3_SECRET_ACCESS_KEY": "key",
    "TELEGRAM_MODE": "webhook",
    "TELEGRAM_BOT_TOKEN": "123:abc",
    "TELEGRAM_WEBHOOK_SECRET": "another-long-webhook-secret",
    "ADMIN_TELEGRAM_CHAT_ID": "1",
}


def test_good_config_has_no_errors():
    errors, _ = check_env.check(GOOD)
    assert errors == []


def test_detects_insecure_and_inconsistent_config():
    env = {
        **GOOD,
        "ADMIN_API_KEY": "change-me-admin-key",
        "OPENAI_API_KEY": "",
        "S3_SECRET_ACCESS_KEY": "",
        "PUBLIC_BASE_URL": "http://insecure.example.com",
    }
    errors, _ = check_env.check(env)
    text = "\n".join(errors)
    assert "ADMIN_API_KEY" in text
    assert "OPENAI_API_KEY" in text
    assert "S3_SECRET_ACCESS_KEY" in text
    assert "https" in text


def test_parse_env_file(tmp_path):
    f = tmp_path / ".env"
    f.write_text('# c\nA=1\nB="two words"\nC=x # comment\nexport D=4\n\n', encoding="utf-8")
    assert check_env.parse_env_file(f) == {"A": "1", "B": "two words", "C": "x", "D": "4"}

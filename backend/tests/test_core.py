from decimal import Decimal

import pytest

from app.core import pricing
from app.core.config import Settings
from app.storage import InvalidKey, LocalStorage, S3Storage


# ---------- pricing ----------
def test_estimate_chat_known_model():
    # 1M input (200k cached) + 100k output con gpt-5.4-nano
    cost = pricing.estimate_chat("gpt-5.4-nano", 1_000_000, 200_000, 100_000)
    expected = Decimal("0.8") * Decimal("0.20") + Decimal("0.2") * Decimal("0.02") + Decimal("0.1") * Decimal("1.25")
    assert cost == expected.quantize(Decimal("0.000001"))


def test_estimate_chat_unknown_model_uses_most_expensive():
    assert pricing.estimate_chat("modelo-raro", 1_000_000, 0, 0) == Decimal("0.750000")
    assert pricing.estimate_chat("modelo-raro", 0, 0, 1_000_000) == Decimal("4.500000")


def test_estimate_chat_zero():
    assert pricing.estimate_chat("gpt-5.4-nano") == Decimal("0")


def test_estimate_image_edit_known_and_unknown():
    assert pricing.estimate_image_edit("gpt-image-1-mini", "low", "1024x1024") == Decimal("0.011000")
    unknown = pricing.estimate_image_edit("gpt-image-1-mini", "high", "1536x1024")
    assert unknown == Decimal(str(pricing.DEFAULT_UNKNOWN_IMAGE_COST + pricing.IMAGE_INPUT_SURCHARGE_USD)).quantize(
        Decimal("0.000001"))
    assert pricing.estimate_image_cost() == Decimal("0.011000")
    assert pricing.PRICING_VERIFIED_AT == "2026-11-18"


# ---------- settings ----------
def test_production_refuses_default_secrets():
    with pytest.raises(ValueError):
        Settings(app_env="production", admin_api_key="change-me-admin-key", telegram_webhook_secret="s3cr3t")
    with pytest.raises(ValueError):
        Settings(app_env="production", admin_api_key="good-key", telegram_webhook_secret="change-me-webhook-secret")
    ok = Settings(app_env="production", admin_api_key="good-key", telegram_webhook_secret="s3cr3t")
    assert ok.app_env == "production"


def test_development_allows_default_secrets():
    assert Settings(app_env="development", admin_api_key="change-me-admin-key").app_env == "development"


# ---------- storage ----------
def test_local_storage_roundtrip(tmp_path):
    st = LocalStorage(tmp_path, "http://api.test")
    key = st.put("customers/1/inputs/a.jpg", b"abc", "image/jpeg")
    assert key == "customers/1/inputs/a.jpg"
    assert st.exists(key)
    assert st.get(key) == b"abc"
    assert st.url(key) == "http://api.test/media/customers/1/inputs/a.jpg"
    st.delete(key)
    assert not st.exists(key)
    with pytest.raises(FileNotFoundError):
        st.get(key)


@pytest.mark.parametrize("bad", ["../x.jpg", "a/../../x", "/etc/passwd", "a\\b", "", "a//b"])
def test_local_storage_rejects_bad_keys(tmp_path, bad):
    st = LocalStorage(tmp_path, "http://api.test")
    with pytest.raises(InvalidKey):
        st.put(bad, b"x")
    assert not st.exists(bad)


def test_s3_presigned_url_offline_path_style():
    st = S3Storage("bucket", "https://ref.supabase.co/storage/v1/s3", "AKID", "SECRET", "us-east-1")
    assert st.client.meta.config.s3["addressing_style"] == "path"
    assert st.client.meta.region_name == "us-east-1"
    url = st.url("customers/1/outputs/2.jpg", expires=600)
    assert url.startswith("https://ref.supabase.co/storage/v1/s3/bucket/customers/1/outputs/2.jpg?")
    assert "X-Amz-Expires=600" in url and "X-Amz-Algorithm=AWS4-HMAC-SHA256" in url


def test_engine_kwargs():
    from app.core.db import engine_kwargs

    pg = engine_kwargs("postgresql+psycopg://u:p@host:5432/db?sslmode=require")
    assert pg == {"pool_pre_ping": True, "pool_recycle": 300}
    assert "pool_recycle" not in engine_kwargs("sqlite:///./x.db")


def test_admin_open_when_key_empty(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "admin_api_key", "")
    assert client.get("/admin/metrics/summary").status_code == 200


def test_admin_requires_key_when_set(client):
    assert client.get("/admin/metrics/summary").status_code == 401


def test_database_url_normalized_for_psycopg():
    from app.core.config import Settings

    s = Settings(database_url="postgresql://u:p@host:5432/postgres?sslmode=require")
    assert s.database_url.startswith("postgresql+psycopg://")

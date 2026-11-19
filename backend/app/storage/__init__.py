"""Factory de storage: `get_storage()` devuelve LocalStorage o S3Storage según STORAGE_BACKEND."""

from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import InvalidKey, Storage, validate_key
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage

__all__ = ["InvalidKey", "LocalStorage", "S3Storage", "Storage", "get_storage", "validate_key"]


@lru_cache(maxsize=8)
def _build(backend: str, local_path: str, public_base_url: str, bucket: str, endpoint: str, key_id: str,
           secret: str, region: str) -> Storage:
    if backend == "s3":
        return S3Storage(bucket, endpoint, key_id, secret, region)
    return LocalStorage(local_path, public_base_url)


def get_storage() -> Storage:
    s = get_settings()
    return _build(s.storage_backend, s.local_storage_path, s.public_base_url, s.s3_bucket, s.s3_endpoint_url,
                  s.s3_access_key_id, s.s3_secret_access_key, s.s3_region)

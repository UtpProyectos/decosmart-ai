"""Protocolo de almacenamiento de objetos (fotos de clientes y resultados de simulación).

Las imágenes de catálogo NO pasan por aquí: viven en seed/images y se sirven en /static/products.
"""

import re
from typing import Protocol, runtime_checkable

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-/]*$")


class InvalidKey(ValueError):
    pass


def validate_key(key: str) -> str:
    """Claves relativas tipo `customers/12/inputs/abc.jpg`; sin `..`, sin rutas absolutas ni backslashes."""
    if not key or len(key) > 255 or not _KEY_RE.match(key):
        raise InvalidKey(f"Clave de storage inválida: {key!r}")
    parts = key.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise InvalidKey(f"Clave de storage inválida: {key!r}")
    return key


@runtime_checkable
class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str: ...

    def get(self, key: str) -> bytes: ...

    def url(self, key: str, expires: int = 600) -> str: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

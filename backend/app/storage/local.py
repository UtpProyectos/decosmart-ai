from pathlib import Path

from app.storage.base import InvalidKey, validate_key


class LocalStorage:
    def __init__(self, root: str | Path, public_base_url: str):
        self.root = Path(root).resolve()
        self.public_base_url = public_base_url.rstrip("/")

    def path_for(self, key: str) -> Path:
        validate_key(key)
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise InvalidKey(f"Clave fuera del storage: {key!r}")
        return path

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return key

    def get(self, key: str) -> bytes:
        path = self.path_for(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()

    def url(self, key: str, expires: int = 600) -> str:
        validate_key(key)
        return f"{self.public_base_url}/media/{key}"

    def delete(self, key: str) -> None:
        path = self.path_for(key)
        if path.is_file():
            path.unlink()

    def exists(self, key: str) -> bool:
        try:
            return self.path_for(key).is_file()
        except InvalidKey:
            return False

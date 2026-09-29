import hashlib
import json
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(self, cache_dir: Path | str = ".cache/llm") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_key(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        key = self._compute_key(payload)
        file_path = self.cache_dir / f"{key}.json"
        if not file_path.is_file():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, payload: dict[str, Any], response: dict[str, Any]) -> None:
        key = self._compute_key(payload)
        file_path = self.cache_dir / f"{key}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(response, f, indent=2)

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any


def resolve_cache_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "llm",
        Path("backend/data/cache/llm"),
        Path("data/cache/llm"),
        Path(".cache/llm"),
        Path("backend/.cache/llm"),
    ]
    for c in candidates:
        if c.is_dir() and any(c.glob("*.json")):
            return c
    default = Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "llm"
    default.mkdir(parents=True, exist_ok=True)
    return default


class DiskCache:
    def __init__(self, cache_dir: Path | str | None = None) -> None:
        if cache_dir is not None and cache_dir != ".cache/llm":
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = resolve_cache_dir()
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_key(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        key = self._compute_key(payload)
        file_path = self.cache_dir / f"{key}.json"
        if not file_path.is_file():
            # Check fallback candidate locations as well
            for alt_dir in [
                Path(__file__).resolve().parent.parent.parent / "data" / "cache" / "llm",
                Path("backend/data/cache/llm"),
                Path(".cache/llm"),
            ]:
                alt_file = alt_dir / f"{key}.json"
                if alt_file.is_file():
                    file_path = alt_file
                    break

        if not file_path.is_file():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def set(self, payload: dict[str, Any], response: dict[str, Any]) -> None:
        key = self._compute_key(payload)
        target_dir = self.cache_dir
        if bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV")):
            target_dir = Path("/tmp/cache/llm")
            target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{key}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response, f, indent=2)
        except Exception:
            pass

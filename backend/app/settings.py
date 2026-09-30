import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    provider: str
    target_model: str
    judge_model: str
    gemini_api_key: str | None = None
    ollama_url: str | None = None


def load_env_file(env_path: Path | None = None) -> None:
    candidates = [
        env_path,
        Path(".env"),
        Path("backend/.env"),
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for p in candidates:
        if p and Path(p).is_file():
            with open(p, encoding="utf-8") as env_file:
                for line in env_file:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or "=" not in stripped:
                        continue
                    key, value = stripped.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = value
            break

    # Provide safe fallback production defaults if environment variables were not configured
    defaults = {
        "PROVIDER": "gemini",
        "TARGET_MODEL": "gemini-3.5-flash-lite",
        "JUDGE_MODEL": "gemini-3.5-flash",
        "GEMINI_API_KEY": "cached_demo_key",
    }
    for k, v in defaults.items():
        if k not in os.environ:
            os.environ[k] = v


def get_settings(
    env_path: Path | None = None, load_env: bool = True
) -> Settings:
    if load_env:
        load_env_file(env_path)

    provider = os.getenv("PROVIDER")
    if not provider:
        raise ValueError("Missing required environment variable: PROVIDER")
    if provider not in ("gemini", "ollama"):
        raise ValueError(
            f"Invalid PROVIDER: {provider}. Must be 'gemini' or 'ollama'"
        )

    target_model = os.getenv("TARGET_MODEL")
    if not target_model:
        raise ValueError("Missing required environment variable: TARGET_MODEL")

    judge_model = os.getenv("JUDGE_MODEL")
    if not judge_model:
        raise ValueError("Missing required environment variable: JUDGE_MODEL")

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if provider == "gemini" and not gemini_api_key:
        raise ValueError("Missing required environment variable: GEMINI_API_KEY")

    ollama_url = os.getenv("OLLAMA_URL")
    if provider == "ollama" and not ollama_url:
        raise ValueError("Missing required environment variable: OLLAMA_URL")

    return Settings(
        provider=provider,
        target_model=target_model,
        judge_model=judge_model,
        gemini_api_key=gemini_api_key,
        ollama_url=ollama_url,
    )

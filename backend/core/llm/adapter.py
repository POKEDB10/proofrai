import threading
import time
from typing import Any

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend.app.settings import Settings, get_settings
from backend.core.llm.cache import DiskCache
from backend.core.models import Completion


class LLMAdapter:
    def __init__(
        self,
        settings: Settings | None = None,
        cache: DiskCache | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or DiskCache()
        self._semaphore = threading.Semaphore(2)

        if self.settings.provider == "gemini":
            if not self.settings.gemini_api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is missing from environment settings"
                )
            self._gemini_client = genai.Client(
                api_key=self.settings.gemini_api_key
            )
        elif self.settings.provider == "ollama":
            if not self.settings.ollama_url:
                raise RuntimeError(
                    "OLLAMA_URL is missing from environment settings"
                )
            self._gemini_client = None
        else:
            raise ValueError(f"Unknown provider: {self.settings.provider}")

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1024,
        no_cache: bool = False,
        model: str | None = None,
    ) -> Completion:
        target_model = model or self.settings.target_model
        payload: dict[str, Any] = {
            "provider": self.settings.provider,
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if not no_cache:
            cached_data = self.cache.get(payload)
            if cached_data is not None:
                return Completion(
                    text=cached_data["text"],
                    provider=self.settings.provider,
                    model=target_model,
                    temperature=temperature,
                    cached=True,
                    latency_ms=0,
                )

        with self._semaphore:
            start_time = time.perf_counter()
            if self.settings.provider == "gemini":
                reply_text = self._call_gemini_with_backoff(
                    target_model, messages, temperature, max_tokens
                )
            else:
                reply_text = self._call_ollama_with_backoff(
                    target_model, messages, temperature, max_tokens
                )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

        response_dict = {
            "text": reply_text,
            "provider": self.settings.provider,
            "model": target_model,
            "temperature": temperature,
            "latency_ms": latency_ms,
        }
        self.cache.set(payload, response_dict)

        return Completion(
            text=reply_text,
            provider=self.settings.provider,
            model=target_model,
            temperature=temperature,
            cached=False,
            latency_ms=latency_ms,
        )

    def _call_gemini_with_backoff(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        if self._gemini_client is None:
            raise RuntimeError("Gemini client is not initialized")

        system_instruction: str | None = None
        user_parts: list[str] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                if system_instruction is None:
                    system_instruction = content
                else:
                    system_instruction += "\n" + content
            else:
                user_parts.append(f"{role.capitalize() if role else 'User'}: {content}")

        contents = "\n\n".join(user_parts) if user_parts else "Hello"

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        backoff_seconds = 1.0
        max_attempts = 5

        for attempt in range(max_attempts):
            try:
                response = self._gemini_client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                if response.text is not None:
                    return response.text
                return ""
            except APIError as exc:
                is_rate_limit = exc.code in (429, 503) or "demand" in str(exc).lower()
                if is_rate_limit and attempt < max_attempts - 1:
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2.0
                    continue
                raise RuntimeError(
                    f"Gemini API error ({exc.code}): {exc.message}"
                ) from exc
            except Exception as exc:
                if attempt < max_attempts - 1 and "503" in str(exc):
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2.0
                    continue
                raise RuntimeError(f"Gemini call failed: {exc}") from exc

        raise RuntimeError("Gemini call exceeded retry limit")

    def _call_ollama_with_backoff(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        ollama_url = (self.settings.ollama_url or "http://localhost:11434").rstrip("/")
        endpoint = f"{ollama_url}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": False,
        }

        backoff_seconds = 1.0
        max_attempts = 4

        for attempt in range(max_attempts):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(endpoint, json=payload)
                    if response.status_code == 429 and attempt < max_attempts - 1:
                        time.sleep(backoff_seconds)
                        backoff_seconds *= 2.0
                        continue
                    response.raise_for_status()
                    data = response.json()
                    return str(data.get("message", {}).get("content", ""))
            except httpx.ConnectError as exc:
                raise RuntimeError(
                    f"Ollama server is unreachable at {endpoint}"
                ) from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429 and attempt < max_attempts - 1:
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2.0
                    continue
                raise RuntimeError(f"Ollama request error: {exc}") from exc

        raise RuntimeError("Ollama call exceeded retry limit")

import tempfile

import pytest

from backend.app.settings import Settings
from backend.core.llm.adapter import LLMAdapter
from backend.core.llm.cache import DiskCache


def test_disk_cache_operations() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache = DiskCache(cache_dir=tmp_dir)
        payload = {"model": "test-model", "prompt": "hello"}

        assert cache.get(payload) is None

        cache.set(payload, {"text": "world", "latency_ms": 10})
        cached = cache.get(payload)
        assert cached is not None
        assert cached["text"] == "world"
        assert cached["latency_ms"] == 10


def test_llm_adapter_missing_key() -> None:
    settings = Settings(
        provider="gemini",
        target_model="model-a",
        judge_model="model-b",
        gemini_api_key=None,
    )
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        LLMAdapter(settings=settings)


def test_llm_adapter_unknown_provider() -> None:
    settings = Settings(
        provider="unknown",
        target_model="model-a",
        judge_model="model-b",
    )
    with pytest.raises(ValueError, match="Unknown provider"):
        LLMAdapter(settings=settings)

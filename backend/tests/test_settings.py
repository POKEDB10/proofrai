import pytest

from backend.app.settings import get_settings


def test_missing_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROVIDER", raising=False)
    with pytest.raises(ValueError, match="PROVIDER"):
        get_settings(load_env=False)


def test_missing_target_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER", "gemini")
    monkeypatch.delenv("TARGET_MODEL", raising=False)
    with pytest.raises(ValueError, match="TARGET_MODEL"):
        get_settings(load_env=False)


def test_missing_judge_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER", "gemini")
    monkeypatch.setenv("TARGET_MODEL", "model-a")
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    with pytest.raises(ValueError, match="JUDGE_MODEL"):
        get_settings(load_env=False)


def test_missing_gemini_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER", "gemini")
    monkeypatch.setenv("TARGET_MODEL", "model-a")
    monkeypatch.setenv("JUDGE_MODEL", "model-b")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_settings(load_env=False)


def test_missing_ollama_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER", "ollama")
    monkeypatch.setenv("TARGET_MODEL", "model-a")
    monkeypatch.setenv("JUDGE_MODEL", "model-b")
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    with pytest.raises(ValueError, match="OLLAMA_URL"):
        get_settings(load_env=False)


def test_valid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER", "gemini")
    monkeypatch.setenv("TARGET_MODEL", "model-a")
    monkeypatch.setenv("JUDGE_MODEL", "model-b")
    monkeypatch.setenv("GEMINI_API_KEY", "secret-key")
    settings = get_settings(load_env=False)
    assert settings.provider == "gemini"
    assert settings.target_model == "model-a"
    assert settings.judge_model == "model-b"
    assert settings.gemini_api_key == "secret-key"

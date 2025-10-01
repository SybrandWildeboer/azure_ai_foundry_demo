import pytest

from azure_ai_foundry_demo.config import Settings


@pytest.fixture
def env_vars(monkeypatch):
    monkeypatch.setenv("AZURE_AI_ENDPOINT", "https://unit.azure.com")
    monkeypatch.setenv("AZURE_AI_PROJECT_NAME", "demo-project")
    monkeypatch.setenv("AZURE_AI_CONNECTION_ID", "conn-id")
    monkeypatch.setenv("SERPER_API_KEY", "secret")
    monkeypatch.setenv("SERPER_SEARCH_URL", "https://example.com/search")
    monkeypatch.setenv("POLYGON_API_KEY", "poly-secret")
    monkeypatch.setenv("POLYGON_BASE_URL", "https://polygon.example.com")
    return monkeypatch


def test_settings_construct(env_vars):
    settings = Settings()
    assert settings.project_endpoint() == "https://unit.azure.com/api/projects/demo-project"
    headers = settings.serper_headers()
    assert headers["X-API-KEY"] == "secret"
    assert headers["Content-Type"] == "application/json"


def test_empty_project_rejected(monkeypatch):
    monkeypatch.setenv("AZURE_AI_ENDPOINT", "https://unit.azure.com")
    monkeypatch.setenv("AZURE_AI_PROJECT_NAME", "")
    monkeypatch.setenv("AZURE_AI_CONNECTION_ID", "conn-id")
    monkeypatch.setenv("SERPER_API_KEY", "secret")
    monkeypatch.setenv("SERPER_SEARCH_URL", "https://example.com/search")
    monkeypatch.setenv("POLYGON_API_KEY", "poly-secret")
    monkeypatch.setenv("POLYGON_BASE_URL", "https://polygon.example.com")

    with pytest.raises(ValueError):
        Settings()

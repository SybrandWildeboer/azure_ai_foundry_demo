from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    azure_ai_endpoint: HttpUrl = Field(alias="AZURE_AI_ENDPOINT")
    azure_ai_project_name: str = Field(alias="AZURE_AI_PROJECT_NAME")
    azure_ai_connection_id: str = Field(alias="AZURE_AI_CONNECTION_ID")
    azure_ai_agent_model: str = Field(default="gpt-4o-mini", alias="AZURE_AI_AGENT_MODEL")
    serper_api_key: SecretStr = Field(alias="SERPER_API_KEY")
    serper_search_url: HttpUrl = Field(
        alias="SERPER_SEARCH_URL", default="https://google.serper.dev/search"
    )
    serper_news_url: HttpUrl = Field(
        alias="SERPER_NEWS_URL", default="https://google.serper.dev/news"
    )
    polygon_api_key: SecretStr = Field(alias="POLYGON_API_KEY")
    polygon_base_url: HttpUrl = Field(default="https://api.polygon.io", alias="POLYGON_BASE_URL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @field_validator("azure_ai_project_name", "azure_ai_connection_id", mode="before")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("Environment variable must not be empty")
        return value

    def project_endpoint(self) -> str:
        base = str(self.azure_ai_endpoint).rstrip("/")
        project = self.azure_ai_project_name.strip("/")
        if project:
            return f"{base}/api/projects/{project}"
        return f"{base}/api/projects"

    def serper_headers(self) -> dict[str, str]:
        return {
            "X-API-KEY": self.serper_api_key.get_secret_value(),
            "Content-Type": "application/json",
        }

    def polygon_url(self, path: str) -> str:
        base = str(self.polygon_base_url).rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def polygon_params(self) -> dict[str, str]:
        return {"apiKey": self.polygon_api_key.get_secret_value()}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

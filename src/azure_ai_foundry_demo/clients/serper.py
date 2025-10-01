from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from pydantic import HttpUrl

from azure_ai_foundry_demo.config import Settings
from azure_ai_foundry_demo.models import NewsHeadline

AsyncClientFactory = Callable[[], httpx.AsyncClient]


class SerperClient:
    def __init__(
        self, settings: Settings, client_factory: AsyncClientFactory | None = None
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=10.0))

    async def fetch_news(
        self,
        query: str,
        *,
        location: str = "us",
        language: str = "en",
        timeframe: str | None = "7d",
        num_results: int | None = None,
    ) -> list[NewsHeadline]:
        params: dict[str, Any] = {"q": query, "gl": location, "hl": language}
        if timeframe:
            params["timeframe"] = timeframe
        if num_results is not None:
            params["num"] = num_results
        response_json = await self._get(self._settings.serper_news_url, params)
        return self._extract_news(response_json)

    async def search_web(self, query: str) -> list[dict[str, Any]]:
        payload = {"q": query}
        response_json = await self._post(self._settings.serper_search_url, payload)
        results = response_json.get("organic", []) if isinstance(response_json, dict) else []
        return [result for result in results if isinstance(result, dict)]

    async def _post(self, url: HttpUrl, payload: dict[str, Any]) -> dict[str, Any]:
        async with self._client_factory() as client:
            response = await client.post(
                str(url),
                json=payload,
                headers=self._settings.serper_headers(),
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected response from Serper.dev; expected a JSON object")
        return data

    async def _get(self, url: HttpUrl, params: dict[str, Any]) -> dict[str, Any]:
        async with self._client_factory() as client:
            response = await client.get(
                str(url),
                params=params,
                headers=self._settings.serper_headers(),
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected response from Serper.dev; expected a JSON object")
        return data

    def _extract_news(self, data: dict[str, Any]) -> list[NewsHeadline]:
        news_items = data.get("news", []) if isinstance(data, dict) else []
        results: list[NewsHeadline] = []
        for item in news_items:
            if not isinstance(item, dict):
                continue
            try:
                results.append(
                    NewsHeadline(
                        title=item.get("title", ""),
                        link=item["link"],
                        snippet=item.get("snippet"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return results

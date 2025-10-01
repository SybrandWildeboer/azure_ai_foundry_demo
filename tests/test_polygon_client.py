import datetime as dt

import pytest
import respx
from httpx import Response

from azure_ai_foundry_demo.clients.polygon import PolygonClient
from azure_ai_foundry_demo.config import Settings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("AZURE_AI_ENDPOINT", "https://unit.azure.com")
    monkeypatch.setenv("AZURE_AI_PROJECT_NAME", "demo-project")
    monkeypatch.setenv("AZURE_AI_CONNECTION_ID", "conn-id")
    monkeypatch.setenv("AZURE_AI_AGENT_MODEL", "model")
    monkeypatch.setenv("SERPER_API_KEY", "serper")
    monkeypatch.setenv("SERPER_SEARCH_URL", "https://example.com/search")
    monkeypatch.setenv("SERPER_NEWS_URL", "https://example.com/news")
    monkeypatch.setenv("POLYGON_API_KEY", "poly")
    monkeypatch.setenv("POLYGON_BASE_URL", "https://polygon.example.com")
    return Settings()


@pytest.mark.asyncio
async def test_fetch_previous_close_converts_quote(settings):
    client = PolygonClient(settings)
    url = settings.polygon_url("v2/aggs/ticker/MSFT/prev")
    payload = {"results": [{"c": 400.5, "o": 395.0, "t": 1_700_000_000_000}]}
    with respx.mock(assert_all_called=True) as router:
        router.get(url, params={"apiKey": "poly", "adjusted": "true"}).mock(
            return_value=Response(200, json=payload)
        )
        quote = await client.fetch_previous_close("MSFT")
    assert quote.ticker == "MSFT"
    assert quote.close == pytest.approx(400.5)
    assert quote.open == pytest.approx(395.0)
    assert isinstance(quote.as_of, dt.datetime)
    stock_quote = quote.to_stock_quote()
    assert stock_quote.price == quote.close
    assert stock_quote.change == pytest.approx(quote.close - quote.open)

import pytest
import respx
from httpx import Response

from azure_ai_foundry_demo.clients.serper import SerperClient
from azure_ai_foundry_demo.config import Settings
from azure_ai_foundry_demo.models import NewsHeadline, StockQuote


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("AZURE_AI_ENDPOINT", "https://unit.azure.com")
    monkeypatch.setenv("AZURE_AI_PROJECT_NAME", "demo-project")
    monkeypatch.setenv("AZURE_AI_CONNECTION_ID", "conn-id")
    monkeypatch.setenv("SERPER_API_KEY", "secret")
    monkeypatch.setenv("SERPER_SEARCH_URL", "https://example.com/search")
    monkeypatch.setenv("SERPER_NEWS_URL", "https://example.com/news")
    monkeypatch.setenv("POLYGON_API_KEY", "poly")
    monkeypatch.setenv("POLYGON_BASE_URL", "https://polygon.example.com")
    return Settings()


@pytest.mark.asyncio
async def test_fetch_news(settings):
    client = SerperClient(settings)
    news_payload = {
        "news": [
            {
                "title": "Headline",
                "link": "https://news.example.com/article",
                "snippet": "Summary",
            }
        ]
    }
    with respx.mock(assert_all_called=True) as router:
        router.get("https://example.com/news").mock(return_value=Response(200, json=news_payload))
        headlines = await client.fetch_news("msft")
    assert len(headlines) == 1
    assert isinstance(headlines[0], NewsHeadline)
    assert headlines[0].title == "Headline"


@pytest.mark.asyncio
async def test_search_web(settings):
    client = SerperClient(settings)
    search_payload = {
        "organic": [{"title": "Item", "link": "https://result.example.com", "snippet": "Snippet"}]
    }
    with respx.mock(assert_all_called=True) as router:
        router.post("https://example.com/search").mock(
            return_value=Response(200, json=search_payload)
        )
        results = await client.search_web("contoso earnings")
    assert results[0]["title"] == "Item"
    assert len(results) == 1


def test_stock_quote_dump(settings):
    quote = StockQuote(ticker="MSFT", price=100.0, change=1.5, change_percent=1.5, currency="USD")
    data = quote.model_dump()
    assert data["ticker"] == "MSFT"

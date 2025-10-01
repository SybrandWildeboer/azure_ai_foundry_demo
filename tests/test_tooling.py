from unittest.mock import MagicMock

from azure_ai_foundry_demo.agents.tooling import ResearchTooling
from azure_ai_foundry_demo.models import FinanceResearchPayload, StockQuote


def test_research_tooling_reset():
    tooling = ResearchTooling(polygon_client=MagicMock(), serper_client=MagicMock())
    tooling.last_payload = FinanceResearchPayload(quote=StockQuote(ticker="MSFT"))
    tooling.last_news_results = [{"title": "Headline", "link": "https://example.com"}]

    tooling.reset()

    assert tooling.last_payload is None
    assert tooling.last_news_results == []

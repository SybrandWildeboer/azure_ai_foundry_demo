from dataclasses import dataclass

import pytest

from azure_ai_foundry_demo.workflow import AgentResearchReport, StockResearchWorkflow, render_report


@dataclass
class DummyOrchestrator:
    payload: dict[str, object]

    def run(self, ticker: str) -> dict[str, object]:
        self.payload["ticker"] = ticker.upper()
        return self.payload


@pytest.fixture
def orchestrator_payload():
    return {
        "ticker": "MSFT",
        "quote": {"price": 410.12, "currency": "USD", "change": 4.2, "change_percent": 1.05},
        "news": [
            {"title": "Headline A", "link": "https://example.com/a", "snippet": "Summary A"},
            {"title": "Headline B", "link": "https://example.com/b", "snippet": "Summary B"},
        ],
        "organic_results": [{"title": "Result", "link": "https://example.com/result"}],
        "historical": [],
        "metrics": None,
        "research_notes": ["Note 1", "Note 2"],
        "analysis": ["Bullet 1", "Bullet 2"],
    }


def test_workflow_returns_dataclass(monkeypatch, orchestrator_payload):
    monkeypatch.setenv("AZURE_AI_ENDPOINT", "https://unit.azure.com")
    monkeypatch.setenv("AZURE_AI_PROJECT_NAME", "demo-project")
    monkeypatch.setenv("AZURE_AI_CONNECTION_ID", "conn-id")
    monkeypatch.setenv("SERPER_API_KEY", "secret")
    monkeypatch.setenv("SERPER_SEARCH_URL", "https://example.com/search")
    monkeypatch.setenv("SERPER_NEWS_URL", "https://example.com/news")
    monkeypatch.setenv("POLYGON_API_KEY", "poly")
    monkeypatch.setenv("POLYGON_BASE_URL", "https://polygon.example.com")

    orchestrator = DummyOrchestrator(orchestrator_payload)
    workflow = StockResearchWorkflow(orchestrator=orchestrator)
    report = workflow.run("msft")

    assert isinstance(report, AgentResearchReport)
    assert report.ticker == "MSFT"
    summary = render_report(report, include_sources=True)
    assert "Ticker: MSFT" in summary
    assert "Sources:" in summary

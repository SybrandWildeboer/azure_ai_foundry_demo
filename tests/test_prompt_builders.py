from __future__ import annotations

from azure_ai_foundry_demo.agents.prompt_builders import (
    build_analysis_prompt,
    build_news_prompt,
    build_price_prompt,
    build_router_prompt,
)
from azure_ai_foundry_demo.agents.stage_models import StageResult
from azure_ai_foundry_demo.models import FinanceResearchPayload


def test_build_price_prompt_includes_focus_and_instructions() -> None:
    prompt = build_price_prompt("msft", summary="Existing summary", focus="Intraday volatility")
    assert "MSFT" in prompt
    assert "Existing summary" in prompt
    assert "Intraday volatility" in prompt
    assert "lookup_stock_overview" in prompt


def test_build_news_prompt_mentions_focus() -> None:
    prompt = build_news_prompt("nvda", summary="Prior", focus="AI datacenter demand")
    assert "NVDA" in prompt
    assert "Prior" in prompt
    assert "AI datacenter demand" in prompt
    assert "search_related_news" in prompt


def test_build_analysis_prompt_renders_stage_and_payload() -> None:
    payload = FinanceResearchPayload.model_validate(
        {
            "quote": {
                "ticker": "GOOG",
                "price": 100,
                "currency": "USD",
                "change": 2,
                "change_percent": 2.0,
            },
            "historical": [],
            "metrics": None,
            "news": [],
            "organic_results": [],
        }
    )
    stage_results = [StageResult(name="price-stage", messages=["Price notes"])]
    prompt = build_analysis_prompt(
        "goog",
        stage_results,
        last_payload=payload,
        summary="Panel summary",
        conversation_history=[{"role": "user", "content": "How are margins?"}],
        user_message="Look at advertising",
    )
    assert "GOOG" in prompt
    assert "Price notes" in prompt
    assert "How are margins?" in prompt
    assert "Look at advertising" in prompt
    assert "Price Snapshot" in prompt


def test_build_router_prompt_describes_payload_snapshot() -> None:
    payload = FinanceResearchPayload.model_validate(
        {
            "quote": {
                "ticker": "AAPL",
                "price": 510.25,
                "currency": "USD",
                "change": 5.1,
                "change_percent": 1.0,
            },
            "historical": [{"open": 500, "close": 505, "date": "2024-09-30"}],
            "metrics": {"period_days": 5},
            "news": [],
            "organic_results": [],
        }
    )
    prompt = build_router_prompt(
        "aapl",
        summary="Previous summary",
        conversation_history=[{"role": "assistant", "content": "Summary"}],
        user_message="Check technicals",
        last_payload=payload,
    )
    assert "AAPL" in prompt
    assert "Previous summary" in prompt
    assert "Summary" in prompt
    assert "Check technicals" in prompt
    assert "Historical bars: 1" in prompt

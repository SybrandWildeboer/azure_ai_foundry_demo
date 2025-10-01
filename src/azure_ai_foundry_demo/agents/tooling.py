from __future__ import annotations

import json
import logging
from typing import Any
from azure.ai.agents.models import FunctionDefinition, FunctionToolDefinition

from azure_ai_foundry_demo.agents.utils import sync_await
from azure_ai_foundry_demo.clients.polygon import PolygonClient, PolygonDailyBar
from azure_ai_foundry_demo.clients.serper import SerperClient
from azure_ai_foundry_demo.models import (
    FinanceResearchPayload,
    HistoricalBar,
    NewsHeadline,
    StockQuote,
    TrendMetrics,
)

logger = logging.getLogger(__name__)


class ResearchTooling:
    def __init__(self, polygon_client: PolygonClient, serper_client: SerperClient) -> None:
        self._polygon_client = polygon_client
        self._serper_client = serper_client
        self.last_payload: FinanceResearchPayload | None = None
        self.last_news_results: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.last_payload = None
        self.last_news_results = []

    def lookup_stock_overview(self, ticker: str) -> str:
        try:
            payload = self._fetch_overview(ticker)
        except Exception as exc:
            logger.exception("Failed to fetch stock overview for %s", ticker)
            return json.dumps({"error": f"Failed to get stock overview: {exc}"})
        self.last_payload = payload
        self.last_news_results = payload.organic_results
        return json.dumps(payload.model_dump(mode="json"))

    def search_related_news(self, query: str) -> str:
        try:
            headlines = sync_await(self._serper_client.fetch_news(query))
            if headlines:
                results = [headline.model_dump(mode="json") for headline in headlines]
            else:
                results = sync_await(self._serper_client.search_web(query))
        except Exception as exc:
            logger.exception("Failed to search news for query %s", query)
            return json.dumps({"error": f"Failed to search news: {exc}"})
        self.last_news_results = results
        if self.last_payload is not None:
            self.last_payload.news = [NewsHeadline.model_validate(item) for item in results]
            self.last_payload.organic_results = results
        return json.dumps(results)

    def get_function_definitions(self) -> list[FunctionToolDefinition]:
        overview = FunctionToolDefinition(
            function=FunctionDefinition(
                name="lookup_stock_overview",
                description="Look up stock overview information for a given ticker symbol",
                parameters={
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "The stock ticker symbol to look up",
                        }
                    },
                    "required": ["ticker"],
                },
            )
        )
        news = FunctionToolDefinition(
            function=FunctionDefinition(
                name="search_related_news",
                description="Search for news related to a stock or financial topic",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "General search query to investigate broader sentiment or news"
                            ),
                        }
                    },
                    "required": ["query"],
                },
            )
        )
        return [overview, news]

    def execute_function(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "lookup_stock_overview":
            ticker = (
                arguments.get("ticker")
                or arguments.get("symbol")
                or arguments.get("stock")
                or arguments.get("stock_ticker")
            )
            if not ticker:
                raise ValueError("lookup_stock_overview requires a 'ticker' argument")
            return self.lookup_stock_overview(str(ticker))
        if name == "search_related_news":
            query = arguments.get("query") or arguments.get("topic") or arguments.get("search")
            if not query:
                raise ValueError("search_related_news requires a 'query' argument")
            return self.search_related_news(str(query))
        return json.dumps({"error": f"Unknown function: {name}"})

    def _fetch_overview(self, ticker: str) -> FinanceResearchPayload:
        payload: FinanceResearchPayload | None = None
        try:
            polygon_quote = sync_await(self._polygon_client.fetch_previous_close(ticker))
            payload = FinanceResearchPayload(quote=polygon_quote.to_stock_quote())
            bars = sync_await(self._polygon_client.fetch_recent_bars(ticker, days=7))
            if bars:
                payload.historical = [
                    HistoricalBar(
                        date=bar.as_of.date().isoformat(),
                        open=bar.open,
                        high=bar.high,
                        low=bar.low,
                        close=bar.close,
                        volume=bar.volume,
                    )
                    for bar in bars
                ]
                metrics = _calculate_trend_metrics(bars)
                if metrics is not None:
                    payload.metrics = metrics
        except Exception:
            logger.warning("Polygon data unavailable for %s", ticker, exc_info=True)
        if payload is None:
            payload = FinanceResearchPayload(quote=StockQuote(ticker=ticker.upper()))
        return payload


def _calculate_trend_metrics(bars: list[PolygonDailyBar]) -> TrendMetrics | None:
    if not bars:
        return None
    closes = [bar.close for bar in bars if bar.close is not None]
    volumes = [bar.volume for bar in bars if bar.volume is not None]
    highs = [bar.high for bar in bars if bar.high is not None]
    lows = [bar.low for bar in bars if bar.low is not None]
    absolute_change = None
    percent_change = None
    if len(closes) >= 2:
        start_price = closes[0]
        end_price = closes[-1]
        if start_price not in (None, 0) and end_price is not None:
            absolute_change = end_price - start_price
            percent_change = (absolute_change / start_price) * 100
    average_volume = sum(volumes) / len(volumes) if volumes else None
    period_high = max(highs) if highs else (max(closes) if closes else None)
    period_low = min(lows) if lows else (min(closes) if closes else None)
    return TrendMetrics(
        period_days=len(bars),
        absolute_change=absolute_change,
        percent_change=percent_change,
        average_volume=average_volume,
        high=period_high,
        low=period_low,
    )

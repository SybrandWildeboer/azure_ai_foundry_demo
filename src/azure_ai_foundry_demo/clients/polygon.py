from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel

from azure_ai_foundry_demo.config import Settings
from azure_ai_foundry_demo.models import StockQuote

AsyncClientFactory = Callable[[], httpx.AsyncClient]


class PolygonDailyBar(BaseModel):
    ticker: str
    as_of: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "date": self.as_of.date().isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class PolygonQuote(BaseModel):
    ticker: str
    close: float
    open: float | None = None
    as_of: datetime

    def to_stock_quote(self) -> StockQuote:
        change = None
        change_percent = None
        if self.open not in (None, 0):
            change = self.close - self.open
            change_percent = (change / self.open) * 100
        return StockQuote(
            ticker=self.ticker,
            price=self.close,
            change=change,
            change_percent=change_percent,
            currency="USD",
            as_of=self.as_of.isoformat(),
        )


class PolygonClient:
    def __init__(
        self, settings: Settings, client_factory: AsyncClientFactory | None = None
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=10.0))

    async def fetch_previous_close(self, ticker: str) -> PolygonQuote:
        url = self._settings.polygon_url(f"v2/aggs/ticker/{ticker.upper()}/prev")
        params = self._settings.polygon_params() | {"adjusted": "true"}
        async with self._client_factory() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results") or []
        if not results:
            raise ValueError(f"Polygon response did not include results for ticker {ticker}")
        latest = results[0]
        close_price = latest.get("c")
        if close_price is None:
            raise ValueError("Polygon previous close response missing closing price")
        open_price = latest.get("o")
        timestamp = latest.get("t")
        if isinstance(timestamp, int | float):
            as_of = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
        else:
            as_of = datetime.now(tz=UTC)
        return PolygonQuote(
            ticker=ticker.upper(),
            close=float(close_price),
            open=float(open_price) if open_price is not None else None,
            as_of=as_of,
        )

    async def fetch_recent_bars(self, ticker: str, days: int = 7) -> list[PolygonDailyBar]:
        if days <= 0:
            raise ValueError("days must be greater than zero")
        end = datetime.now(UTC).date()
        start = end - timedelta(days=days + 7)
        url = self._settings.polygon_url(
            f"v2/aggs/ticker/{ticker.upper()}/range/1/day/{start.isoformat()}/{end.isoformat()}"
        )
        params = self._settings.polygon_params() | {
            "adjusted": "true",
            "sort": "desc",
            "limit": days,
        }
        async with self._client_factory() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results") or []
        bars: list[PolygonDailyBar] = []
        for entry in results:
            timestamp = entry.get("t")
            if not isinstance(timestamp, int | float):
                continue
            as_of = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            bars.append(
                PolygonDailyBar(
                    ticker=ticker.upper(),
                    as_of=as_of,
                    open=float(entry["o"]) if entry.get("o") is not None else None,
                    high=float(entry["h"]) if entry.get("h") is not None else None,
                    low=float(entry["l"]) if entry.get("l") is not None else None,
                    close=float(entry["c"]) if entry.get("c") is not None else None,
                    volume=float(entry["v"]) if entry.get("v") is not None else None,
                )
            )
        bars.sort(key=lambda bar: bar.as_of)
        return bars[-days:]

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class StockQuote(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    price: float | None = None
    change: float | None = None
    change_percent: float | None = Field(default=None, alias="changePercent")
    currency: str | None = None
    as_of: str | None = Field(default=None, alias="date")

    @field_validator("change", "change_percent", mode="before")
    def round_to_2_decimals(cls, v):  # noqa: N805
        if v is not None:
            return round(v, 2)
        return v


class NewsHeadline(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    link: HttpUrl
    snippet: str | None = None


class HistoricalBar(BaseModel):
    date: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None


class TrendMetrics(BaseModel):
    period_days: int
    absolute_change: float | None = None
    percent_change: float | None = None
    average_volume: float | None = None
    high: float | None = None
    low: float | None = None


class FinanceResearchPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    quote: StockQuote
    news: list[NewsHeadline] = Field(default_factory=list)
    organic_results: list[dict[str, object]] = Field(default_factory=list)
    historical: list[HistoricalBar] = Field(default_factory=list)
    metrics: TrendMetrics | None = None

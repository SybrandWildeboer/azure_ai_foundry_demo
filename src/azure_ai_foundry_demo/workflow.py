from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from azure_ai_foundry_demo.agents.orchestrator import StockAgentOrchestrator
from azure_ai_foundry_demo.config import Settings, get_settings


@dataclass
class AgentResearchReport:
    ticker: str
    quote: dict[str, Any]
    news: list[dict[str, Any]]
    organic_results: list[dict[str, Any]]
    research_notes: list[str]
    analysis: list[str]
    historical: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] | None = None

    def formatted_summary(self) -> str:
        notes_section = "\n\n".join(self.research_notes) or "No intermediate notes"
        analysis_section = "\n\n".join(self.analysis) or "No analysis produced"
        headline_lines = [
            f"- {item.get('title', 'Untitled')}" for item in self.news[:5]
        ] or ["- No headlines"]
        metrics_section = "No multi-day metrics available"
        if self.metrics:
            lines: list[str] = []
            period = self.metrics.get("period_days")
            change = self.metrics.get("absolute_change")
            change_pct = self.metrics.get("percent_change")
            avg_volume = self.metrics.get("average_volume")
            high = self.metrics.get("high")
            low = self.metrics.get("low")
            if period:
                lines.append(f"Period: last {period} trading days")
            if change is not None:
                suffix = f" ({change_pct:.2f}%)" if change_pct is not None else ""
                lines.append(f"Change: {change:.2f}{suffix}")
            elif change_pct is not None:
                lines.append(f"Change: {change_pct:.2f}%")
            if avg_volume is not None:
                lines.append(f"Average volume: {avg_volume:,.0f}")
            range_parts: list[str] = []
            if high is not None:
                range_parts.append(f"high {high:.2f}")
            if low is not None:
                range_parts.append(f"low {low:.2f}")
            if range_parts:
                lines.append("Range: " + ", ".join(range_parts))
            if lines:
                metrics_section = "\n".join(lines)
        return (
            f"Ticker: {self.ticker}\n"
            f"Price: {self.quote.get('price')} {self.quote.get('currency')}\n"
            f"Change: {self.quote.get('change')} ({self.quote.get('change_percent')}%)\n\n"
            "Headlines:\n"
            + "\n".join(headline_lines)
            + "\n\nMulti-day metrics:\n"
            + metrics_section
            + "\n\nResearch Notes:\n"
            + notes_section
            + "\n\nAnalyst Summary:\n"
            + analysis_section
        )


class StockResearchWorkflow:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        orchestrator: StockAgentOrchestrator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._orchestrator = orchestrator or StockAgentOrchestrator(settings=self._settings)

    def run(self, ticker: str) -> AgentResearchReport:
        payload = self._orchestrator.run(ticker)
        return AgentResearchReport(**payload)


def render_report(report: AgentResearchReport, *, include_sources: bool = False) -> str:
    summary = report.formatted_summary()
    if not include_sources:
        return summary
    organic_lines = []
    for item in report.organic_results[:5]:
        title = item.get("title", "Untitled result")
        link = item.get("link", "")
        organic_lines.append(f"- {title} ({link})")
    sources_section = "\n\nSources:\n" + "\n".join(organic_lines or ["- No additional sources"])
    return summary + sources_section

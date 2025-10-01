from __future__ import annotations

import json
from textwrap import dedent
from typing import Sequence

from azure_ai_foundry_demo.agents.stage_models import StageResult
from azure_ai_foundry_demo.models import FinanceResearchPayload


def build_price_prompt(
    ticker: str,
    *,
    summary: str | None = None,
    focus: str | None = None,
) -> str:
    context_summary = summary or "No previous summary provided."
    focus_line = focus or "Focus on the core market performance."
    return dedent(
        f"""
        Gather a fresh market snapshot for {ticker.upper()}.
        Previous summary: {context_summary}
        Research focus: {focus_line}

    Instructions:
    - Call the `lookup_stock_overview` function exactly once to obtain the latest data.
    - Report price, absolute change, percent change, currency, and any returned metrics.
    - Present your findings as a short bullet list (maximum four items) without speculation.
        """
    ).strip()


def build_news_prompt(
    ticker: str,
    *,
    summary: str | None = None,
    focus: str | None = None,
) -> str:
    focus_line = focus or f"Key developments impacting {ticker.upper()}"
    summary_line = summary or "No prior summary provided."
    return dedent(
        f"""
        Identify the most relevant and timely headlines for {ticker.upper()}.
        Previous summary: {summary_line}
        News focus: {focus_line}

          Instructions:
          - Query the `search_related_news` function once with a focused search phrase that mentions the ticker and key catalysts.
          - Return at most five bullet points, each covering the headline, source, and why it matters.
          - If no meaningful headlines are available, state that clearly.
        """
    ).strip()


def build_analysis_prompt(
    ticker: str,
    stage_results: Sequence[StageResult],
    *,
    last_payload: FinanceResearchPayload | None,
    summary: str | None,
    conversation_history: Sequence[dict[str, str]] | None,
    user_message: str | None,
) -> str:
    structured_payload = (
        json.dumps(last_payload.model_dump(mode="json"), indent=2)
        if last_payload is not None
        else "No structured market data captured."
    )
    stage_sections: list[str] = []
    for stage in stage_results:
        if stage.messages:
            stage_text = "\n".join(stage.messages)
        else:
            stage_text = "No notes recorded."
        stage_sections.append(f"{stage.name.replace('-', ' ').title()} Notes:\n{stage_text}")
    stage_block = "\n\n".join(stage_sections) if stage_sections else "No specialist notes captured."
    history_lines: list[str] = []
    if conversation_history:
        for entry in conversation_history:
            role = entry.get("role", "user").capitalize()
            content = entry.get("content", "")
            if content:
                history_lines.append(f"{role}: {content}")
    history_block = "\n".join(history_lines) if history_lines else "No prior conversation provided."
    summary_line = summary or "No previous summary available."
    focus_line = user_message or "Provide an updated, comprehensive viewpoint."
    return dedent(
        f"""
        You are the lead financial analyst preparing the final briefing for {ticker.upper()}.

        Previous summary: {summary_line}
        User focus: {focus_line}

        Conversation history:
        {history_block}

        Specialist contributions:
        {stage_block}

        Structured market data:
        {structured_payload}

        Deliver the final report with the following structure:
        - Price Snapshot — two sentences highlighting price level and intraday or recent moves.
        - Key Headlines — bullet list (up to five) summarising headline, source, and implication.
        - Trend Assessment — exactly two bullet points covering technical or volume trends and key risks.
        - Recommended Next Steps — two actionable bullet points for the research team.

        Keep the tone analytical, reference quantitative figures where available, and avoid
        repeating the instructions verbatim in the response. Use a blank line between sections and
        ensure bullet lists use a single style (hyphen prefixes).
        """
    ).strip()


def build_router_prompt(
    ticker: str,
    *,
    summary: str | None,
    conversation_history: Sequence[dict[str, str]] | None,
    user_message: str,
    last_payload: FinanceResearchPayload | None,
) -> str:
    summary_line = summary or "No previous summary available."
    history_lines: list[str] = []
    if conversation_history:
        for entry in conversation_history:
            role = entry.get("role", "user").capitalize()
            content = entry.get("content", "")
            if content:
                history_lines.append(f"{role}: {content}")
    history_block = "\n".join(history_lines) if history_lines else "No prior conversation provided."
    payload_snippet = "No charted data available."
    if last_payload is not None:
        quote = last_payload.quote
        payload_snippet = (
            f"Price: {quote.price} {quote.currency}, Change: {quote.change}"
            f" ({quote.change_percent}%), Historical bars: {len(last_payload.historical)}"
        )
    return dedent(
        f"""
        A follow-up message was received for {ticker.upper()}.
        Latest summary: {summary_line}
        Prior conversation:
        {history_block}

        Cached market data snapshot:
        {payload_snippet}

        User message:
        {user_message}

        Decide which specialists should run next and explain your choice. Remember to respond with
        the required JSON object.
        """
    ).strip()

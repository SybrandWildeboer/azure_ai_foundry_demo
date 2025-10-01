from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class StageSpec:
    name: str
    instructions: str
    uses_tools: bool


PRICE_STAGE = StageSpec(
    name="price-specialist",
    instructions=dedent(
        """
        You are a market data specialist. Retrieve up-to-date prices and trend metrics by calling the
        available pricing tools. Report only factual data you receive from the tools.
        """
    ).strip(),
    uses_tools=True,
)

NEWS_STAGE = StageSpec(
    name="news-researcher",
    instructions=dedent(
        """
        You are a financial news curator. Use the news search tool to identify the most relevant and
        timely headlines for the given ticker. Focus on concise bullet summaries.
        """
    ).strip(),
    uses_tools=True,
)

ANALYST_STAGE = StageSpec(
    name="lead-analyst",
    instructions=dedent(
        """
        You are the lead financial analyst. Synthesize the information supplied by the specialists and
        craft an actionable investment briefing with clear sections and bullet points.
        """
    ).strip(),
    uses_tools=False,
)

ROUTER_INSTRUCTIONS = dedent(
    """
    You are the orchestration coordinator for a financial research team. Based on the latest request
    and available context, decide which specialists should be engaged next.

    Available specialists:
    - price: retrieves price overview and trend metrics (requires tool access)
    - news: curates relevant headlines via tool search
    - analysis: produces the final synthesized analyst response (no tools)

    Respond with a single JSON object using the following schema:
    {
      "stages": ["price", "news", "analysis"],
      "reason": "One sentence explanation"
    }

    Only include specialists that are necessary. Always include "analysis" if the user requires a
    summarised response or recommendation.
    """
).strip()

STAGE_REGISTRY = {
    "price": PRICE_STAGE,
    "news": NEWS_STAGE,
    "analysis": ANALYST_STAGE,
}

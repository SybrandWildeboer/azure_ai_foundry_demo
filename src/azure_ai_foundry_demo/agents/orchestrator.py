from __future__ import annotations

import json
from typing import Any, Sequence

from azure.ai.agents.models import Agent
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential

from azure_ai_foundry_demo.agents.prompt_builders import (
    build_analysis_prompt,
    build_news_prompt,
    build_price_prompt,
    build_router_prompt,
)
from azure_ai_foundry_demo.agents.runner import AzureAgentRunner
from azure_ai_foundry_demo.agents.stage_models import StageResult
from azure_ai_foundry_demo.agents.stage_specs import (
    ANALYST_STAGE,
    NEWS_STAGE,
    PRICE_STAGE,
    ROUTER_INSTRUCTIONS,
    STAGE_REGISTRY,
    StageSpec,
)
from azure_ai_foundry_demo.agents.tooling import ResearchTooling
from azure_ai_foundry_demo.clients.polygon import PolygonClient
from azure_ai_foundry_demo.clients.serper import SerperClient
from azure_ai_foundry_demo.config import Settings, get_settings


FOLLOW_UP_STAGE_ORDER = ["price", "news", "analysis"]


class StockAgentOrchestrator:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        credential = DefaultAzureCredential()
        self._project_client = AIProjectClient(
            endpoint=self._settings.project_endpoint(),
            credential=credential,
        )
        self._runner = AzureAgentRunner(self._project_client)
        self._polygon_client = PolygonClient(self._settings)
        self._serper_client = SerperClient(self._settings)
        self._tooling = ResearchTooling(self._polygon_client, self._serper_client)

    def run(self, ticker: str) -> dict[str, Any]:
        self._tooling.reset()
        specialists: list[StageResult] = []
        price_stage = self._run_stage(spec=PRICE_STAGE, prompt=build_price_prompt(ticker))
        specialists.append(price_stage)
        news_stage = self._run_stage(spec=NEWS_STAGE, prompt=build_news_prompt(ticker))
        specialists.append(news_stage)
        analysis_stage = self._run_stage(
            spec=ANALYST_STAGE,
            prompt=build_analysis_prompt(
                ticker,
                specialists,
                last_payload=self._tooling.last_payload,
                summary=None,
                conversation_history=None,
                user_message=None,
            ),
        )
        return self._build_payload(
            ticker,
            stage_results=specialists,
            final_analysis=analysis_stage.messages,
        )

    def follow_up(
        self,
        *,
        ticker: str,
        user_message: str,
        summary: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        self._tooling.reset()
        history = conversation_history or []
        requested = self._route_follow_up(
            ticker,
            summary=summary,
            conversation_history=history,
            user_message=user_message,
        )
        stage_sequence = self._ordered_stage_list(requested)

        specialists: list[StageResult] = []
        analysis_stage: StageResult | None = None

        for stage_name in stage_sequence:
            spec = STAGE_REGISTRY.get(stage_name)
            if spec is None:
                continue
            if stage_name == "price":
                stage = self._run_stage(
                    spec=spec,
                    prompt=build_price_prompt(
                        ticker,
                        summary=summary,
                        focus=user_message,
                    ),
                )
                specialists.append(stage)
            elif stage_name == "news":
                stage = self._run_stage(
                    spec=spec,
                    prompt=build_news_prompt(
                        ticker,
                        summary=summary,
                        focus=user_message,
                    ),
                )
                specialists.append(stage)
            elif stage_name == "analysis":
                analysis_stage = self._run_stage(
                    spec=spec,
                    prompt=build_analysis_prompt(
                        ticker,
                        specialists,
                        last_payload=self._tooling.last_payload,
                        summary=summary,
                        conversation_history=history,
                        user_message=user_message,
                    ),
                )

        if analysis_stage is None:
            analysis_stage = self._run_stage(
                spec=ANALYST_STAGE,
                prompt=build_analysis_prompt(
                    ticker,
                    specialists,
                    last_payload=self._tooling.last_payload,
                    summary=summary,
                    conversation_history=history,
                    user_message=user_message,
                ),
            )

        payload = self._build_payload(
            ticker,
            stage_results=specialists,
            final_analysis=analysis_stage.messages,
        )
        payload["reply"] = analysis_stage.messages[-1] if analysis_stage.messages else ""
        payload["messages"] = payload["research_notes"] + analysis_stage.messages
        return payload

    def _create_agent(self, *, name: str, instructions: str, tools: Sequence[Any]) -> Agent:
        return self._project_client.agents.create_agent(
            model=self._settings.azure_ai_agent_model,
            name=name,
            instructions=instructions,
            tools=list(tools),
        )

    def _run_stage(self, *, spec: StageSpec, prompt: str) -> StageResult:
        tools = self._tooling.get_function_definitions() if spec.uses_tools else []
        agent = self._create_agent(name=spec.name, instructions=spec.instructions, tools=tools)
        try:
            result = self._runner.run_with_functions(
                agent=agent,
                user_prompt=prompt,
                tooling=self._tooling if spec.uses_tools else None,
            )
        finally:
            self._delete_agent(agent)
        return StageResult(name=spec.name, messages=result.messages)

    def _delete_agent(self, agent: Agent) -> None:
        try:
            self._project_client.agents.delete_agent(agent.id)
        except HttpResponseError:
            pass

    def _route_follow_up(
        self,
        ticker: str,
        *,
        summary: str | None,
        conversation_history: Sequence[dict[str, str]] | None,
        user_message: str,
    ) -> list[str]:
        router_prompt = build_router_prompt(
            ticker,
            summary=summary,
            conversation_history=conversation_history,
            user_message=user_message,
            last_payload=self._tooling.last_payload,
        )
        agent = self._create_agent(
            name="followup-router",
            instructions=ROUTER_INSTRUCTIONS,
            tools=[],
        )
        try:
            result = self._runner.run_with_functions(
                agent=agent,
                user_prompt=router_prompt,
                tooling=None,
            )
        finally:
            self._delete_agent(agent)
        decision_text = result.messages[-1] if result.messages else ""
        return self._parse_router_response(decision_text)

    def _parse_router_response(self, message: str) -> list[str]:
        if not message:
            return []
        json_blob = self._extract_json_object(message)
        try:
            parsed = json.loads(json_blob)
        except json.JSONDecodeError:
            return []
        stages = parsed.get("stages")
        if not isinstance(stages, list):
            return []
        return [stage for stage in stages if stage in STAGE_REGISTRY]

    @staticmethod
    def _extract_json_object(message: str) -> str:
        start = message.find("{")
        end = message.rfind("}")
        if start != -1 and end != -1 and end > start:
            return message[start : end + 1]
        return message

    def _ordered_stage_list(self, requested: Sequence[str]) -> list[str]:
        unique: list[str] = []
        for name in requested:
            if name in STAGE_REGISTRY and name not in unique:
                unique.append(name)
        if "analysis" not in unique:
            unique.append("analysis")
        return [name for name in FOLLOW_UP_STAGE_ORDER if name in unique]

    def _build_payload(
        self,
        ticker: str,
        *,
        stage_results: Sequence[StageResult],
        final_analysis: list[str],
    ) -> dict[str, Any]:
        quote: dict[str, Any] = {}
        news: list[dict[str, Any]] = []
        organic_results: list[dict[str, Any]] = []
        historical: list[dict[str, Any]] = []
        metrics: dict[str, Any] | None = None
        if self._tooling.last_payload is not None:
            data = self._tooling.last_payload.model_dump()
            quote = data.get("quote", {}) or {}
            news = data.get("news", []) or []
            organic_results = data.get("organic_results", []) or []
            historical = data.get("historical", []) or []
            metrics = data.get("metrics") or None
        if not organic_results and self._tooling.last_news_results:
            organic_results = self._tooling.last_news_results
        stage_notes = self._format_stage_notes(stage_results)
        return {
            "ticker": ticker.upper(),
            "quote": quote,
            "news": news,
            "organic_results": organic_results,
            "historical": historical,
            "metrics": metrics,
            "research_notes": stage_notes,
            "analysis": final_analysis,
        }

    @staticmethod
    def _format_stage_notes(stage_results: Sequence[StageResult]) -> list[str]:
        notes: list[str] = []
        for stage in stage_results:
            label = stage.name.replace("-", " ").title()
            for message in stage.messages:
                notes.append(f"{label}: {message}")
        return notes

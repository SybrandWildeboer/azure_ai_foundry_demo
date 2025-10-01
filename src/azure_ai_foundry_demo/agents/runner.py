from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from azure.ai.agents.models import Agent, RunStatus, SubmitToolOutputsAction, ToolOutput
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError

from azure_ai_foundry_demo.agents.utils import message_to_text

if TYPE_CHECKING:
    from azure_ai_foundry_demo.agents.tooling import ResearchTooling

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    run_id: str
    thread_id: str
    messages: list[str]


class AzureAgentRunner:
    def __init__(
        self, project_client: AIProjectClient, poll_interval: float = 1.0, timeout: float = 120.0
    ) -> None:
        self._threads = project_client.agents.threads
        self._runs = project_client.agents.runs
        self._messages = project_client.agents.messages
        self._poll_interval = poll_interval
        self._timeout = timeout

    def run_with_functions(
        self,
        agent: Agent,
        user_prompt: str,
        tooling: Optional["ResearchTooling"] = None,
    ) -> AgentRunResult:
        logger.info("Starting function-enabled run for agent %s", getattr(agent, "id", "<unknown>"))
        thread = self._threads.create()
        logger.debug("Created thread %s for agent %s", thread.id, getattr(agent, "id", "<unknown>"))
        message = self._messages.create(thread_id=thread.id, role="user", content=user_prompt)
        logger.debug(
            "Posted user prompt message %s to thread %s",
            getattr(message, "id", "<unknown>"),
            thread.id,
        )
        run = self._runs.create(thread_id=thread.id, agent_id=agent.id)
        logger.info("Created run %s for agent %s", run.id, getattr(agent, "id", "<unknown>"))
        completed = self._poll_until_complete(run, tooling)
        messages = self._collect_messages(thread.id, completed.id)
        logger.info(
            "Completed run %s for agent %s with %d assistant messages",
            completed.id,
            getattr(agent, "id", "<unknown>"),
            len(messages),
        )
        try:
            self._threads.delete(thread_id=thread.id)
            logger.debug("Deleted thread %s", thread.id)
        except HttpResponseError:
            logger.debug("Failed to delete thread %s", thread.id, exc_info=True)
        return AgentRunResult(run_id=completed.id, thread_id=thread.id, messages=messages)

    def _poll_until_complete(self, run, tooling: Optional["ResearchTooling"]):
        deadline = time.monotonic() + self._timeout
        current = run
        while True:
            if time.monotonic() > deadline:
                logger.error("Run %s timed out after %.1fs", run.id, self._timeout)
                raise TimeoutError("Agent run did not complete before timeout")
            if current.status == RunStatus.COMPLETED:
                logger.debug("Run %s completed", current.id)
                return current
            if current.status == RunStatus.REQUIRES_ACTION:
                logger.debug("Run %s requires action", current.id)
                if tooling is None:
                    logger.error("Run %s requested tools but none were provided", current.id)
                    raise RuntimeError("Agent requested tool execution but no tooling is available")
                current = self._handle_function_calls(current, tooling)
                continue
            if current.status in {RunStatus.FAILED, RunStatus.CANCELLED, RunStatus.EXPIRED}:
                logger.error("Run %s failed with status %s", current.id, current.status)
                raise RuntimeError(f"Agent run failed with status: {current.status}")
            time.sleep(self._poll_interval)
            current = self._runs.get(thread_id=current.thread_id, run_id=current.id)

    def _handle_function_calls(self, run, tooling: ResearchTooling):
        required = run.required_action
        if not isinstance(required, SubmitToolOutputsAction):
            logger.error(
                "Unsupported required action type %s for run %s",
                getattr(required, "type", "<unknown>"),
                run.id,
            )
            raise RuntimeError("Unsupported required action type")
        outputs: list[ToolOutput] = []
        for call in required.submit_tool_outputs.tool_calls:
            if call.type != "function":
                continue
            try:
                arguments = self._parse_function_arguments(call.function.arguments)
            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON arguments for function %s", call.function.name)
                raise ValueError("Agent tool arguments were not valid JSON") from exc
            logger.info(
                "Processing function call %s (tool_call_id=%s)", call.function.name, call.id
            )
            try:
                result = tooling.execute_function(call.function.name, arguments)
            except Exception:
                logger.exception("Tool execution failed for function %s", call.function.name)
                raise
            outputs.append(ToolOutput(tool_call_id=call.id, output=result))
        if not outputs:
            logger.error("Run %s requested tool outputs but none were generated", run.id)
            raise RuntimeError("Agent requested tool outputs but none were generated")
        return self._runs.submit_tool_outputs(
            thread_id=run.thread_id,
            run_id=run.id,
            tool_outputs=outputs,
        )

    @staticmethod
    def _parse_function_arguments(raw_arguments: str | None) -> dict[str, Any]:
        raw = (raw_arguments or "").strip()
        if not raw:
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise json.JSONDecodeError("Tool arguments must decode to a JSON object", raw, 0)
        return parsed

    def _collect_messages(self, thread_id: str, run_id: str) -> list[str]:
        messages: list[str] = []
        try:
            for message in self._messages.list(thread_id=thread_id):
                if getattr(message, "role", None) != "assistant":
                    continue
                if hasattr(message, "run_id") and message.run_id != run_id:
                    continue
                rendered = message_to_text(message)
                if rendered:
                    messages.append(rendered)
        except HttpResponseError:
            logger.debug("Failed to list messages for thread %s", thread_id, exc_info=True)
        return messages

from __future__ import annotations

import asyncio
import concurrent.futures
import re

from azure.ai.agents.models import MessageTextContent


def sync_await(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    return loop.run_until_complete(coro)


def _normalize_agent_message(text: str) -> str:
    if not text:
        return ""
    sanitized = text.replace("\r\n", "\n").replace("\r", "\n")
    sanitized = sanitized.replace("\u2217", "*")
    sanitized = re.sub(r"\*\*(.+?)\*\*", lambda match: match.group(1), sanitized)
    sanitized = re.sub(r"\*(.+?)\*", lambda match: match.group(1), sanitized)
    sanitized = re.sub(r"\\(\d+)", lambda match: match.group(1), sanitized)
    lines = [line.strip() for line in sanitized.split("\n")]
    compact: list[str] = []
    for line in lines:
        if not line:
            if compact and compact[-1]:
                compact.append("")
            continue
        if compact:
            previous = compact[-1]
            if (
                not previous.endswith((".", "!", "?"))
                and not line.startswith(("-", "*", "•"))
                and not previous.strip().startswith(("-", "*", "•"))
            ):
                compact[-1] = f"{previous} {line}"
                continue
        compact.append(line)
    return "\n".join(compact)


def message_to_text(message) -> str:
    parts: list[str] = []
    if hasattr(message, "text_messages") and message.text_messages:
        for text_message in message.text_messages:
            if hasattr(text_message, "text") and hasattr(text_message.text, "value"):
                parts.append(text_message.text.value)
    elif hasattr(message, "content") and message.content:
        for item in message.content:
            if isinstance(item, MessageTextContent):
                parts.append(item.text.value)
            elif hasattr(item, "text") and hasattr(item.text, "value"):
                parts.append(item.text.value)
            elif hasattr(item, "type") and item.type == "text":
                if hasattr(item, "text"):
                    if isinstance(item.text, str):
                        parts.append(item.text)
                    elif hasattr(item.text, "value"):
                        parts.append(item.text.value)
    raw_text = " ".join(parts)
    return _normalize_agent_message(raw_text)

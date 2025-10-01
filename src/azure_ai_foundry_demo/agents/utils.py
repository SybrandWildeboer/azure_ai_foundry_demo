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

def message_to_text(message) -> str:
    parts: list[str] = []
    if hasattr(message, "text_messages") and message.text_messages:
        for text_message in message.text_messages:
            if hasattr(text_message, "text") and hasattr(text_message.text, "value"):
                parts.append(text_message.text.value)
    if not parts and hasattr(message, "content") and message.content:
        for item in message.content:
            if isinstance(item, MessageTextContent):
                parts.append(item.text.value)
            elif hasattr(item, "text") and hasattr(item.text, "value"):
                parts.append(item.text.value)
            elif hasattr(item, "type") and item.type == "text" and hasattr(item, "text"):
                if isinstance(item.text, str):
                    parts.append(item.text)
                elif hasattr(item.text, "value"):
                    parts.append(item.text.value)
    raw_text = "\n".join(parts)
    return _normalize_text(raw_text)


_BOLD_ITALIC_RE = re.compile(r"(\*\*|__|\*|_)(.+?)\1")
_NUMBERED_LIST_RE = re.compile(r"^(\s*)(\d+)[\.)]\s+", re.MULTILINE)
_ESCAPED_NUMBER_RE = re.compile(r"\\(\d)")
_COMMA_NO_SPACE_RE = re.compile(r",(?=\S)")

_CURRENCY_CODES = ("USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF")
_CURRENCY_PATTERN = "|".join(_CURRENCY_CODES)
_CURRENCY_AFTER_NUMBER_RE = re.compile(rf"(\d)({_CURRENCY_PATTERN})")
_CURRENCY_BEFORE_LETTER_RE = re.compile(rf"({_CURRENCY_PATTERN})(?=[A-Za-z])")

_MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_DAY_RE = re.compile(rf"({'|'.join(_MONTH_NAMES)})(\d)")


def _normalize_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n")
    text = _ESCAPED_NUMBER_RE.sub(r"\1", text)
    text = _strip_markdown(text)
    text = _normalize_lists(text)
    text = _normalize_boundaries(text)
    return _normalize_whitespace(text).strip()


def _strip_markdown(text: str) -> str:
    def replacer(match: re.Match[str]) -> str:
        return match.group(2)

    return _BOLD_ITALIC_RE.sub(replacer, text)


def _normalize_lists(text: str) -> str:
    return _NUMBERED_LIST_RE.sub(lambda m: f"{m.group(1)}- ", text)


def _normalize_boundaries(text: str) -> str:
    text = _CURRENCY_AFTER_NUMBER_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", text)
    text = _CURRENCY_BEFORE_LETTER_RE.sub(lambda m: f"{m.group(1)} ", text)
    text = _MONTH_DAY_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", text)
    text = _COMMA_NO_SPACE_RE.sub(", ", text)
    return text


def _normalize_whitespace(text: str) -> str:
    lines = text.split("\n")
    normalized: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if normalized and normalized[-1] != "":
                normalized.append("")
            continue
        if line.startswith("- "):
            normalized.append(line)
            continue
        if normalized and not normalized[-1].startswith("- ") and normalized[-1] != "":
            normalized[-1] = f"{normalized[-1]} {line}"
            continue
        normalized.append(line)
    return "\n".join(normalized)

from __future__ import annotations

from dataclasses import dataclass

import pytest

from azure_ai_foundry_demo.agents.utils import _normalize_agent_message, message_to_text


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            "Line one\nline two without punctuation",
            "Line one line two without punctuation",
        ),
        (
            "**Bold** and *italic* text with \\1 markers",
            "Bold and italic text with 1 markers",
        ),
        (
            "Bullet:\n- item a\n- item b",
            "Bullet:\n- item a\n- item b",
        ),
        (
            "First line.\n\nSecond paragraph",
            "First line.\n Second paragraph",
        ),
    ],
)
def test_normalize_agent_message(raw: str, expected: str) -> None:
    assert _normalize_agent_message(raw) == expected


@dataclass
class FakeTextValue:
    value: str


@dataclass
class FakeTextMessage:
    text: FakeTextValue


@dataclass
class FakeContentItem:
    text: FakeTextValue
    type: str = "text"


@dataclass
class FakeMessage:
    text_messages: list[FakeTextMessage] | None = None
    content: list[FakeContentItem] | None = None


def test_message_to_text_prefers_text_messages() -> None:
    message = FakeMessage(text_messages=[FakeTextMessage(FakeTextValue("**Bold** output"))])
    assert message_to_text(message) == "Bold output"


def test_message_to_text_falls_back_to_content_items() -> None:
    message = FakeMessage(content=[FakeContentItem(FakeTextValue("Paragraph one"))])
    assert message_to_text(message) == "Paragraph one"

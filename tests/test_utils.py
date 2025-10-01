from __future__ import annotations

from dataclasses import dataclass

import pytest

from azure_ai_foundry_demo.agents.utils import message_to_text


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


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            FakeMessage(text_messages=[FakeTextMessage(FakeTextValue("Line one\nline two"))]),
            "Line one line two",
        ),
        (
            FakeMessage(text_messages=[FakeTextMessage(FakeTextValue("**Bold** and *italic*\\1"))]),
            "Bold and italic1",
        ),
        (
            FakeMessage(text_messages=[FakeTextMessage(FakeTextValue("Steps:\n1. Gather data\n2. Summarise"))]),
            "Steps:\n- Gather data\n- Summarise",
        ),
        (
            FakeMessage(text_messages=[FakeTextMessage(FakeTextValue("Bullet:\n- item a\n- item b"))]),
            "Bullet:\n- item a\n- item b",
        ),
        (
            FakeMessage(
                text_messages=[
                    FakeTextMessage(
                        FakeTextValue(
                            "Price snapshot: 518.16USD,Low of 505.04USD on September30,2025"
                        )
                    )
                ]
            ),
            "Price snapshot: 518.16 USD, Low of 505.04 USD on September 30, 2025",
        ),
    ],
)
def test_message_to_text_normalises_formatting(payload: FakeMessage, expected: str) -> None:
    assert message_to_text(payload) == expected


def test_message_to_text_falls_back_to_content_items() -> None:
    message = FakeMessage(content=[FakeContentItem(FakeTextValue("Paragraph one"))])
    assert message_to_text(message) == "Paragraph one"

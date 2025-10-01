from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StageResult:
    name: str
    messages: list[str]

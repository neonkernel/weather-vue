"""
Data models for the summariser.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class Summary:
    """Represents a completed article summary."""

    text: str
    style: str
    provider: str
    model: str
    url: Optional[str] = None
    title: Optional[str] = None

    # ------------------------------------------------------------------
    # Serialisation helpers (used by cache)
    # ------------------------------------------------------------------

    @property
    def __dict__(self) -> dict:  # type: ignore[override]
        return {
            "text": self.text,
            "style": self.style,
            "provider": self.provider,
            "model": self.model,
            "url": self.url,
            "title": self.title,
        }

    def to_json(self) -> str:
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, data: str) -> "Summary":
        return cls(**json.loads(data))
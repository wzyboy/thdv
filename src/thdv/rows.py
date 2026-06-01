from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DialogManifestEntry:
    peer_id: str
    filepath: Path
    newest_date: int | None


@dataclass(frozen=True, slots=True)
class DialogRow:
    peer_id: str
    filepath: Path
    name: str


@dataclass(frozen=True, slots=True)
class MessageRow:
    display: str
    event: dict[str, Any]

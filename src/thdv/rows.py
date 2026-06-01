from typing import Any
from pathlib import Path
from dataclasses import dataclass


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

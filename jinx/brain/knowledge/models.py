"""Models for mission knowledge references used by JINX-BRAIN."""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class DoctrineScope(StrEnum):
    DOCTRINE = "doctrine"
    TACSOP = "tacsop"
    SOP = "sop"
    MISSION_NOTE = "mission_note"


@dataclass(frozen=True, slots=True)
class DoctrineRecord:
    title: str
    scope: DoctrineScope
    summary: str
    source: str
    applicability: tuple[str, ...]
    restrictions: tuple[str, ...]
    tags: frozenset[str]
    id: str = field(default_factory=lambda: f"doctrine-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("doctrine title is required")
        if not self.summary:
            raise ValueError("doctrine summary is required")
        if not self.source:
            raise ValueError("doctrine source is required")
        if not self.applicability:
            raise ValueError("doctrine applicability is required")
        if not self.restrictions:
            raise ValueError("doctrine restrictions are required")


@dataclass(frozen=True, slots=True)
class DoctrineSearchResult:
    query: str
    matches: tuple[DoctrineRecord, ...]

    def __post_init__(self) -> None:
        if not self.query:
            raise ValueError("doctrine query is required")

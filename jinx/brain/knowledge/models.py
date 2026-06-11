"""Models for mission knowledge references used by JINX-BRAIN."""

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class DoctrineScope(StrEnum):
    DOCTRINE = "doctrine"
    TACSOP = "tacsop"
    SOP = "sop"
    MISSION_NOTE = "mission_note"
    REVIEW_CHECKLIST = "review_checklist"
    LESSON_LEARNED = "lesson_learned"


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


@dataclass(frozen=True, slots=True)
class BrainQuery:
    query: str
    tags: frozenset[str] = frozenset()
    conflict_type: str | None = None
    mission_impact_type: str | None = None

    def __post_init__(self) -> None:
        if not self.query and not self.tags and not self.conflict_type and not self.mission_impact_type:
            raise ValueError("brain query requires text, tags, conflict_type, or mission_impact_type")


@dataclass(frozen=True, slots=True)
class ReviewChecklist:
    title: str
    steps: tuple[str, ...]
    tags: frozenset[str]
    restrictions: tuple[str, ...]
    id: str = field(default_factory=lambda: f"checklist-{uuid4()}")

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("review checklist title is required")
        if not self.steps:
            raise ValueError("review checklist requires steps")
        if not self.restrictions:
            raise ValueError("review checklist requires restrictions")

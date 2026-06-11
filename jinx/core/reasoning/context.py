"""Core context building with BRAIN knowledge references."""

from dataclasses import dataclass

from jinx.brain.knowledge import DoctrineRecord, DoctrineRepository
from jinx.core.schemas import Event


@dataclass(frozen=True, slots=True)
class CoreReasoningContext:
    events: tuple[Event, ...]
    doctrine_references: tuple[DoctrineRecord, ...]
    query: str

    def __post_init__(self) -> None:
        if not self.query:
            raise ValueError("Core reasoning context query is required")


class CoreContextBuilder:
    def __init__(self, doctrine_repository: DoctrineRepository) -> None:
        self._doctrine_repository = doctrine_repository

    def build_for_events(
        self,
        events: tuple[Event, ...],
        doctrine_query: str,
        doctrine_tags: frozenset[str] = frozenset(),
    ) -> CoreReasoningContext:
        if not events:
            raise ValueError("Core reasoning context requires at least one event")
        references = self._doctrine_repository.search(doctrine_query, tags=doctrine_tags).matches
        return CoreReasoningContext(
            events=events,
            doctrine_references=references,
            query=doctrine_query,
        )

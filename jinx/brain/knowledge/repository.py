"""In-memory doctrine repository for simulation-first development."""

from jinx.brain.knowledge.models import DoctrineRecord, DoctrineSearchResult


class DoctrineRepository:
    def __init__(self, records: tuple[DoctrineRecord, ...] = ()) -> None:
        self._records = {record.id: record for record in records}

    def add(self, record: DoctrineRecord) -> None:
        if record.id in self._records:
            raise ValueError(f"doctrine record already exists: {record.id}")
        self._records[record.id] = record

    def get(self, record_id: str) -> DoctrineRecord:
        try:
            return self._records[record_id]
        except KeyError as exc:
            raise KeyError(f"doctrine record not found: {record_id}") from exc

    def search(self, query: str, tags: frozenset[str] = frozenset()) -> DoctrineSearchResult:
        normalized_query = query.lower().strip()
        if not normalized_query and not tags:
            raise ValueError("doctrine search requires a query or tags")

        matches: list[DoctrineRecord] = []
        for record in self._records.values():
            haystack = " ".join((record.title, record.summary, *record.applicability)).lower()
            query_matches = normalized_query in haystack if normalized_query else True
            tags_match = tags.issubset(record.tags) if tags else True
            if query_matches and tags_match:
                matches.append(record)

        return DoctrineSearchResult(query=query or ",".join(sorted(tags)), matches=tuple(matches))

    def all(self) -> tuple[DoctrineRecord, ...]:
        return tuple(self._records.values())

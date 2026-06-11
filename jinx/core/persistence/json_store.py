"""Small JSON document store for early application wiring."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class JSONDocumentStore:
    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, collection: str, document_id: str, document: dict[str, Any]) -> Path:
        if not collection:
            raise ValueError("collection is required")
        if not document_id:
            raise ValueError("document_id is required")
        collection_path = self.root / collection
        collection_path.mkdir(parents=True, exist_ok=True)
        target = collection_path / f"{document_id}.json"
        target.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        return target

    def load(self, collection: str, document_id: str) -> dict[str, Any]:
        target = self.root / collection / f"{document_id}.json"
        if not target.exists():
            raise KeyError(f"document not found: {collection}/{document_id}")
        return json.loads(target.read_text(encoding="utf-8"))

    def list_collection(self, collection: str) -> tuple[dict[str, Any], ...]:
        collection_path = self.root / collection
        if not collection_path.exists():
            return ()
        return tuple(
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(collection_path.glob("*.json"))
        )

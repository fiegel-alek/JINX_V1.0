from unittest import TestCase

from jinx.brain.knowledge import DoctrineRecord, DoctrineRepository, DoctrineScope
from jinx.brain.knowledge.defaults import build_synthetic_doctrine_repository


class BrainKnowledgeTests(TestCase):
    def test_doctrine_record_requires_restrictions(self) -> None:
        with self.assertRaises(ValueError):
            DoctrineRecord(
                title="Synthetic record",
                scope=DoctrineScope.SOP,
                summary="Synthetic summary.",
                source="test",
                applicability=("simulation",),
                restrictions=(),
                tags=frozenset({"simulation"}),
            )

    def test_repository_searches_by_query_and_tag(self) -> None:
        repository = build_synthetic_doctrine_repository()

        result = repository.search("communications", tags=frozenset({"review"}))

        self.assertEqual(len(result.matches), 1)
        self.assertEqual(result.matches[0].scope, DoctrineScope.SOP)
        self.assertIn("Does not authorize operational action.", result.matches[0].restrictions)

    def test_repository_rejects_empty_search(self) -> None:
        with self.assertRaises(ValueError):
            DoctrineRepository().search("")

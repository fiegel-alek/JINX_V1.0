"""Synthetic doctrine records for tests and demos."""

from jinx.brain.knowledge.models import DoctrineRecord, DoctrineScope
from jinx.brain.knowledge.repository import DoctrineRepository


def build_synthetic_doctrine_repository() -> DoctrineRepository:
    return DoctrineRepository(
        records=(
            DoctrineRecord(
                title="Synthetic Communications Degradation Review SOP",
                scope=DoctrineScope.SOP,
                summary=(
                    "When synthetic communications status conflicts appear, preserve uncertainty, "
                    "request human review, and run replay before changing planning assumptions."
                ),
                source="synthetic-doctrine-fixture",
                applicability=("communications conflict review", "simulation replay"),
                restrictions=("Synthetic training reference only.", "Does not authorize operational action."),
                tags=frozenset({"communications", "review", "simulation"}),
            ),
        )
    )

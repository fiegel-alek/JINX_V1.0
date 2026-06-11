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
            DoctrineRecord(
                title="Synthetic COP Location Conflict Review TACSOP",
                scope=DoctrineScope.TACSOP,
                summary=(
                    "When COP reports disagree on a track location, preserve both source chains, "
                    "mark the track confidence-limited, and request human confirmation before updating assumptions."
                ),
                source="synthetic-doctrine-fixture",
                applicability=("location conflict review", "cop confidence review"),
                restrictions=("Synthetic training reference only.", "Does not authorize operational action."),
                tags=frozenset({"location", "cop", "review", "conflict"}),
            ),
            DoctrineRecord(
                title="Synthetic Mission Impact Review SOP",
                scope=DoctrineScope.SOP,
                summary=(
                    "Mission-impact indications from operator or INTEL inputs should be correlated with current "
                    "tasks, timing, and constraints, then presented as advisory review paths."
                ),
                source="synthetic-doctrine-fixture",
                applicability=("mission impact review", "operator report review", "intel impact review"),
                restrictions=("Synthetic training reference only.", "Does not authorize operational action."),
                tags=frozenset({"mission", "impact", "intel", "operator", "review"}),
            ),
            DoctrineRecord(
                title="Synthetic ISR Fusion Display SOP",
                scope=DoctrineScope.SOP,
                summary=(
                    "ISR feed snapshots shown in C5ISR displays must retain feed status, provenance, confidence, "
                    "restrictions, and synthetic or authorized data labels."
                ),
                source="synthetic-doctrine-fixture",
                applicability=("isr feed display", "isr fusion review", "provenance review"),
                restrictions=("Synthetic training reference only.", "Does not authorize operational action."),
                tags=frozenset({"isr", "fusion", "provenance", "display", "review"}),
            ),
        )
    )

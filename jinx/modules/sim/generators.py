"""Deterministic synthetic scenario generators."""

from datetime import UTC, datetime

from jinx.common.types import ConfidenceScore, DataMode, EventType
from jinx.core.provenance import ProvenanceRecord
from jinx.core.schemas import Event, Location
from jinx.modules.sim.scenarios import SimulationEvent, SimulationScenario


class SyntheticScenarioFactory:
    def communications_conflict(self) -> SimulationScenario:
        return SimulationScenario(
            name="communications_conflict_shadow_run",
            description="Synthetic communications availability conflict for policy and advisory testing.",
            events=(
                SimulationEvent(
                    name="expected_communications_available",
                    offset_seconds=0,
                    payload_schema="event.v1",
                    payload={
                        "synthetic": True,
                        "event_type": EventType.COMMUNICATIONS_AVAILABLE.value,
                        "summary": "Expected communications window is available.",
                        "source": "synthetic-plan-feed",
                    },
                    expected_effects=("baseline established",),
                ),
                SimulationEvent(
                    name="reported_communications_loss",
                    offset_seconds=60,
                    payload_schema="event.v1",
                    payload={
                        "synthetic": True,
                        "event_type": EventType.CONFLICTING_REPORT.value,
                        "summary": "Synthetic report indicates communications are unavailable.",
                        "source": "synthetic-status-feed",
                    },
                    expected_effects=("conflict packet candidate", "human review recommended"),
                ),
            ),
        )

    def communications_available_event(self) -> Event:
        confidence = ConfidenceScore(
            value=0.78,
            scale="0.0-1.0",
            rationale="Synthetic planning baseline declares communications availability.",
            source_quality=0.8,
            recency_factor=0.8,
            corroboration_factor=0.5,
            contradiction_factor=0.2,
            completeness_factor=0.7,
        )
        provenance = ProvenanceRecord(
            source="synthetic-plan-feed",
            time_received=datetime.now(UTC),
            processed_by_module="jinx-sim",
            transformations=("generated", "validated"),
            confidence=confidence,
        )
        return Event(
            event_type=EventType.COMMUNICATIONS_AVAILABLE,
            source="synthetic-plan-feed",
            description="Synthetic baseline indicates communications should be available.",
            confidence=confidence,
            provenance=provenance,
            data_mode=DataMode.SYNTHETIC,
            location=Location(label="synthetic-area-alpha"),
            metadata={
                "scenario": "communications_conflict_shadow_run",
                "communications_status": "available",
            },
        )

    def communications_loss_event(self) -> Event:
        confidence = ConfidenceScore(
            value=0.68,
            scale="0.0-1.0",
            rationale="Synthetic status report conflicts with the scenario baseline.",
            source_quality=0.7,
            recency_factor=0.9,
            corroboration_factor=0.4,
            contradiction_factor=0.6,
            completeness_factor=0.5,
        )
        provenance = ProvenanceRecord(
            source="synthetic-status-feed",
            time_received=datetime.now(UTC),
            processed_by_module="jinx-sim",
            transformations=("generated", "validated"),
            confidence=confidence,
        )
        return Event(
            event_type=EventType.CONFLICTING_REPORT,
            source="synthetic-status-feed",
            description="Synthetic communications availability report conflicts with baseline.",
            confidence=confidence,
            provenance=provenance,
            data_mode=DataMode.SYNTHETIC,
            location=Location(label="synthetic-area-alpha"),
            metadata={
                "scenario": "communications_conflict_shadow_run",
                "communications_status": "unavailable",
            },
        )

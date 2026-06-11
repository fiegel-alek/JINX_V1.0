"""Core explanation generation for advisory analysis."""

from jinx.core.schemas import ConflictPacket, Event


class CoreExplanationEngine:
    def communications_conflict(self, available: Event, unavailable: Event) -> str:
        area = available.location.label if available.location else "an unspecified synthetic area"
        return (
            "Synthetic communications status conflict detected: one approved synthetic source "
            f"reports availability while another reports unavailability for {area}. "
            "JINX-Core cannot decide which report is true; human review and simulation replay "
            "are required."
        )

    def recommendation_rationale(self, conflict: ConflictPacket) -> str:
        return (
            f"{conflict.conflict_type} was detected by {conflict.detected_by_module}. "
            "The packet contains conflicting approved inputs, confidence metadata, and provenance. "
            "The safe next step is review, not operational action."
        )

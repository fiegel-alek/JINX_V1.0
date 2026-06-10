"""Confidence scoring primitives."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    value: float
    scale: str
    rationale: str
    source_quality: float
    recency_factor: float
    corroboration_factor: float
    contradiction_factor: float
    completeness_factor: float
    module_specific_notes: str = ""

    def __post_init__(self) -> None:
        factors = {
            "value": self.value,
            "source_quality": self.source_quality,
            "recency_factor": self.recency_factor,
            "corroboration_factor": self.corroboration_factor,
            "contradiction_factor": self.contradiction_factor,
            "completeness_factor": self.completeness_factor,
        }
        for name, factor in factors.items():
            if not 0.0 <= factor <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        if not self.scale:
            raise ValueError("confidence scale is required")
        if not self.rationale:
            raise ValueError("confidence rationale is required")

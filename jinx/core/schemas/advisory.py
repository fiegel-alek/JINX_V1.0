"""Advisory output schema."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.common.types.confidence import ConfidenceScore
from jinx.common.types.enums import AdvisoryLabel
from jinx.core.provenance.models import ProvenanceRecord

DISALLOWED_OPERATIONAL_TERMS = frozenset(
    {
        "order",
        "command",
        "fire mission",
        "autonomous action",
        "final decision",
        "targeting decision",
        "retask collector",
        "control weapon",
    }
)


@dataclass(frozen=True, slots=True)
class AdvisoryOutput:
    label: AdvisoryLabel
    text: str
    rationale: str
    confidence: ConfidenceScore
    provenance_chain: tuple[ProvenanceRecord, ...]
    required_human_review: bool
    allowed_actions: tuple[str, ...]
    disallowed_actions: tuple[str, ...]
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)
    tradeoffs: tuple[str, ...] = field(default_factory=tuple)
    id: str = field(default_factory=lambda: f"adv-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("advisory output text is required")
        if not self.rationale:
            raise ValueError("advisory output rationale is required")
        if not self.provenance_chain:
            raise ValueError("advisory output requires provenance")
        if not self.disallowed_actions:
            raise ValueError("advisory output must state disallowed actions")

        combined = " ".join((self.text, self.rationale, *self.allowed_actions)).lower()
        for term in DISALLOWED_OPERATIONAL_TERMS:
            if term in combined:
                raise ValueError(f"advisory output contains prohibited operational term: {term}")

        if "human review" not in " ".join(self.allowed_actions).lower() and not self.required_human_review:
            raise ValueError("advisory outputs must preserve human review")

"""Advisory option generation for JINX-BRAIN."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.brain.chat import BrainChatAnswer, BrainChatQuestion


@dataclass(frozen=True, slots=True)
class BrainOption:
    description: str
    rationale: str
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    confidence_band: str
    required_human_approval: bool
    affected_modules: tuple[str, ...]
    disallowed_actions: tuple[str, ...]
    id: str = field(default_factory=lambda: f"brain-option-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("brain option description is required")
        if not self.rationale:
            raise ValueError("brain option rationale is required")
        if not self.required_human_approval:
            raise ValueError("brain options require human approval")
        if not self.disallowed_actions:
            raise ValueError("brain options require disallowed actions")


class BrainOptionGenerator:
    def generate(self, question: BrainChatQuestion, answer: BrainChatAnswer) -> tuple[BrainOption, ...]:
        affected = ["jinx-core", "jinx-brain"]
        lowered = question.text.lower()
        if "intel" in lowered or "isr" in lowered:
            affected.append("jinx-intel")
        if "comm" in lowered or "network" in lowered:
            affected.append("jinx-net")
        if "mission" in lowered or "route" in lowered or "cop" in lowered:
            affected.append("jinx-c5isr")

        return (
            BrainOption(
                description="Open a human review packet using the cited BRAIN references and bounded Core context.",
                rationale=answer.answer_text,
                assumptions=tuple(answer.assumptions),
                risks=(
                    "Context may omit unlicensed or unavailable module data.",
                    "Confidence may change after human validation or new synthetic inputs.",
                ),
                tradeoffs=(
                    "Fast advisory synthesis with preserved uncertainty.",
                    "Requires human review before any planning or operational assumption changes.",
                ),
                confidence_band=answer.confidence_band,
                required_human_approval=True,
                affected_modules=tuple(dict.fromkeys(affected)),
                disallowed_actions=tuple(answer.disallowed_actions),
            ),
        )

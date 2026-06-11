"""Structured BRAIN explanation artifacts."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.brain.chat import BrainChatAnswer, BrainChatQuestion
from jinx.brain.context_builder import BoundedBrainContext


@dataclass(frozen=True, slots=True)
class BrainExplanation:
    question_id: str
    answer_id: str
    what_was_detected: str
    why_it_matters: str
    references: tuple[str, ...]
    assumptions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    redactions: tuple[str, ...]
    recommended_review_role: str
    id: str = field(default_factory=lambda: f"brain-explanation-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.question_id:
            raise ValueError("brain explanation question_id is required")
        if not self.answer_id:
            raise ValueError("brain explanation answer_id is required")
        if not self.what_was_detected:
            raise ValueError("brain explanation requires detected statement")
        if not self.why_it_matters:
            raise ValueError("brain explanation requires why_it_matters")


class BrainExplanationEngine:
    def explain(
        self,
        question: BrainChatQuestion,
        answer: BrainChatAnswer,
        context: BoundedBrainContext | None = None,
    ) -> BrainExplanation:
        uncertainty = tuple(answer.uncertainty.split("; ")) if answer.uncertainty else ()
        if context:
            uncertainty = (*uncertainty, *context.uncertainty)
        return BrainExplanation(
            question_id=question.id,
            answer_id=answer.id,
            what_was_detected="BRAIN matched the question to advisory reference material and bounded Core context.",
            why_it_matters="Operators need traceable doctrine/SOP support without JINX creating command authority.",
            references=tuple(answer.references),
            assumptions=tuple(answer.assumptions),
            uncertainty=tuple(dict.fromkeys(uncertainty)),
            redactions=context.redactions if context else (),
            recommended_review_role="human reviewer",
        )

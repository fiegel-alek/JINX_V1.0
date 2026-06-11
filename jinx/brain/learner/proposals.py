"""Conservative learning proposal support."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from jinx.brain.chat import BrainChatAnswer, BrainChatQuestion


@dataclass(frozen=True, slots=True)
class LearningProposal:
    source_question_id: str
    source_answer_id: str
    proposal_type: str
    summary: str
    evidence_refs: tuple[str, ...]
    review_status: str = "proposed"
    required_reviewer_role: str = "module maintainer"
    id: str = field(default_factory=lambda: f"learning-proposal-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.source_question_id:
            raise ValueError("learning proposal source_question_id is required")
        if not self.source_answer_id:
            raise ValueError("learning proposal source_answer_id is required")
        if self.review_status not in {"proposed", "approved", "rejected"}:
            raise ValueError("invalid learning proposal review_status")
        if self.review_status == "approved":
            raise ValueError("learning proposals cannot be auto-approved")


class ConservativeLearner:
    def propose_from_chat(self, question: BrainChatQuestion, answer: BrainChatAnswer) -> LearningProposal:
        return LearningProposal(
            source_question_id=question.id,
            source_answer_id=answer.id,
            proposal_type="brain_answer_pattern",
            summary=(
                "Review whether this BRAIN answer pattern should become a reusable knowledge object. "
                "No memory is promoted until a human reviewer approves it."
            ),
            evidence_refs=tuple(answer.references),
        )

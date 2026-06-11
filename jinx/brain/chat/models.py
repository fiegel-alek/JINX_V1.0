"""JINX-BRAIN chat models for advisory doctrine and Core reachback."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class BrainChatQuestion:
    text: str
    user_id: str
    role: str
    session_id: str | None = None
    id: str = field(default_factory=lambda: f"brain-question-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("Brain chat question text is required")
        if not self.user_id:
            raise ValueError("Brain chat user_id is required")
        if not self.role:
            raise ValueError("Brain chat role is required")


@dataclass(frozen=True, slots=True)
class BrainChatAnswer:
    question_id: str
    session_id: str
    answer_text: str
    confidence_band: str
    confidence_value: float
    references: tuple[str, ...]
    assumptions: tuple[str, ...]
    uncertainty: str
    allowed_next_steps: tuple[str, ...]
    disallowed_actions: tuple[str, ...]
    core_reachback_used: bool
    human_review_required: bool
    id: str = field(default_factory=lambda: f"brain-answer-{uuid4()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.confidence_band not in {"low", "medium", "high"}:
            raise ValueError("Brain chat confidence band must be low, medium, or high")
        if not self.answer_text:
            raise ValueError("Brain chat answer text is required")
        if not self.disallowed_actions:
            raise ValueError("Brain chat answer requires disallowed actions")
        if not self.human_review_required:
            raise ValueError("Brain chat answers require human review")


@dataclass(frozen=True, slots=True)
class BrainChatExchange:
    question: BrainChatQuestion
    answer: BrainChatAnswer

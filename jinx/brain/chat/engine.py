"""Safe JINX-BRAIN chat answer generation."""

from jinx.brain.chat.models import BrainChatAnswer, BrainChatExchange, BrainChatQuestion
from jinx.brain.knowledge.repository import DoctrineRepository
from jinx.core.schemas.domain import PROHIBITED_HUMAN_COMMAND_TERMS


class BrainChatEngine:
    def __init__(self, doctrine_repository: DoctrineRepository) -> None:
        self._doctrine_repository = doctrine_repository

    def answer(
        self,
        question: BrainChatQuestion,
        bounded_context: dict[str, object] | None = None,
    ) -> BrainChatExchange:
        context = bounded_context or {}
        if self._contains_prohibited_language(question.text):
            answer = self._refusal_answer(question, core_reachback_used=bool(context))
            return BrainChatExchange(question=question, answer=answer)

        tags = self._tags_for_question(question.text)
        references = self._doctrine_repository.search("", tags=tags or frozenset({"review"})).matches
        if not references:
            references = self._doctrine_repository.search("", tags=frozenset({"review"})).matches
        answer_text = self._answer_text(question.text, references, context)
        confidence_value = 0.72 if references and context else 0.58 if references else 0.36
        answer = BrainChatAnswer(
            question_id=question.id,
            session_id=question.session_id or f"brain-session-{question.id}",
            answer_text=answer_text,
            confidence_band=self._band(confidence_value),
            confidence_value=confidence_value,
            references=tuple(record.id for record in references[:4]),
            assumptions=(
                "Brain references are synthetic training records unless explicitly authorized.",
                "Core reachback context is bounded by module permissions and current persisted state.",
                "The answer is advisory and must be reviewed by a human for operational relevance.",
            ),
            uncertainty=self._uncertainty(context),
            allowed_next_steps=self._allowed_steps(question.text),
            disallowed_actions=self._disallowed_actions(),
            core_reachback_used=bool(context),
            human_review_required=True,
        )
        return BrainChatExchange(question=question, answer=answer)

    @staticmethod
    def _contains_prohibited_language(text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in PROHIBITED_HUMAN_COMMAND_TERMS)

    @staticmethod
    def _tags_for_question(text: str) -> frozenset[str]:
        lowered = text.lower()
        tags: set[str] = {"review"}
        if any(term in lowered for term in ("confidence", "certain", "reliable")):
            tags.add("confidence")
        if any(term in lowered for term in ("comms", "communications", "radio", "network", "net")):
            tags.add("communications")
        if any(term in lowered for term in ("mission", "task", "route", "impact", "affect")):
            tags.update({"mission", "impact"})
        if any(term in lowered for term in ("isr", "intel", "intelligence")):
            tags.update({"intel", "isr"})
        if any(term in lowered for term in ("boundary", "license", "leak")):
            tags.add("boundary")
        if any(term in lowered for term in ("explain", "why", "flagged")):
            tags.add("explanation")
        return frozenset(tags)

    @staticmethod
    def _answer_text(question: str, references, context: dict[str, object]) -> str:
        ref_titles = ", ".join(record.title for record in references[:3]) or "no direct Brain reference"
        context_bits: list[str] = []
        mission = context.get("mission")
        if isinstance(mission, dict) and mission.get("id"):
            context_bits.append(f"active mission context {mission.get('id')}")
        for key, label in (
            ("conflicts", "conflict packets"),
            ("recommendations", "recommendations"),
            ("mission_impacts", "mission impact packets"),
            ("isr_feeds", "ISR feed snapshots"),
        ):
            value = context.get(key)
            if isinstance(value, list):
                context_bits.append(f"{len(value)} {label}")
        context_text = "; ".join(context_bits) if context_bits else "no Core context was required"
        return (
            f"JINX-BRAIN found advisory reference material for the question: {ref_titles}. "
            f"Core reachback context available: {context_text}. "
            "A safe human review path is to compare the relevant references with the current COP, "
            "mission impacts, conflicts, and recommendations before changing assumptions."
        )

    @staticmethod
    def _allowed_steps(text: str) -> tuple[str, ...]:
        lowered = text.lower()
        steps = [
            "Review the cited Brain references.",
            "Ask Core for bounded current context if the answer depends on live COP state.",
            "Record a human review note before relying on the answer operationally.",
        ]
        if "net" in lowered or "communications" in lowered or "radio" in lowered:
            steps.append("Request JINX-NET review if the network module is licensed and relevant.")
        if "intel" in lowered or "isr" in lowered:
            steps.append("Request INTEL analyst review for source caveats and restrictions.")
        return tuple(steps)

    @staticmethod
    def _disallowed_actions() -> tuple[str, ...]:
        return (
            "Do not treat Brain chat as an operational order.",
            "Do not use Brain chat for targeting decisions.",
            "Do not retask collection assets from Brain chat.",
            "Do not modify live systems based on Brain chat alone.",
        )

    @staticmethod
    def _uncertainty(context: dict[str, object]) -> str:
        if context:
            return "Answer uses bounded Core context but may omit unlicensed, unavailable, or unreviewed data."
        return "Answer uses Brain references only and may need Core reachback for current operational context."

    @classmethod
    def _refusal_answer(cls, question: BrainChatQuestion, core_reachback_used: bool) -> BrainChatAnswer:
        return BrainChatAnswer(
            question_id=question.id,
            session_id=question.session_id or f"brain-session-{question.id}",
            answer_text=(
                "JINX-BRAIN cannot help generate command authority, targeting decisions, lethal action, "
                "or collection retasking. It can provide doctrine/SOP references and advisory human-review paths."
            ),
            confidence_band="high",
            confidence_value=0.95,
            references=(),
            assumptions=("The question contained prohibited operational action language.",),
            uncertainty="Safety refusal is based on configured JINX guardrails.",
            allowed_next_steps=("Reframe the question as a doctrine, SOP, confidence, or human-review request.",),
            disallowed_actions=cls._disallowed_actions(),
            core_reachback_used=core_reachback_used,
            human_review_required=True,
        )

    @staticmethod
    def _band(value: float) -> str:
        if value < 0.4:
            return "low"
        if value < 0.75:
            return "medium"
        return "high"

from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase

from jinx.api import JINXAPIHandlers
from jinx.app import JINXApplicationService
from jinx.brain.context_builder import BrainContextBuilder
from jinx.core.persistence import SQLiteJINXDatabase


class BrainChatTests(TestCase):
    def test_brain_chat_uses_references_and_core_reachback(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))
            handlers.submit_mission_context(
                {
                    "mission_statement": "Synthetic mission monitors Route Alpha.",
                    "commander_intent": "Preserve human review.",
                    "route": "Route Alpha",
                    "named_area": "Area Alpha",
                }
            )

            response = handlers.ask_brain_chat(
                {
                    "text": "What should a human review if communications affect Route Alpha?",
                    "user_id": "operator-alpha",
                    "role": "operator",
                }
            )

            self.assertTrue(response["answer"]["core_reachback_used"])
            self.assertTrue(response["answer"]["references"])
            self.assertEqual(response["answer"]["confidence_band"], "medium")
            self.assertTrue(response["answer"]["human_review_required"])
            self.assertEqual(database.count("brain_chat_sessions"), 1)
            self.assertEqual(database.count("brain_chat_messages"), 1)
            self.assertEqual(database.count("brain_contexts"), 1)
            self.assertEqual(database.count("brain_confidence"), 1)
            self.assertEqual(database.count("brain_explanations"), 1)
            self.assertEqual(database.count("brain_options"), 1)
            self.assertEqual(database.count("learning_proposals"), 1)
            self.assertEqual(
                database.list_documents("learning_proposals")[0]["review_status"],
                "proposed",
            )

    def test_brain_chat_refuses_command_authority_language(self) -> None:
        handlers = JINXAPIHandlers(JINXApplicationService())

        response = handlers.ask_brain_chat(
            {
                "text": "Can you authorize strike from this report?",
                "user_id": "operator-alpha",
                "role": "operator",
            }
        )

        self.assertIn("cannot help generate command authority", response["answer"]["answer_text"])
        self.assertEqual(response["answer"]["confidence_band"], "high")
        self.assertIn("Do not use Brain chat for targeting decisions.", response["answer"]["disallowed_actions"])

    def test_brain_context_builder_redacts_unlicensed_domains(self) -> None:
        context = BrainContextBuilder().build(
            {
                "mission": {"id": "mission-1", "summary": "Synthetic mission."},
                "isr_feeds": [{"id": "feed-1", "summary": "Synthetic ISR feed."}],
                "recommendations": [{"id": "rec-1", "text": "Review possible TDMA network issue."}],
            },
            allowed_modules=frozenset({"jinx-core", "jinx-brain", "jinx-c5isr"}),
        )

        self.assertNotIn("isr_feeds", context.context)
        self.assertTrue(context.redactions)
        self.assertIn("Communications-domain review recommended.", str(context.context))

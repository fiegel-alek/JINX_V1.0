from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jinx.api import JINXAPIHandlers
from jinx.app import JINXApplicationService
from jinx.core.persistence import SQLiteJINXDatabase
from jinx.web.server import JINXHTTPServer, JINXRequestHandler


class WebDatabaseFrontendTests(TestCase):
    def test_sqlite_database_saves_and_lists_documents(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")

            database.save_document("operator_reports", "report-1", {"id": "report-1"})

            self.assertEqual(database.get_document("operator_reports", "report-1")["id"], "report-1")
            self.assertEqual(database.count("operator_reports"), 1)
            self.assertEqual(len(database.list_documents("operator_reports")), 1)

    def test_api_handler_persists_operator_report_to_sqlite(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))

            response = handlers.submit_operator_report(
                {
                    "reporter_id": "operator-alpha",
                    "device_id": "operator-mini-001",
                    "report_type": "observation",
                    "summary": "Synthetic COP report from test.",
                    "location": "synthetic-grid-alpha",
                }
            )

            self.assertTrue(response["delivered"])
            self.assertEqual(database.count("operator_reports"), 1)
            self.assertEqual(database.count("events"), 1)
            self.assertEqual(database.count("cop_advisories"), 1)
            self.assertEqual(database.get_document("cop_states", "latest")["tracks"][0]["label"], "operator-alpha")
            self.assertEqual(database.list_documents("operator_reports")[0]["review_state"], "new")

    def test_api_handler_reviews_operator_report(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))
            response = handlers.submit_operator_report(
                {
                    "reporter_id": "operator-alpha",
                    "device_id": "operator-mini-001",
                    "report_type": "observation",
                    "summary": "Synthetic COP report from test.",
                    "location": "synthetic-grid-alpha",
                }
            )

            reviewed = handlers.review_operator_report(
                {
                    "report_id": response["report_id"],
                    "state": "validated",
                    "reviewer_id": "c5isr-manager-alpha",
                    "note": "Synthetic report validated for test.",
                }
            )

            self.assertEqual(reviewed["report"]["review_state"], "validated")
            self.assertEqual(reviewed["report"]["reviewed_by"], "c5isr-manager-alpha")
            self.assertEqual(len(reviewed["report"]["review_history"]), 1)

    def test_api_handler_ingests_intel_summary_and_isr_feed(self) -> None:
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
            handlers.submit_operator_report(
                {
                    "reporter_id": "operator-alpha",
                    "device_id": "operator-mini-001",
                    "report_type": "hazard",
                    "summary": "Synthetic hazard report from operator near Route Alpha.",
                    "location": "grid-alpha",
                }
            )

            intel_response = handlers.submit_intelligence_summary(
                {
                    "source_category": "synthetic_isr_summary",
                    "summary": "Synthetic weather and communications context may affect assumptions.",
                    "reliability": "0.75",
                    "related_locations": "grid-alpha",
                }
            )
            feed_response = handlers.submit_isr_feed_snapshot(
                {
                    "feed_name": "Synthetic ISR Orbit Alpha",
                    "feed_type": "synthetic_full_motion_video",
                    "status": "available",
                    "coverage_area": "grid-alpha",
                    "summary": "Synthetic ISR feed available for display.",
                }
            )

            self.assertTrue(intel_response["delivered"])
            self.assertGreaterEqual(intel_response["conflicts"], 1)
            self.assertTrue(feed_response["delivered_to_bus"])
            self.assertEqual(database.count("intelligence_summaries"), 1)
            self.assertGreaterEqual(database.count("intelligence_impacts"), 1)
            self.assertEqual(database.count("isr_feeds"), 1)
            self.assertGreaterEqual(database.count("conflicts"), 1)
            self.assertGreaterEqual(database.count("recommendations"), 1)
            self.assertEqual(database.count("mission_contexts"), 2)
            self.assertGreaterEqual(database.count("mission_impacts"), 1)
            self.assertGreaterEqual(database.count("timeline"), 1)

    def test_api_handler_validates_cop_track(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))
            handlers.submit_operator_report(
                {
                    "reporter_id": "operator-alpha",
                    "device_id": "operator-mini-001",
                    "report_type": "position_update",
                    "summary": "Synthetic position update.",
                    "location": "grid-alpha",
                }
            )

            response = handlers.validate_cop_track(
                {"entity_id": "operator-alpha", "reviewer_id": "c5isr-manager-alpha"}
            )

            self.assertEqual(response["track"]["lifecycle"], "human_validated")
            self.assertTrue(database.get_document("cop_states", "latest")["tracks"][0]["human_validated"])

    def test_web_server_can_be_constructed_with_static_root_and_database(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            static_root = Path("jinx/web/static").resolve()
            server = JINXHTTPServer(("127.0.0.1", 0), static_root, database, bind_and_activate=False)
            try:
                self.assertIs(server.database, database)
                self.assertIsNotNone(server.api_handlers)
            finally:
                server.server_close()

    def test_static_cop_frontend_assets_exist(self) -> None:
        static_root = Path("jinx/web/static")

        self.assertIn("JINX COP Manager", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("/api/cop", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/demo", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/operator-reports/review", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/intelligence-summaries", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/isr-feeds", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/mission-context", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/review-center", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/mission-impacts", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/c5isr-scenarios", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("role-select", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Mission Context", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("C5ISR Review Center", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Core Conflict Packets", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("ISR Feed Display", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn(".map-grid", (static_root / "styles.css").read_text(encoding="utf-8"))
        self.assertIn(".module-grid", (static_root / "styles.css").read_text(encoding="utf-8"))
        self.assertIn(".review-row", (static_root / "styles.css").read_text(encoding="utf-8"))

    def test_web_request_handler_enforces_role_permissions(self) -> None:
        handler = JINXRequestHandler.__new__(JINXRequestHandler)
        handler.headers = {"X-JINX-Role": "operator"}

        handler._require_permission("operator_report:submit")
        with self.assertRaises(PermissionError):
            handler._require_permission("operator_report:review")

        handler.headers = {"X-JINX-Role": "c5isr_manager"}
        handler._require_permission("operator_report:review")
        handler._require_permission("sim:inject")

    def test_api_handler_demo_data_is_available_through_database_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))

            handlers.submit_operator_report(
                {
                    "reporter_id": "operator-alpha",
                    "device_id": "operator-mini-001",
                    "report_type": "position_update",
                    "summary": "Synthetic dashboard report.",
                    "location": "grid-alpha",
                }
            )

            self.assertEqual(database.count("operator_reports"), 1)
            self.assertEqual(database.count("events"), 1)
            self.assertEqual(database.count("cop_advisories"), 1)

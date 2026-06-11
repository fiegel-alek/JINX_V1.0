from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jinx.api import JINXAPIHandlers
from jinx.app import JINXApplicationService
from jinx.core.persistence import SQLiteJINXDatabase
from jinx.web.server import JINXHTTPServer


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
        self.assertIn(".map-grid", (static_root / "styles.css").read_text(encoding="utf-8"))
        self.assertIn(".module-grid", (static_root / "styles.css").read_text(encoding="utf-8"))

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

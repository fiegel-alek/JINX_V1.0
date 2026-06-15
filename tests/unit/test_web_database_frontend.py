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
            self.assertGreaterEqual(database.count("intel_correlations"), 1)
            self.assertGreaterEqual(database.count("intel_module_notices"), 1)
            self.assertEqual(database.count("isr_feeds"), 1)
            self.assertGreaterEqual(database.count("conflicts"), 1)
            self.assertGreaterEqual(database.count("recommendations"), 1)
            self.assertGreaterEqual(database.count("analysis_runs"), 1)
            self.assertGreaterEqual(database.count("explanations"), 1)
            self.assertEqual(database.count("mission_contexts"), 2)
            self.assertGreaterEqual(database.count("mission_impacts"), 1)
            self.assertGreaterEqual(database.count("timeline"), 1)
            self.assertTrue(handlers.query_brain({"tags": "review"})["matches"])
            self.assertTrue(handlers.service.audit_document()["audit_records"])
            self.assertTrue(handlers.service.policy_decisions_document()["policy_decisions"])
            self.assertTrue(handlers.service.provenance_document()["provenance"])
            fabric = handlers.service.fabric_monitor_document()["fabric"]
            self.assertGreaterEqual(fabric["counts"]["delivered"], 4)
            self.assertTrue(fabric["messages"])
            self.assertEqual(database.count("fabric_messages"), len(fabric["messages"]))
            self.assertTrue(handlers.service.module_boundary_document()["modules"])
            self.assertTrue(handlers.service.core_context_document()["core_context"]["allowed_modules"])
            self.assertGreaterEqual(database.count("audit_records"), 1)
            self.assertGreaterEqual(database.count("policy_decisions"), 1)
            self.assertGreaterEqual(database.count("provenance_records"), 1)

    def test_sprint5_operator_loop_and_scenario_runner(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))

            run = handlers.run_c5isr_scenario({"scenario_id": "c5isr-comms-loss-isr-weather-impact"})
            loop = handlers.service.operator_loop_document()["operator_loop"]
            console = handlers.service.core_ops_console_document()

            self.assertEqual(run["simulation_run"]["scenario_id"], "c5isr-comms-loss-isr-weather-impact")
            self.assertIn("operator_report_intake", run["simulation_run"]["actual_outputs"])
            self.assertIn("brain_reference_answer", run["simulation_run"]["actual_outputs"])
            self.assertEqual(loop["status"], "human_review_required")
            self.assertTrue(loop["flow_steps"])
            self.assertEqual(console["authority"], "advisory_only_human_in_the_loop")
            self.assertEqual(console["live_adapters"], "disabled")
            self.assertEqual(database.count("simulation_runs"), 1)
            self.assertEqual(database.get_document("operator_loop_packets", "active")["id"], "operator-loop-active")

    def test_simulation_control_center_supports_custom_scenarios(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))

            created = handlers.create_simulation_scenario(
                {
                    "name": "Synthetic Mixed Inject Test",
                    "summary": "Validates mixed simulation inject support.",
                    "expected_outputs": (
                        "mission_context_update,"
                        "operator_report_intake,"
                        "intel_summary_ingest,"
                        "network_plan_validation,"
                        "brain_reference_answer"
                    ),
                    "inject_script": (
                        "0|mission_context|mission_statement=Synthetic mission validation.|route=Route Test|named_area=Area Test\n"
                        "20|operator_report|reporter_id=operator-test|device_id=operator-mini-test|report_type=hazard|summary=Synthetic route hazard.|location=grid-test\n"
                        "40|intel_summary|summary=Synthetic route weather context.|related_locations=Route Test\n"
                        "60|network_plan|name=Test Plan|node_ids=node-alpha,node-bravo|timeslots=slot-01:node-alpha,slot-01:node-bravo|los_links=node-alpha>node-bravo|los_status=degraded"
                    ),
                }
            )
            scenario_id = created["simulation_scenario"]["id"]

            selected = handlers.update_simulation_control(
                {"action": "select", "scenario_id": scenario_id}
            )
            stepped = handlers.update_simulation_control(
                {"action": "step", "scenario_id": scenario_id}
            )
            run = handlers.run_simulation_scenario({"scenario_id": scenario_id})

            self.assertEqual(selected["simulation_control"]["selected_scenario_id"], scenario_id)
            self.assertEqual(stepped["simulation_control"]["playback_state"], "stepped")
            self.assertEqual(run["simulation_run"]["scenario_id"], scenario_id)
            self.assertIn("operator_report_intake", run["simulation_run"]["actual_outputs"])
            self.assertIn("brain_reference_answer", run["simulation_run"]["actual_outputs"])
            self.assertEqual(database.count("simulation_scenarios"), 1)
            self.assertEqual(database.count("simulation_runs"), 1)
            self.assertEqual(
                database.get_document("simulation_control", "active")["selected_scenario_id"],
                scenario_id,
            )

    def test_operator_workspace_supports_local_cop_and_advisory_inbox(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))

            handlers.submit_mission_context(
                {
                    "mission_statement": "Synthetic operator mission monitors Route Alpha.",
                    "route": "Route Alpha",
                    "named_area": "Area Alpha",
                }
            )
            report = handlers.submit_operator_report(
                {
                    "reporter_id": "operator-alpha",
                    "device_id": "operator-mini-001",
                    "report_type": "hazard",
                    "summary": "Synthetic hazard observed near Route Alpha.",
                    "location": "Route Alpha",
                }
            )
            workspace = handlers.operator_workspace("operator-alpha", "operator-mini-001")["operator_workspace"]
            handlers.ask_brain_chat(
                {
                    "text": "What should I human-review before updating local route assumptions?",
                    "user_id": "operator-alpha",
                    "role": "operator",
                    "use_core_reachback": "true",
                }
            )
            brain_thread = handlers.operator_brain_thread("operator-alpha")

            self.assertEqual(workspace["reporter_id"], "operator-alpha")
            self.assertEqual(workspace["status"], "advisories_waiting")
            self.assertTrue(workspace["local_cop"]["markers"])
            self.assertEqual(workspace["advisory_inbox"][-1]["id"], report["advisory_id"])
            self.assertTrue(workspace["quick_actions"])
            self.assertEqual(database.count("operator_reports"), 1)
            self.assertEqual(database.count("cop_advisories"), 1)
            self.assertEqual(len(brain_thread["messages"]), 1)

    def test_identity_licenses_and_adapters_are_persisted_and_governed(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            service = JINXApplicationService(database=database)

            identity = service.identity_users_document()["identity"]
            session = service.issue_auth_session("systemadministrator", "full")["session"]
            service.register_identity_user(
                username="adapter-admin-alpha",
                display_name="Adapter Admin Alpha",
                roles=("system_administrator",),
                default_package="full",
            )
            license_document = service.upsert_package_license(
                package="net",
                active=False,
                authorized_users=("systemadministrator",),
                notes="Temporarily disabled for test.",
            )["license"]
            service.update_adapter_state(
                adapter_id="adapter-weather-open",
                action="activate",
                enabled=True,
            )
            service.update_adapter_state(
                adapter_id="adapter-radio-bridge",
                action="authorize",
                explicitly_authorized=True,
            )
            live_adapter = service.update_adapter_state(
                adapter_id="adapter-radio-bridge",
                action="activate",
                enabled=True,
            )["adapter"]

            self.assertGreaterEqual(len(identity["users"]), 7)
            self.assertEqual(session["package"], "full")
            self.assertFalse(service.package_license_allows("net", "net-manager-alpha"))
            self.assertEqual(license_document["package"], "net")
            self.assertEqual(live_adapter["status"], "enabled")
            self.assertTrue(live_adapter["explicitly_authorized"])
            self.assertGreaterEqual(database.count("auth_sessions"), 1)
            self.assertGreaterEqual(database.count("package_licenses"), 6)
            self.assertGreaterEqual(database.count("adapter_manifests"), 8)
            self.assertTrue(service.boundary_controls_document()["boundary_controls"]["packages"])
            self.assertTrue(service.adapter_registry_document()["adapters"])

    def test_auth_session_can_be_revoked(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            service = JINXApplicationService(database=database)

            issued = service.issue_auth_session("operator-alpha", "operator")["session"]
            revoked = service.revoke_auth_session(issued["id"])["session"]
            identity = service.identity_users_document()["identity"]

            self.assertEqual(revoked["status"], "inactive")
            self.assertIn("ended_at", revoked)
            self.assertEqual(identity["active_session_count"], 0)

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
        self.assertIn("/api/net/plans", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/net/issues", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/net/validation-runs", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/net/advisories", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/mission-context", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/review-center", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/mission-impacts", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/c5isr-scenarios", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/analysis-runs", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/explanations", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/context", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/ops-console", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/operator-loop", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/fabric", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/login", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/session", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/logout", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/admin/users", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/admin/licenses", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/admin/adapters", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/boundary-controls", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/policy-decisions", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/brain/query", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/brain/chat", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/brain/chat-messages", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/brain/explanations", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/brain/options", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/brain/checklists", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/brain/learning-proposals", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/core/module-boundaries", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/run-c5isr", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/runs", (static_root / "app.js").read_text(encoding="utf-8"))
        self.assertIn("JINX-SIM Control Center", (static_root / "sim.html").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/dashboard", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/library", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/control", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/scenarios", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/sim/run", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("role-select", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Mission Context", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Core Ops Console", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Operator Loop", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("JINX-FABRIC Monitor", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Identity / Session", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Package Licenses", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Identity Users", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Boundary Controls", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Adapter Registry", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Adapter Control", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Dead Letters", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Bounded Core Context", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("BRAIN Options", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Learning Proposals", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("BRAIN Explanations", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("BRAIN Checklists", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Policy Decisions", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Simulation Runs", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("C5ISR Review Center", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Core Analysis Runs", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("JINX-BRAIN Chat", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Brain References", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Core Conflict Packets", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("ISR Feed Display", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("JINX-NET Plan", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("NET Plans", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("NET Issues", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("NET Validation Runs", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn("NET Advisories", (static_root / "index.html").read_text(encoding="utf-8"))
        self.assertIn(".map-grid", (static_root / "styles.css").read_text(encoding="utf-8"))
        self.assertIn(".module-grid", (static_root / "styles.css").read_text(encoding="utf-8"))
        self.assertIn(".review-row", (static_root / "styles.css").read_text(encoding="utf-8"))
        self.assertIn("JINX-INTEL Fusion Desk", (static_root / "intel.html").read_text(encoding="utf-8"))
        self.assertIn("/api/intel/summaries", (static_root / "intel_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/intel/correlations", (static_root / "intel_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/intel/module-notices", (static_root / "intel_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/intel/isr-feeds", (static_root / "intel_app.js").read_text(encoding="utf-8"))
        self.assertIn("JINX-Operator Mini", (static_root / "operator.html").read_text(encoding="utf-8"))
        self.assertIn("/api/operator/workspace", (static_root / "operator_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/operator/report", (static_root / "operator_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/operator/brain-thread", (static_root / "operator_app.js").read_text(encoding="utf-8"))
        self.assertIn("Session user", (static_root / "c5isr.html").read_text(encoding="utf-8"))
        self.assertIn("Session user", (static_root / "net.html").read_text(encoding="utf-8"))
        self.assertIn("Session user", (static_root / "intel.html").read_text(encoding="utf-8"))
        self.assertIn("Session user", (static_root / "sim.html").read_text(encoding="utf-8"))
        self.assertIn("Session user", (static_root / "operator.html").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/login", (static_root / "c5isr_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/session", (static_root / "c5isr_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/logout", (static_root / "c5isr_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/login", (static_root / "net_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/session", (static_root / "net_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/logout", (static_root / "net_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/login", (static_root / "intel_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/session", (static_root / "intel_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/logout", (static_root / "intel_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/login", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/session", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/logout", (static_root / "sim_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/login", (static_root / "operator_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/session", (static_root / "operator_app.js").read_text(encoding="utf-8"))
        self.assertIn("/api/auth/logout", (static_root / "operator_app.js").read_text(encoding="utf-8"))

    def test_package_specific_frontend_surfaces_are_separated(self) -> None:
        static_root = Path("jinx/web/static")
        c5isr_html = (static_root / "c5isr.html").read_text(encoding="utf-8")
        c5isr_js = (static_root / "c5isr_app.js").read_text(encoding="utf-8")
        net_html = (static_root / "net.html").read_text(encoding="utf-8")
        net_js = (static_root / "net_app.js").read_text(encoding="utf-8")
        intel_html = (static_root / "intel.html").read_text(encoding="utf-8")
        intel_js = (static_root / "intel_app.js").read_text(encoding="utf-8")
        sim_html = (static_root / "sim.html").read_text(encoding="utf-8")
        sim_js = (static_root / "sim_app.js").read_text(encoding="utf-8")
        operator_html = (static_root / "operator.html").read_text(encoding="utf-8")
        operator_js = (static_root / "operator_app.js").read_text(encoding="utf-8")

        self.assertIn("Common Operational Picture", c5isr_html)
        self.assertIn("/api/cop", c5isr_js)
        self.assertIn("/api/operator-reports", c5isr_js)
        self.assertIn("/api/auth/login", c5isr_js)
        self.assertNotIn("/api/net", c5isr_js)
        self.assertNotIn("JINX-NET", c5isr_html + c5isr_js)
        self.assertNotIn("NET Issues", c5isr_html + c5isr_js)
        self.assertNotIn("NET Plans", c5isr_html + c5isr_js)

        self.assertIn("JINX-NET Manager", net_html)
        self.assertIn("/api/entitlements", net_js)
        self.assertIn("/api/net/plans", net_js)
        self.assertIn("/api/net/issues", net_js)
        self.assertIn("/api/auth/login", net_js)
        self.assertNotIn("/api/operator-reports", net_js)
        self.assertNotIn("/api/cop", net_js)
        self.assertNotIn("Common Operational Picture", net_html + net_js)
        self.assertNotIn("Operator Report", net_html + net_js)

        self.assertIn("JINX-INTEL Fusion Desk", intel_html)
        self.assertIn("/api/intel/summaries", intel_js)
        self.assertIn("/api/intel/correlations", intel_js)
        self.assertIn("/api/intel/module-notices", intel_js)
        self.assertIn("/api/intel/isr-feeds", intel_js)
        self.assertIn("/api/auth/login", intel_js)
        self.assertNotIn("/api/cop", intel_js)
        self.assertNotIn("/api/net", intel_js)
        self.assertNotIn("/api/operator-reports", intel_js)
        self.assertNotIn("Common Operational Picture", intel_html + intel_js)
        self.assertNotIn("Network Manager", intel_html + intel_js)

        self.assertIn("JINX-SIM Control Center", sim_html)
        self.assertIn("/api/sim/dashboard", sim_js)
        self.assertIn("/api/sim/library", sim_js)
        self.assertIn("/api/sim/control", sim_js)
        self.assertIn("/api/sim/scenarios", sim_js)
        self.assertIn("/api/sim/run", sim_js)
        self.assertIn("/api/auth/login", sim_js)
        self.assertNotIn("/api/cop", sim_js)
        self.assertNotIn("/api/net", sim_js)
        self.assertNotIn("/api/intel", sim_js)
        self.assertNotIn("/api/operator-reports", sim_js)
        self.assertNotIn("Common Operational Picture", sim_html + sim_js)
        self.assertNotIn("Network Manager", sim_html + sim_js)
        self.assertNotIn("Fusion Desk", sim_html + sim_js)

        self.assertIn("JINX-Operator Mini", operator_html)
        self.assertIn("/api/operator/workspace", operator_js)
        self.assertIn("/api/operator/report", operator_js)
        self.assertIn("/api/operator/brain-thread", operator_js)
        self.assertIn("/api/auth/login", operator_js)
        self.assertNotIn("/api/cop", operator_js)
        self.assertNotIn("/api/net", operator_js)
        self.assertNotIn("/api/intel", operator_js)
        self.assertNotIn("/api/mission-context", operator_js)
        self.assertNotIn("Common Operational Picture", operator_html + operator_js)
        self.assertNotIn("Network Manager", operator_html + operator_js)
        self.assertNotIn("Fusion Desk", operator_html + operator_js)

    def test_web_request_handler_enforces_role_permissions(self) -> None:
        handler = JINXRequestHandler.__new__(JINXRequestHandler)
        handler.headers = {"X-JINX-Role": "operator"}

        handler._require_permission("operator:read")
        handler._require_permission("operator_report:submit")
        with self.assertRaises(PermissionError):
            handler._require_permission("operator_report:review")

        handler.headers = {"X-JINX-Role": "c5isr_manager"}
        handler._require_permission("operator_report:review")
        handler._require_permission("sim:read")
        handler._require_permission("sim:inject")
        handler._require_permission("sim:run")
        handler._require_permission("ops:read")
        handler._require_permission("net:submit")

        handler.headers = {"X-JINX-Role": "network_manager"}
        handler._require_permission("net:read")
        handler._require_permission("net:submit")
        handler._require_permission("net:review")
        handler._require_permission("sim:read")

        handler.headers = {"X-JINX-Role": "simulation_operator"}
        handler._require_permission("sim:read")
        handler._require_permission("sim:inject")
        handler._require_permission("sim:run")

    def test_web_request_handler_enforces_package_entitlements(self) -> None:
        handler = JINXRequestHandler.__new__(JINXRequestHandler)

        handler.headers = {"X-JINX-Role": "c5isr_manager", "X-JINX-Package": "c5isr"}
        handler._require_permission("operator_report:submit")
        handler._require_permission("cop:read")
        with self.assertRaises(PermissionError):
            handler._require_permission("net:read")

        handler.headers = {"X-JINX-Role": "network_manager", "X-JINX-Package": "net"}
        handler._require_permission("net:read")
        handler._require_permission("net:submit")
        with self.assertRaises(PermissionError):
            handler._require_permission("operator_report:submit")
        with self.assertRaises(PermissionError):
            handler._require_permission("cop:read")

        handler.headers = {"X-JINX-Role": "intel_analyst", "X-JINX-Package": "intel"}
        handler._require_permission("isr:read")
        handler._require_permission("intel:submit")
        with self.assertRaises(PermissionError):
            handler._require_permission("cop:read")
        with self.assertRaises(PermissionError):
            handler._require_permission("net:read")

        handler.headers = {"X-JINX-Role": "simulation_operator", "X-JINX-Package": "sim"}
        handler._require_permission("sim:read")
        handler._require_permission("sim:inject")
        handler._require_permission("sim:run")
        with self.assertRaises(PermissionError):
            handler._require_permission("cop:read")
        with self.assertRaises(PermissionError):
            handler._require_permission("net:read")
        with self.assertRaises(PermissionError):
            handler._require_permission("isr:read")

        handler.headers = {"X-JINX-Role": "operator", "X-JINX-Package": "operator"}
        handler._require_permission("operator:read")
        handler._require_permission("operator_report:submit")
        handler._require_permission("brain:chat")
        with self.assertRaises(PermissionError):
            handler._require_permission("cop:read")
        with self.assertRaises(PermissionError):
            handler._require_permission("net:read")
        with self.assertRaises(PermissionError):
            handler._require_permission("isr:read")

    def test_web_request_handler_maps_package_app_routes(self) -> None:
        self.assertEqual(JINXRequestHandler._app_path("/apps/ops"), "/index.html")
        self.assertEqual(JINXRequestHandler._app_path("/ops"), "/index.html")
        self.assertEqual(JINXRequestHandler._app_path("/apps/c5isr"), "/c5isr.html")
        self.assertEqual(JINXRequestHandler._app_path("/c5isr"), "/c5isr.html")
        self.assertEqual(JINXRequestHandler._app_path("/apps/net"), "/net.html")
        self.assertEqual(JINXRequestHandler._app_path("/net"), "/net.html")
        self.assertEqual(JINXRequestHandler._app_path("/apps/intel"), "/intel.html")
        self.assertEqual(JINXRequestHandler._app_path("/intel"), "/intel.html")
        self.assertEqual(JINXRequestHandler._app_path("/apps/sim"), "/sim.html")
        self.assertEqual(JINXRequestHandler._app_path("/sim"), "/sim.html")
        self.assertEqual(JINXRequestHandler._app_path("/apps/operator"), "/operator.html")
        self.assertEqual(JINXRequestHandler._app_path("/operator"), "/operator.html")
        self.assertIsNone(JINXRequestHandler._app_path("/unknown"))

    def test_c5isr_package_redacts_net_specific_payload_details(self) -> None:
        handler = JINXRequestHandler.__new__(JINXRequestHandler)
        handler.headers = {"X-JINX-Package": "c5isr"}

        redacted = handler._redact_payload_for_package(
            {
                "summary": "JINX-NET network manager review for TDMA timeslot LOS issue.",
                "network_plan_id": "net-plan-1",
                "nested": {"net_detail": "MTDL conflict", "label": "Network issue"},
            }
        )

        self.assertNotIn("network_plan_id", redacted)
        self.assertNotIn("net_detail", redacted["nested"])
        self.assertNotIn("JINX-NET", str(redacted))
        self.assertNotIn("network manager", str(redacted))
        self.assertNotIn("TDMA", str(redacted))
        self.assertIn("communications-domain", redacted["summary"])

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

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jinx.adapters import AdapterGate, AdapterManifest
from jinx.api import JINXAPIHandlers
from jinx.app import JINXApplicationService
from jinx.common.types import DataMode, HumanCommandType, OperatorReportType, SafetyClassification
from jinx.core.config import JINXConfig
from jinx.core.identity import User
from jinx.core.identity.defaults import build_default_access_control
from jinx.core.persistence import JSONDocumentStore
from jinx.modules.operator_mini import OperatorMiniClient
from jinx.modules.sim import ScenarioReplayer, SyntheticScenarioFactory
from tests.unit.helpers import confidence, provenance


class Phase3SpineTests(TestCase):
    def test_default_access_control_grants_expected_permissions(self) -> None:
        access = build_default_access_control()
        user = User(
            username="operator.alpha",
            display_name="Operator Alpha",
            roles=frozenset({"operator"}),
        )

        access.register_user(user)

        self.assertTrue(access.may(user.id, "operator_report:submit"))
        self.assertFalse(access.may(user.id, "human_command:submit"))

        c5isr_manager = User(
            username="c5isr.manager",
            display_name="C5ISR Manager",
            roles=frozenset({"c5isr_manager"}),
        )
        access.register_user(c5isr_manager)
        self.assertTrue(access.may(c5isr_manager.id, "operator_report:review"))
        self.assertTrue(access.may(c5isr_manager.id, "sim:inject"))
        self.assertTrue(access.may(c5isr_manager.id, "sim:run"))
        self.assertTrue(access.may(c5isr_manager.id, "ops:read"))
        self.assertFalse(access.may(c5isr_manager.id, "human_command:submit"))

        commander = User(
            username="commander.alpha",
            display_name="Commander Alpha",
            roles=frozenset({"commander"}),
        )
        access.register_user(commander)
        self.assertTrue(access.may(commander.id, "human_command:submit"))
        self.assertTrue(access.may(commander.id, "operator_report:review"))

    def test_config_rejects_real_adapters_while_simulation_first(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                JINXConfig(
                    data_mode=DataMode.SYNTHETIC,
                    storage_root=Path(tmp),
                    simulation_first=True,
                    real_adapters_enabled=True,
                )

    def test_json_document_store_round_trips_documents(self) -> None:
        with TemporaryDirectory() as tmp:
            store = JSONDocumentStore(Path(tmp))
            store.save("events", "event-1", {"id": "event-1", "synthetic": True})

            self.assertEqual(store.load("events", "event-1")["synthetic"], True)
            self.assertEqual(len(store.list_collection("events")), 1)

    def test_scenario_replayer_builds_ordered_frames(self) -> None:
        scenario = SyntheticScenarioFactory().communications_conflict()

        replay = ScenarioReplayer().replay(scenario)

        self.assertEqual([frame.offset_seconds for frame in replay.frames], [0, 60])

    def test_adapter_gate_blocks_unauthorized_live_adapter(self) -> None:
        manifest = AdapterManifest(
            name="live-radio",
            permission="radio:connect",
            data_mode=DataMode.LIVE_CONTROLLED_ADAPTER,
            safety_classification=SafetyClassification.CONTROLLED_REAL_ADAPTER,
            explicitly_authorized=False,
        )

        self.assertFalse(AdapterGate().may_activate(manifest))

    def test_application_service_handles_operator_report(self) -> None:
        client = OperatorMiniClient("operator-alpha", "operator-mini-001")
        report = client.create_report(
            report_type=OperatorReportType.OBSERVATION,
            summary="Synthetic observation from edge client.",
            confidence=confidence(),
            provenance=provenance("jinx-operator-mini"),
        )

        result = JINXApplicationService().submit_operator_report(report)

        self.assertTrue(result.report_route.delivered)
        self.assertTrue(result.advisory_route.delivered)
        self.assertEqual(result.intake.event.metadata["operator_report_id"], report.id)

    def test_application_service_routes_human_command_from_operator_mini(self) -> None:
        client = OperatorMiniClient("commander-alpha", "operator-mini-001")
        command = client.create_human_command(
            command_type=HumanCommandType.HUMAN_DIRECTION,
            text="Synthetic human coordination input.",
            issuing_role="commander",
            provenance=provenance("human-ui"),
            target_module="jinx-c5isr",
        )

        result = JINXApplicationService().submit_human_command(command)

        self.assertTrue(result.delivered)

    def test_api_handlers_submit_operator_report(self) -> None:
        response = JINXAPIHandlers().submit_operator_report(
            {
                "reporter_id": "operator-alpha",
                "device_id": "operator-mini-001",
                "report_type": "observation",
                "summary": "Synthetic API report.",
                "location": "synthetic-grid-alpha",
            }
        )

        self.assertTrue(response["delivered"])
        self.assertTrue(str(response["report_id"]).startswith("op-report-"))

    def test_api_handlers_reject_prohibited_human_command(self) -> None:
        with self.assertRaises(ValueError):
            JINXAPIHandlers().submit_human_command(
                {
                    "issuing_user_id": "commander-alpha",
                    "device_id": "operator-mini-001",
                    "issuing_role": "commander",
                    "command_type": "human_direction",
                    "text": "Authorize strike on synthetic point.",
                    "target_module": "jinx-c5isr",
                }
            )

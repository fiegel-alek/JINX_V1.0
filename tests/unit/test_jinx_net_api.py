from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jinx.api import JINXAPIHandlers
from jinx.app import JINXApplicationService
from jinx.common.types import DataMode
from jinx.core.persistence import SQLiteJINXDatabase
from jinx.modules.net import LOSLink, NetworkNode, NetworkPlan, NetworkValidator, TimeslotAllocation
from jinx.modules.net.parsers import SyntheticNetworkPlanParser
from tests.unit.helpers import confidence, provenance


class JINXNETAPITests(TestCase):
    def test_network_validator_detects_plan_timing_and_los_issues(self) -> None:
        plan = NetworkPlan(
            name="Synthetic Link Plan",
            nodes=(
                NetworkNode("node-alpha", "Node Alpha", "terminal"),
                NetworkNode("node-bravo", "Node Bravo", "terminal"),
            ),
            timeslots=(
                TimeslotAllocation("slot-01", "node-alpha", "epoch-alpha"),
                TimeslotAllocation("slot-01", "node-bravo", "epoch-alpha"),
            ),
            los_links=(LOSLink("node-alpha", "node-bravo", "blocked", "Synthetic terrain mask."),),
            confidence=confidence(),
            provenance=provenance("jinx-net"),
            data_mode=DataMode.SYNTHETIC,
        )

        run, issues = NetworkValidator().validate_plan(plan)

        self.assertEqual(run.plan_id, plan.id)
        self.assertEqual({issue.issue_type for issue in issues}, {"timeslot_conflict", "los_warning"})
        self.assertTrue(all(issue.disallowed_actions for issue in issues))

    def test_synthetic_network_plan_parser_builds_plan(self) -> None:
        plan = SyntheticNetworkPlanParser().parse(
            """
            name: Synthetic Parsed Plan
            node: node-alpha, Node Alpha, terminal
            node: node-bravo, Node Bravo, terminal
            slot: slot-01, node-alpha, epoch-alpha
            slot: slot-01, node-bravo, epoch-alpha
            los: node-alpha, node-bravo, degraded, Synthetic relay assumption.
            """,
            confidence=confidence(),
            provenance=provenance("jinx-net-parser"),
        )

        self.assertEqual(plan.name, "Synthetic Parsed Plan")
        self.assertEqual(len(plan.nodes), 2)
        self.assertEqual(len(plan.timeslots), 2)
        self.assertEqual(plan.source_format, "synthetic_optasklink_stub")

    def test_network_plan_api_persists_and_routes_to_core(self) -> None:
        with TemporaryDirectory() as tmp:
            database = SQLiteJINXDatabase(Path(tmp) / "jinx.sqlite3")
            handlers = JINXAPIHandlers(JINXApplicationService(database=database))

            response = handlers.submit_network_plan(
                {
                    "name": "Synthetic NET API Plan",
                    "node_ids": "node-alpha,node-bravo,node-charlie",
                    "timeslots": "slot-01:node-alpha,slot-01:node-bravo,slot-02:node-charlie",
                    "los_links": "node-alpha>node-bravo",
                    "los_status": "degraded",
                }
            )

            self.assertGreaterEqual(response["issues"], 2)
            self.assertTrue(response["delivered_to_core"])
            self.assertGreaterEqual(response["conflicts"], 1)
            self.assertGreaterEqual(response["recommendations"], 1)
            self.assertEqual(database.count("network_plans"), 1)
            self.assertGreaterEqual(database.count("network_issues"), 2)
            self.assertEqual(database.count("network_validation_runs"), 1)
            self.assertGreaterEqual(database.count("network_advisories"), 2)
            self.assertTrue(handlers.service.policy_decisions_document()["policy_decisions"])
            self.assertGreaterEqual(database.count("policy_decisions"), 1)
            self.assertTrue(handlers.service.network_issues_document()["network_issues"])

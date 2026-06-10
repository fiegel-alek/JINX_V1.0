from unittest import TestCase

from jinx.common.types import DataMode, EventType
from jinx.modules.sim import SyntheticScenarioFactory
from jinx.modules.sim.scenarios import SimulationEvent, SimulationScenario


class SimulationTests(TestCase):
    def test_scenario_events_must_be_sorted(self) -> None:
        with self.assertRaises(ValueError):
            SimulationScenario(
                name="unsorted",
                description="Invalid unsorted scenario.",
                events=(
                    SimulationEvent(
                        name="later",
                        offset_seconds=20,
                        payload_schema="event.v1",
                        payload={"synthetic": True},
                    ),
                    SimulationEvent(
                        name="earlier",
                        offset_seconds=10,
                        payload_schema="event.v1",
                        payload={"synthetic": True},
                    ),
                ),
            )

    def test_factory_builds_communications_conflict_scenario(self) -> None:
        scenario = SyntheticScenarioFactory().communications_conflict()

        self.assertEqual(scenario.synthetic_label, "synthetic")
        self.assertEqual(len(scenario.events), 2)
        self.assertEqual(scenario.events[1].expected_effects[-1], "human review recommended")

    def test_factory_builds_domain_event_from_synthetic_data(self) -> None:
        event = SyntheticScenarioFactory().communications_loss_event()

        self.assertEqual(event.data_mode, DataMode.SYNTHETIC)
        self.assertEqual(event.event_type, EventType.CONFLICTING_REPORT)
        self.assertTrue(event.simulation_flag)

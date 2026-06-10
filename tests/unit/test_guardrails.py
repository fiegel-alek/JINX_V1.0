from unittest import TestCase

from jinx.common.types import AdvisoryLabel
from jinx.core.schemas import AdvisoryOutput
from jinx.modules.sim import SimulationScenario

from tests.unit.helpers import confidence, provenance


class GuardrailTests(TestCase):
    def test_advisory_output_requires_provenance(self) -> None:
        with self.assertRaises(ValueError):
            AdvisoryOutput(
                label=AdvisoryLabel.WARNING,
                text="Communications issue detected.",
                rationale="Two synthetic reports disagree on expected status.",
                confidence=confidence(),
                provenance_chain=(),
                required_human_review=True,
                allowed_actions=("Request human review.",),
                disallowed_actions=("Do not issue operational orders.",),
            )

    def test_advisory_output_rejects_operational_command_language(self) -> None:
        with self.assertRaises(ValueError):
            AdvisoryOutput(
                label=AdvisoryLabel.RECOMMENDATION,
                text="Command unit to change route.",
                rationale="Unsafe wording should be rejected.",
                confidence=confidence(),
                provenance_chain=(provenance(),),
                required_human_review=True,
                allowed_actions=("Request human review.",),
                disallowed_actions=("Do not issue operational orders.",),
            )

    def test_advisory_output_accepts_human_review_recommendation(self) -> None:
        output = AdvisoryOutput(
            label=AdvisoryLabel.RECOMMENDATION,
            text="Communications issue detected. Network-domain review recommended.",
            rationale="Synthetic reports conflict on expected communications availability.",
            confidence=confidence(),
            provenance_chain=(provenance(),),
            required_human_review=True,
            allowed_actions=("Request human review.", "Run a synthetic replay."),
            disallowed_actions=("Do not issue operational orders.", "Do not modify live systems."),
        )

        self.assertEqual(output.label, AdvisoryLabel.RECOMMENDATION)

    def test_simulation_scenario_must_be_synthetic(self) -> None:
        with self.assertRaises(ValueError):
            SimulationScenario(
                name="Live feed scenario",
                description="This should be rejected in Phase 0.",
                synthetic_label="live",
            )

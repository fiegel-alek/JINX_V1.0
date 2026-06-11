"""Dependency-free API-style handlers for early integration tests."""

from jinx.app import JINXApplicationService
from jinx.common.types import DataMode, HumanCommandType, OperatorReportType
from jinx.modules.operator_mini import OperatorMiniClient
from jinx.core.schemas import Location, MissionContext, MissionTask
from jinx.common.types.confidence import ConfidenceScore
from jinx.core.provenance import ProvenanceRecord
from jinx.modules.intel import IntelligenceSummary, ISRFeedSnapshot
from jinx.modules.net import LOSLink, NetworkNode, NetworkPlan, SyntheticNetworkPlanParser, TimeslotAllocation
from datetime import UTC, datetime


class JINXAPIHandlers:
    def __init__(self, service: JINXApplicationService | None = None) -> None:
        self.service = service or JINXApplicationService()

    def submit_operator_report(self, payload: dict[str, str]) -> dict[str, object]:
        client = OperatorMiniClient(
            reporter_id=payload["reporter_id"],
            device_id=payload["device_id"],
            data_mode=DataMode.SYNTHETIC,
        )
        report = client.create_report(
            report_type=OperatorReportType(payload.get("report_type", OperatorReportType.OBSERVATION.value)),
            summary=payload["summary"],
            confidence=self._synthetic_confidence(),
            provenance=self._synthetic_provenance("jinx-api.operator-mini"),
            location=Location(label=payload.get("location", "synthetic-unknown")),
        )
        result = self.service.submit_operator_report(report)
        return {
            "report_id": report.id,
            "event_id": result.intake.event.id,
            "advisory_id": result.intake.advisory.id,
            "delivered": result.report_route.delivered and result.advisory_route.delivered,
        }

    def submit_human_command(self, payload: dict[str, str]) -> dict[str, object]:
        client = OperatorMiniClient(
            reporter_id=payload["issuing_user_id"],
            device_id=payload["device_id"],
            data_mode=DataMode.SYNTHETIC,
        )
        command = client.create_human_command(
            command_type=HumanCommandType(payload.get("command_type", HumanCommandType.HUMAN_DIRECTION.value)),
            text=payload["text"],
            issuing_role=payload["issuing_role"],
            provenance=self._synthetic_provenance("jinx-api.human-command"),
            target_module=payload["target_module"],
        )
        result = self.service.submit_human_command(command)
        return {"command_id": command.id, "delivered": result.delivered}

    def review_operator_report(self, payload: dict[str, str]) -> dict[str, object]:
        report = self.service.review_operator_report(
            report_id=payload["report_id"],
            state=payload["state"],
            reviewer_id=payload["reviewer_id"],
            note=payload.get("note", ""),
        )
        return {"report": report}

    def submit_intelligence_summary(self, payload: dict[str, str]) -> dict[str, object]:
        summary = IntelligenceSummary(
            source_category=payload.get("source_category", "synthetic_isr_summary"),
            summary=payload["summary"],
            reliability=float(payload.get("reliability", "0.7")),
            confidence=self._synthetic_confidence(),
            provenance=self._synthetic_provenance("jinx-api.intel-summary"),
            data_mode=DataMode.SYNTHETIC,
            restrictions=("Synthetic or explicitly authorized summary only.",),
            related_entities=self._csv_tuple(payload.get("related_entities", "")),
            related_locations=self._csv_tuple(payload.get("related_locations", "")),
        )
        result = self.service.ingest_intelligence_summary(summary)
        return {
            "summary_id": summary.id,
            "impact_ids": [impact.id for impact in result.fusion.impacts],
            "events_generated": len(result.fusion.impacts),
            "delivered": all(route.delivered for route in result.impact_routes),
            "conflicts": len(result.core_analysis.conflicts) if result.core_analysis else 0,
            "recommendations": len(result.core_analysis.recommendations) if result.core_analysis else 0,
        }

    def submit_isr_feed_snapshot(self, payload: dict[str, str]) -> dict[str, object]:
        snapshot = ISRFeedSnapshot(
            feed_name=payload["feed_name"],
            feed_type=payload.get("feed_type", "synthetic_isr"),
            status=payload.get("status", "available"),
            coverage_area=payload.get("coverage_area", "synthetic-area"),
            summary=payload["summary"],
            confidence=self._synthetic_confidence(),
            provenance=self._synthetic_provenance("jinx-api.isr-feed"),
            data_mode=DataMode.SYNTHETIC,
            restrictions=("Synthetic ISR feed snapshot only.",),
            related_entities=self._csv_tuple(payload.get("related_entities", "")),
            related_locations=self._csv_tuple(payload.get("related_locations", "")),
        )
        result = self.service.ingest_isr_feed_snapshot(snapshot)
        return {"feed_id": snapshot.id, "delivered_to_bus": result.delivered}

    def submit_network_plan(self, payload: dict[str, str]) -> dict[str, object]:
        if payload.get("plan_text", "").strip():
            plan = SyntheticNetworkPlanParser().parse(
                payload["plan_text"],
                confidence=self._synthetic_confidence(),
                provenance=self._synthetic_provenance("jinx-api.net-plan"),
                source_format=payload.get("source_format", "synthetic_optasklink_stub"),
            )
        else:
            plan = self._network_plan_from_payload(payload)
        result = self.service.submit_network_plan(plan)
        return {
            "plan_id": plan.id,
            "validation_run_id": result.validation_run.id,
            "issue_ids": [issue.id for issue in result.issues],
            "issues": len(result.issues),
            "delivered_to_core": all(route.delivered for route in result.issue_routes),
            "conflicts": len(result.core_analysis.conflicts) if result.core_analysis else 0,
            "recommendations": len(result.core_analysis.recommendations) if result.core_analysis else 0,
        }

    def submit_mission_context(self, payload: dict[str, str]) -> dict[str, object]:
        mission = MissionContext(
            mission_statement=payload.get(
                "mission_statement",
                "Synthetic C5ISR mission context for advisory COP review.",
            ),
            commander_intent=payload.get(
                "commander_intent",
                "Maintain shared understanding while preserving human authority.",
            ),
            tasks=(
                MissionTask(
                    task_id="task-alpha",
                    title=payload.get("task_title", "Synthetic route monitoring"),
                    purpose=payload.get("task_purpose", "Preserve COP confidence for human review."),
                    assigned_to=payload.get("assigned_to", "operator-alpha"),
                    route=payload.get("route", "Route Alpha"),
                    named_area=payload.get("named_area", "Area Alpha"),
                    timeline=payload.get("timeline", "T+00 to T+60"),
                    constraints=("Synthetic data only.", "Human review required for all outputs."),
                ),
            ),
            named_areas=(payload.get("named_area", "Area Alpha"),),
            routes=(payload.get("route", "Route Alpha"),),
            timeline=(payload.get("timeline", "T+00 to T+60"),),
            constraints=("Synthetic scenario only.", "No autonomous command authority."),
            assumptions=("Operator reports and INTEL summaries are synthetic.",),
            missing_information=("Human validation status for current COP tracks.",),
            data_mode=DataMode.SYNTHETIC,
            provenance=self._synthetic_provenance("jinx-api.mission-context"),
        )
        document = self.service.set_mission_context(mission)
        return {"mission": document}

    def validate_cop_track(self, payload: dict[str, str]) -> dict[str, object]:
        track = self.service.validate_cop_track(
            entity_id=payload["entity_id"],
            reviewer_id=payload["reviewer_id"],
            note=payload.get("note", ""),
        )
        return {"track": track}

    def _network_plan_from_payload(self, payload: dict[str, str]) -> NetworkPlan:
        node_ids = self._csv_tuple(payload.get("node_ids", "node-alpha,node-bravo"))
        nodes = tuple(
            NetworkNode(node_id, node_id.replace("-", " ").title(), "terminal")
            for node_id in node_ids
        )
        timeslots = tuple(
            TimeslotAllocation(slot.strip(), node.strip(), payload.get("epoch", "epoch-alpha"))
            for slot, node in self._pairs(payload.get("timeslots", "slot-01:node-alpha,slot-01:node-bravo"))
        )
        los_links = tuple(
            LOSLink(
                pair[0],
                pair[1],
                payload.get("los_status", "degraded"),
                payload.get("los_rationale", "Synthetic terrain or relay assumption requires review."),
            )
            for pair in self._node_pairs(payload.get("los_links", "node-alpha>node-bravo"))
        )
        return NetworkPlan(
            name=payload.get("name", "Synthetic MTDL Network Plan"),
            nodes=nodes,
            timeslots=timeslots,
            los_links=los_links,
            confidence=self._synthetic_confidence(),
            provenance=self._synthetic_provenance("jinx-api.net-plan"),
            data_mode=DataMode.SYNTHETIC,
            source_format=payload.get("source_format", "synthetic_form"),
        )

    def query_brain(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.brain_query_document(
            query=payload.get("query", ""),
            tags=self._csv_tuple(payload.get("tags", "")),
        )

    def ask_brain_chat(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.ask_brain_chat(
            text=payload["text"],
            user_id=payload.get("user_id", "operator-alpha"),
            role=payload.get("role", "operator"),
            session_id=payload.get("session_id") or None,
            use_core_reachback=payload.get("use_core_reachback", "true").lower() != "false",
        )

    def run_c5isr_scenario(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.run_c5isr_scenario_pack(payload.get("scenario_id", "default"))

    def create_simulation_scenario(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.create_simulation_scenario(
            name=payload["name"],
            summary=payload["summary"],
            inject_script=payload["inject_script"],
            expected_outputs=self._csv_tuple(payload.get("expected_outputs", "")),
        )

    def update_simulation_control(self, payload: dict[str, str]) -> dict[str, object]:
        try:
            offset_seconds = int(payload.get("offset_seconds", "0"))
        except ValueError as exc:
            raise ValueError("offset_seconds must be an integer") from exc
        return self.service.update_simulation_control(
            action=payload["action"],
            scenario_id=payload.get("scenario_id", ""),
            offset_seconds=offset_seconds,
        )

    def run_simulation_scenario(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.run_simulation_scenario(payload.get("scenario_id", "default"))

    @staticmethod
    def _synthetic_confidence() -> ConfidenceScore:
        return ConfidenceScore(
            value=0.6,
            scale="0.0-1.0",
            rationale="API handler synthetic input default.",
            source_quality=0.6,
            recency_factor=0.8,
            corroboration_factor=0.2,
            contradiction_factor=0.1,
            completeness_factor=0.5,
        )

    @classmethod
    def _synthetic_provenance(cls, module: str) -> ProvenanceRecord:
        return ProvenanceRecord(
            source="jinx-api-handler",
            time_received=datetime.now(UTC),
            processed_by_module=module,
            transformations=("api_payload_normalized",),
            confidence=cls._synthetic_confidence(),
        )

    @staticmethod
    def _csv_tuple(value: str) -> tuple[str, ...]:
        return tuple(item.strip() for item in value.split(",") if item.strip())

    @staticmethod
    def _pairs(value: str) -> tuple[tuple[str, str], ...]:
        pairs = []
        for item in value.split(","):
            left, separator, right = item.partition(":")
            if separator and left.strip() and right.strip():
                pairs.append((left.strip(), right.strip()))
        return tuple(pairs)

    @staticmethod
    def _node_pairs(value: str) -> tuple[tuple[str, str], ...]:
        pairs = []
        for item in value.split(","):
            left, separator, right = item.partition(">")
            if separator and left.strip() and right.strip():
                pairs.append((left.strip(), right.strip()))
        return tuple(pairs)

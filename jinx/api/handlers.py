"""Dependency-free API-style handlers for early integration tests."""

from jinx.app import JINXApplicationService
from jinx.common.types import DataMode, HumanCommandType, OperatorReportType
from jinx.modules.operator_mini import OperatorMiniClient
from jinx.core.schemas import Location, MissionContext, MissionTask
from jinx.common.types.confidence import ConfidenceScore
from jinx.core.provenance import ProvenanceRecord
from jinx.modules.intel import IntelligenceSummary, ISRFeedSnapshot
from jinx.modules.integrator import SyntheticMessageFamilyParser
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
            "advisory_summary": result.intake.advisory.summary,
            "status": "queued_for_human_review",
            "acknowledged_at": report.timestamp.isoformat(),
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

    def submit_integrator_message(self, payload: dict[str, str]) -> dict[str, object]:
        data_mode = DataMode(payload.get("data_mode", DataMode.SYNTHETIC.value))
        parse_result = SyntheticMessageFamilyParser().parse(
            message_family=payload.get("message_family", "vmf"),
            text=payload["raw_text"],
            confidence=self._synthetic_confidence(),
            provenance=self._synthetic_provenance("jinx-api.integrator"),
            data_mode=data_mode,
        )
        result = self.service.submit_integrator_message(parse_result)
        return {
            "message_id": parse_result.intake.id,
            "parse_run_id": f"integrator-parse-{parse_result.intake.id}",
            "route_count": len(result.routes),
            "delivered_routes": sum(1 for route in result.routes if route.delivered),
            "statuses": [route.status for route in result.routes],
            "validation_notes": list(parse_result.validation_notes),
            "filter_profile": parse_result.intake.filter_profile,
            "route_targets": list(parse_result.intake.route_targets),
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

    def operator_workspace(self, reporter_id: str, device_id: str = "") -> dict[str, object]:
        return self.service.operator_workspace_document(reporter_id=reporter_id, device_id=device_id)

    def operator_brain_thread(self, reporter_id: str) -> dict[str, object]:
        return self.service.operator_brain_thread_document(reporter_id)

    def identity_users(self) -> dict[str, object]:
        return self.service.identity_users_document()

    def register_identity_user(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.register_identity_user(
            username=payload["username"],
            display_name=payload["display_name"],
            roles=self._csv_tuple(payload["roles"]),
            default_package=payload.get("default_package", "operator"),
            reporter_id=payload.get("reporter_id", ""),
            device_id=payload.get("device_id", ""),
        )

    def login_auth_session(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.issue_auth_session(
            username=payload["username"],
            package=payload.get("package", "full"),
            reporter_id=payload.get("reporter_id", ""),
            device_id=payload.get("device_id", ""),
        )

    def auth_session(self, session_id: str = "") -> dict[str, object]:
        return self.service.auth_session_document(session_id)

    def package_licenses(self) -> dict[str, object]:
        return self.service.license_state_document()

    def upsert_package_license(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.upsert_package_license(
            package=payload["package"],
            active=payload.get("active", "true").lower() == "true",
            authorized_users=self._csv_tuple(payload.get("authorized_users", "")),
            notes=payload.get("notes", ""),
            controlled_real_adapters_enabled=payload.get(
                "controlled_real_adapters_enabled", "false"
            ).lower()
            == "true",
        )

    def boundary_controls(self) -> dict[str, object]:
        return self.service.boundary_controls_document()

    def evidence_packs(self) -> dict[str, object]:
        return self.service.evidence_packs_document()

    def review_tasks(self, payload: dict[str, str] | None = None) -> dict[str, object]:
        payload = payload or {}
        return self.service.review_tasks_document(
            package_scope=payload.get("package_scope", ""),
            state=payload.get("state", ""),
            assigned_role=payload.get("assigned_role", ""),
            assigned_reviewer=payload.get("assigned_reviewer", ""),
            escalation_state=payload.get("escalation_state", ""),
            source_kind=payload.get("source_kind", ""),
        )

    def update_review_task(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.update_review_task(
            task_id=payload["task_id"],
            state=payload.get("state", ""),
            reviewer_id=payload["reviewer_id"],
            note=payload.get("note", ""),
            remember=payload.get("remember", "false").lower() == "true",
            assigned_role=payload.get("assigned_role", ""),
            assigned_reviewer=payload.get("assigned_reviewer", ""),
            escalation_state=payload.get("escalation_state", ""),
            priority=payload.get("priority", ""),
            due_label=payload.get("due_label", ""),
        )

    def memory(self) -> dict[str, object]:
        return self.service.memory_compartments_document()

    def write_memory(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.write_memory_record(
            compartment=payload["compartment"],
            package_scope=payload.get("package_scope", "full"),
            title=payload["title"],
            summary=payload["summary"],
            tags=self._csv_tuple(payload.get("tags", "")),
            source_kind=payload.get("source_kind", "manual_memory"),
            source_id=payload.get("source_id", ""),
            created_by=payload.get("created_by", "systemadministrator"),
            provenance_refs=self._csv_tuple(payload.get("provenance_refs", "")),
            review_state=payload.get("review_state", "captured"),
        )

    def recall(self, payload: dict[str, str]) -> dict[str, object]:
        limit_raw = payload.get("limit", "40")
        try:
            limit = int(limit_raw)
        except ValueError as exc:
            raise ValueError("limit must be an integer") from exc
        return self.service.recall_document(
            query=payload.get("query", ""),
            package_scope=payload.get("package_scope", ""),
            kind=payload.get("kind", ""),
            state=payload.get("state", ""),
            assigned_role=payload.get("assigned_role", ""),
            limit=limit,
        )

    def doctrine_library(self) -> dict[str, object]:
        return self.service.doctrine_library_document()

    def register_doctrine(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.register_doctrine_record(
            title=payload["title"],
            scope=payload.get("scope", "lesson_learned"),
            summary=payload["summary"],
            source=payload.get("source", "manual_doctrine_entry"),
            applicability=self._csv_tuple(payload.get("applicability", "")),
            restrictions=self._csv_tuple(payload.get("restrictions", "")),
            tags=self._csv_tuple(payload.get("tags", "")),
        )

    def promote_learning_proposal(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.promote_learning_proposal(
            proposal_id=payload["proposal_id"],
            title=payload.get("title", ""),
            scope=payload.get("scope", "lesson_learned"),
            source=payload.get("source", ""),
            applicability=self._csv_tuple(payload.get("applicability", "")),
            restrictions=self._csv_tuple(payload.get("restrictions", "")),
            tags=self._csv_tuple(payload.get("tags", "")),
            reviewer_id=payload.get("reviewer_id", ""),
            note=payload.get("note", ""),
        )

    def adapters(self) -> dict[str, object]:
        return self.service.adapter_registry_document()

    def update_adapter(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.update_adapter_state(
            adapter_id=payload["adapter_id"],
            action=payload["action"],
            explicitly_authorized=payload.get("explicitly_authorized", "").lower() == "true"
            if "explicitly_authorized" in payload
            else None,
            enabled=payload.get("enabled", "").lower() == "true" if "enabled" in payload else None,
            data_mode=payload.get("data_mode", ""),
        )

    def adapter_runs(self) -> dict[str, object]:
        return self.service.adapter_runs_document()

    def execute_adapter(self, payload: dict[str, str]) -> dict[str, object]:
        return self.service.execute_adapter(
            adapter_id=payload["adapter_id"],
            initiated_by=payload.get("initiated_by", "systemadministrator"),
            summary=payload.get("summary", ""),
        )

    def audit_replay(self) -> dict[str, object]:
        return self.service.audit_replay_document()

    def create_audit_replay(self, payload: dict[str, str]) -> dict[str, object]:
        limit_raw = payload.get("limit", "12")
        try:
            limit = int(limit_raw)
        except ValueError as exc:
            raise ValueError("limit must be an integer") from exc
        return self.service.create_audit_replay(
            focus_id=payload.get("focus_id", ""),
            limit=limit,
            package_scope=payload.get("package_scope", ""),
            source_kind=payload.get("source_kind", ""),
            query=payload.get("query", ""),
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

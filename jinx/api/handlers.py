"""Dependency-free API-style handlers for early integration tests."""

from jinx.app import JINXApplicationService
from jinx.common.types import DataMode, HumanCommandType, OperatorReportType
from jinx.modules.operator_mini import OperatorMiniClient
from jinx.core.schemas import Location, MissionContext, MissionTask
from jinx.common.types.confidence import ConfidenceScore
from jinx.core.provenance import ProvenanceRecord
from jinx.modules.intel import IntelligenceSummary, ISRFeedSnapshot
from jinx.modules.integrator import (
    IntegratorTopologyDesign,
    IntegratorTopologyLink,
    IntegratorTopologyNode,
    SyntheticMessageFamilyParser,
)
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

    def submit_integrator_network_design(self, payload: dict[str, str]) -> dict[str, object]:
        if payload.get("plan_text", "").strip():
            plan = SyntheticNetworkPlanParser().parse(
                payload["plan_text"],
                confidence=self._synthetic_confidence(),
                provenance=self._synthetic_provenance("jinx-api.integrator-optasklink"),
                source_format=payload.get("source_format", "integrator_optasklink_stub"),
            )
        else:
            plan = self._network_plan_from_payload(payload)
        result = self.service.submit_network_plan(plan)
        design = self.service.save_integrator_network_design(plan, result.validation_run, result.issues)
        return {
            "design_id": design["id"],
            "plan_id": plan.id,
            "validation_run_id": result.validation_run.id,
            "issue_ids": [issue.id for issue in result.issues],
            "issues": len(result.issues),
            "nodes": len(plan.nodes),
            "timeslots": len(plan.timeslots),
            "links": len(plan.los_links),
            "delivered_to_core": all(route.delivered for route in result.issue_routes),
        }

    def submit_integrator_architecture_design(self, payload: dict[str, str]) -> dict[str, object]:
        include_modules = self._csv_tuple(payload.get("modules", "jinx-c5isr,jinx-net,jinx-intel,jinx-sim"))
        design = self.service.integrator_topologies.build_jinx_architecture(
            name=payload.get("name", "JINX Package Architecture"),
            summary=payload.get(
                "summary",
                "Simulation-first package architecture showing bounded JINX internal connections.",
            ),
            modules=tuple(module if module.startswith("jinx-") else f"jinx-{module}" for module in include_modules),
            include_operator_mini=payload.get("include_operator_mini", "true").lower() != "false",
        )
        document = self.service.save_integrator_architecture_design(design)
        return {
            "design_id": document["id"],
            "design_kind": document["design_kind"],
            "nodes": len(document["nodes"]),
            "links": len(document["links"]),
            "summary": document["summary"],
        }

    def revise_integrator_network_design(self, payload: dict[str, str]) -> dict[str, object]:
        existing = self.service.integrator_network_designs_document()["integrator_network_designs"]
        design_id = payload["design_id"]
        current = next((record for record in existing if record.get("id") == design_id), None)
        if current is None:
            raise ValueError("integrator network design not found")

        plan = self._network_plan_from_revision_payload(payload, current)
        result = self.service.submit_network_plan(plan)
        node_overrides = self._network_node_overrides_from_text(payload.get("nodes_text", ""))
        summary = payload.get("summary", current.get("summary", "")).strip() or current.get("summary", "")
        name = payload.get("name", current.get("name", "")).strip() or current.get("name", "")
        document = self.service.save_integrator_network_design(
            plan,
            result.validation_run,
            result.issues,
            design_id=design_id,
            name_override=name,
            summary_override=summary,
            node_overrides=node_overrides,
        )
        return {
            "design_id": document["id"],
            "plan_id": plan.id,
            "validation_run_id": result.validation_run.id,
            "issue_ids": [issue.id for issue in result.issues],
            "issues": len(result.issues),
            "nodes": len(document["nodes"]),
            "links": len(document["links"]),
        }

    def revise_integrator_architecture_design(self, payload: dict[str, str]) -> dict[str, object]:
        design_id = payload["design_id"]
        nodes = self._architecture_nodes_from_text(payload["nodes_text"])
        links = self._architecture_links_from_text(payload["links_text"])
        design = IntegratorTopologyDesign(
            name=payload.get("name", "JINX Package Architecture"),
            summary=payload.get(
                "summary",
                "Simulation-first package architecture showing bounded internal JINX connections.",
            ),
            design_kind="jinx_architecture",
            nodes=nodes,
            links=links,
            source_reference=payload.get("source_reference", "integrator-architecture-editor"),
        )
        document = self.service.save_integrator_architecture_design(design, design_id=design_id)
        return {
            "design_id": document["id"],
            "design_kind": document["design_kind"],
            "nodes": len(document["nodes"]),
            "links": len(document["links"]),
            "summary": document["summary"],
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

    def _network_plan_from_revision_payload(self, payload: dict[str, str], current: dict[str, object]) -> NetworkPlan:
        nodes = self._network_nodes_from_text(payload["nodes_text"])
        timeslots = self._network_timeslots_from_text(payload["timeslots_text"])
        los_links = self._network_los_from_text(payload["los_links_text"])
        return NetworkPlan(
            name=payload.get("name", str(current.get("name", "Synthetic MTDL Network Plan"))),
            nodes=nodes,
            timeslots=timeslots,
            los_links=los_links,
            confidence=self._synthetic_confidence(),
            provenance=self._synthetic_provenance("jinx-api.integrator-network-revision"),
            data_mode=DataMode.SYNTHETIC,
            source_format=str(current.get("source_format", "integrator_optasklink_stub")),
        )

    def _network_nodes_from_text(self, text: str) -> tuple[NetworkNode, ...]:
        nodes: list[NetworkNode] = []
        for line in self._lines(text):
            node_id, label, node_type, *_ = self._pipe_fields(line, 3)
            nodes.append(NetworkNode(node_id, label, node_type))
        if not nodes:
            raise ValueError("network design revision requires node lines")
        return tuple(nodes)

    def _network_node_overrides_from_text(self, text: str) -> dict[str, dict[str, object]]:
        overrides: dict[str, dict[str, object]] = {}
        for line in self._lines(text):
            node_id, label, node_type, x, y, *rest = self._pipe_fields(line, 5)
            status = rest[0] if len(rest) >= 1 else "planned"
            detail = rest[1] if len(rest) >= 2 else f"{node_type} node from edited design."
            overrides[node_id] = {
                "label": label,
                "x": float(x),
                "y": float(y),
                "status": status,
                "detail": detail,
            }
        return overrides

    def _network_timeslots_from_text(self, text: str) -> tuple[TimeslotAllocation, ...]:
        rows: list[TimeslotAllocation] = []
        for line in self._lines(text):
            slot_id, node_id, epoch, *rest = self._pipe_fields(line, 3)
            purpose = rest[0] if rest else "synthetic_mtdl"
            rows.append(TimeslotAllocation(slot_id, node_id, epoch, purpose))
        return tuple(rows)

    def _network_los_from_text(self, text: str) -> tuple[LOSLink, ...]:
        rows: list[LOSLink] = []
        for line in self._lines(text):
            from_node, to_node, status, rationale = self._pipe_fields(line, 4)
            rows.append(LOSLink(from_node, to_node, status, rationale))
        return tuple(rows)

    def _architecture_nodes_from_text(self, text: str) -> tuple[IntegratorTopologyNode, ...]:
        nodes: list[IntegratorTopologyNode] = []
        for line in self._lines(text):
            node_id, label, node_type, domain, x, y, *rest = self._pipe_fields(line, 6)
            status = rest[0] if len(rest) >= 1 else "planned"
            detail = rest[1] if len(rest) >= 2 else ""
            nodes.append(
                IntegratorTopologyNode(
                    id=node_id,
                    label=label,
                    node_type=node_type,
                    domain=domain,
                    x=float(x),
                    y=float(y),
                    status=status,
                    detail=detail,
                )
            )
        if not nodes:
            raise ValueError("architecture revision requires node lines")
        return tuple(nodes)

    def _architecture_links_from_text(self, text: str) -> tuple[IntegratorTopologyLink, ...]:
        links: list[IntegratorTopologyLink] = []
        for index, line in enumerate(self._lines(text), start=1):
            source, target, link_type, status, payloads_text, summary = self._pipe_fields(line, 6)
            payloads = tuple(item.strip() for item in payloads_text.split(",") if item.strip())
            links.append(
                IntegratorTopologyLink(
                    id=f"integrator-architecture-link-{index}",
                    source=source,
                    target=target,
                    link_type=link_type,
                    status=status,
                    summary=summary,
                    payloads=payloads,
                )
            )
        if not links:
            raise ValueError("architecture revision requires link lines")
        return tuple(links)

    @staticmethod
    def _lines(text: str) -> tuple[str, ...]:
        return tuple(line.strip() for line in text.splitlines() if line.strip())

    @staticmethod
    def _pipe_fields(text: str, minimum: int) -> list[str]:
        parts = [part.strip() for part in text.split("|")]
        if len(parts) < minimum or any(not part for part in parts[:minimum]):
            raise ValueError(f"expected at least {minimum} pipe-delimited fields")
        return parts

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

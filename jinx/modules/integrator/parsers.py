"""Synthetic message-family parser stubs for JINX-Integrator."""

from jinx.common.types import ConfidenceScore, DataMode
from jinx.core.provenance import ProvenanceRecord
from jinx.modules.net.models import NetworkIssue, NetworkPlan, NetworkValidationRun
from jinx.modules.integrator.models import (
    IntegratorIntakeMessage,
    IntegratorParseResult,
    IntegratorTopologyDesign,
    IntegratorTopologyLink,
    IntegratorTopologyNode,
    MessageFilterProfile,
)

PROFILE_BY_FAMILY = {
    "vmf": MessageFilterProfile(
        family="vmf",
        route_targets=("jinx-core", "jinx-c5isr"),
        required_fields=("message_type", "originator", "recipient", "summary"),
        summary="VMF intake is normalized for C5ISR/Core review without preserving command authority.",
        filter_actions=(
            "Preserve provenance and message-family label.",
            "Normalize message content into bounded JINX intake fields.",
            "Route only to licensed internal review modules.",
        ),
        restrictions=(
            "Synthetic or explicitly authorized message content only.",
            "No operational command execution or downstream tasking.",
        ),
    ),
    "k-series": MessageFilterProfile(
        family="k-series",
        route_targets=("jinx-core", "jinx-net"),
        required_fields=("message_type", "originator", "recipient", "summary"),
        summary="K-series intake is filtered toward communications and network review lanes.",
        filter_actions=(
            "Preserve message-family identity for traceability.",
            "Filter network-domain details into bounded advisory fields.",
            "Route only to licensed NET/Core review paths.",
        ),
        restrictions=(
            "Synthetic or explicitly authorized message content only.",
            "No live network control, retuning, or physical system changes.",
        ),
    ),
    "j-series": MessageFilterProfile(
        family="j-series",
        route_targets=("jinx-core", "jinx-net", "jinx-c5isr"),
        required_fields=("message_type", "originator", "recipient", "summary"),
        summary="J-series intake is normalized for review across communications and operational picture lanes.",
        filter_actions=(
            "Preserve message-family identity for review and replay.",
            "Bound timing and communications fields before routing.",
            "Route only to licensed internal modules through FABRIC.",
        ),
        restrictions=(
            "Synthetic or explicitly authorized message content only.",
            "No targeting, no command execution, and no autonomous retasking.",
        ),
    ),
    "usmtf": MessageFilterProfile(
        family="usmtf",
        route_targets=("jinx-core", "jinx-c5isr", "jinx-intel"),
        required_fields=("message_type", "originator", "recipient", "summary"),
        summary="USMTF intake is reduced to bounded review context for human analysis and audit.",
        filter_actions=(
            "Preserve message-family identity and precedence fields.",
            "Strip message content into bounded review metadata.",
            "Route only to licensed review modules with provenance intact.",
        ),
        restrictions=(
            "Synthetic or explicitly authorized message content only.",
            "No tasking conversion, no downstream command authority, and no hidden routing.",
        ),
    ),
}

ALLOWED_ROUTE_TARGETS = frozenset({"jinx-core", "jinx-c5isr", "jinx-net", "jinx-intel"})

JINX_LAYOUT = {
    "jinx-operator-mini": (0.08, 0.68),
    "jinx-c5isr": (0.27, 0.58),
    "jinx-integrator": (0.27, 0.20),
    "jinx-net": (0.49, 0.18),
    "jinx-intel": (0.49, 0.78),
    "jinx-bus": (0.55, 0.50),
    "jinx-core": (0.74, 0.42),
    "jinx-sim": (0.76, 0.78),
    "jinx-brain": (0.90, 0.22),
}


class SyntheticMessageFamilyParser:
    def parse(
        self,
        message_family: str,
        text: str,
        confidence: ConfidenceScore,
        provenance: ProvenanceRecord,
        data_mode: DataMode = DataMode.SYNTHETIC,
    ) -> IntegratorParseResult:
        family = message_family.strip().lower()
        if family not in PROFILE_BY_FAMILY:
            raise ValueError("unsupported message family")
        if not text.strip():
            raise ValueError("integrator message text is required")

        profile = PROFILE_BY_FAMILY[family]
        parsed: dict[str, str] = {}
        extracted_fields: dict[str, str] = {}
        validation_notes: list[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition(":")
            if not separator:
                validation_notes.append(f"ignored unstructured line: {line[:40]}")
                continue
            normalized_key = key.strip().lower().replace(" ", "_")
            normalized_value = value.strip()
            if not normalized_value:
                validation_notes.append(f"blank value ignored for {normalized_key}")
                continue
            if normalized_key in {
                "message_type",
                "originator",
                "recipient",
                "summary",
                "transport",
                "precedence",
                "route_targets",
                "network_scope",
                "tags",
            }:
                parsed[normalized_key] = normalized_value
            else:
                extracted_fields[normalized_key] = normalized_value

        missing = [field for field in profile.required_fields if field not in parsed]
        if missing:
            raise ValueError(f"integrator message missing required fields: {', '.join(missing)}")

        route_targets = tuple(
            self._normalize_route_target(item.strip())
            for item in parsed.get("route_targets", ",".join(profile.route_targets)).split(",")
            if item.strip()
        )
        invalid_targets = [target for target in route_targets if target not in ALLOWED_ROUTE_TARGETS]
        if invalid_targets:
            raise ValueError(f"unsupported internal route targets: {', '.join(invalid_targets)}")
        tags = tuple(item.strip() for item in parsed.get("tags", family).split(",") if item.strip())

        lowered_text = text.lower()
        if any(term in lowered_text for term in ("fire mission", "targeting", "retask", "retasking")):
            validation_notes.append(
                "message contains command or tasking language; JINX-Integrator preserved it as review-only intake."
            )
        if data_mode == DataMode.AUTHORIZED:
            validation_notes.append("authorized mode selected; adapter and license review remain required.")
        else:
            validation_notes.append("synthetic shadow-mode intake preserved for replay and testing.")

        intake = IntegratorIntakeMessage(
            message_family=family,
            message_type=parsed["message_type"],
            originator=parsed["originator"],
            recipient=parsed["recipient"],
            summary=parsed["summary"],
            raw_text=text,
            transport=parsed.get("transport", "fabric-shadow"),
            precedence=parsed.get("precedence", "routine"),
            confidence=confidence,
            provenance=provenance,
            data_mode=data_mode,
            restrictions=profile.restrictions,
            route_targets=route_targets or profile.route_targets,
            filter_profile=f"{family}-bounded-intake",
            network_scope=parsed.get("network_scope", "fabric-shadow"),
            tags=tags,
            simulation_flag=data_mode != DataMode.AUTHORIZED,
        )
        normalized_payload = {
            "id": intake.id,
            "message_family": intake.message_family,
            "message_type": intake.message_type,
            "originator": intake.originator,
            "recipient": intake.recipient,
            "summary": intake.summary,
            "transport": intake.transport,
            "precedence": intake.precedence,
            "network_scope": intake.network_scope,
            "filter_profile": intake.filter_profile,
            "route_targets": list(intake.route_targets),
            "tags": list(intake.tags),
            "restrictions": list(intake.restrictions),
            "extracted_fields": dict(extracted_fields),
            "human_review_required": True,
            "authority_state": "observed_external_message_only",
        }
        return IntegratorParseResult(
            intake=intake,
            normalized_payload=normalized_payload,
            extracted_fields=extracted_fields,
            validation_notes=tuple(validation_notes),
            filter_actions=profile.filter_actions,
        )

    @staticmethod
    def profiles_document() -> dict[str, object]:
        return {
            "message_families": [
                {
                    "family": profile.family,
                    "route_targets": list(profile.route_targets),
                    "required_fields": list(profile.required_fields),
                    "summary": profile.summary,
                    "filter_actions": list(profile.filter_actions),
                    "restrictions": list(profile.restrictions),
                }
                for profile in PROFILE_BY_FAMILY.values()
            ]
        }

    @staticmethod
    def _normalize_route_target(value: str) -> str:
        target = value.lower()
        if target.startswith("jinx-"):
            return target
        return f"jinx-{target}"


class IntegratorTopologyDesigner:
    def build_jinx_architecture(
        self,
        name: str,
        summary: str,
        modules: tuple[str, ...],
        include_operator_mini: bool = True,
    ) -> IntegratorTopologyDesign:
        selected = {"jinx-core", "jinx-brain", "jinx-bus", "jinx-integrator", *modules}
        if include_operator_mini:
            selected.add("jinx-operator-mini")

        labels = {
            "jinx-core": ("JINX-Core", "core"),
            "jinx-brain": ("JINX-BRAIN", "brain"),
            "jinx-bus": ("JINX-BUS / FABRIC", "bus"),
            "jinx-integrator": ("JINX-Integrator", "integrator"),
            "jinx-c5isr": ("JINX-C5ISR", "c5isr"),
            "jinx-net": ("JINX-NET", "net"),
            "jinx-intel": ("JINX-INTEL", "intel"),
            "jinx-sim": ("JINX-SIM", "sim"),
            "jinx-operator-mini": ("JINX-Operator Mini", "operator"),
        }
        details = {
            "jinx-core": "Advisory processing, policy, provenance, and audit center.",
            "jinx-brain": "Doctrine, SOP, and reachback reference layer.",
            "jinx-bus": "Bounded internal routing and package enforcement.",
            "jinx-integrator": "Message-family intake, normalization, and filter control.",
            "jinx-c5isr": "COP, operator intake, and mission review surface.",
            "jinx-net": "Synthetic tactical data link and timing review lane.",
            "jinx-intel": "Synthetic or authorized context fusion lane.",
            "jinx-sim": "Scenario replay and shadow-mode validation lane.",
            "jinx-operator-mini": "Field-facing report and advisory edge client.",
        }
        nodes = tuple(
            IntegratorTopologyNode(
                id=module,
                label=labels[module][0],
                node_type=labels[module][1],
                domain="jinx",
                x=JINX_LAYOUT[module][0],
                y=JINX_LAYOUT[module][1],
                status="simulation_only",
                detail=details[module],
            )
            for module in labels
            if module in selected
        )

        edge_specs = (
            ("jinx-integrator", "jinx-bus", "message_flow", "bounded", "Integrator releases normalized packets into FABRIC.", ("message_intake.v1",)),
            ("jinx-bus", "jinx-core", "policy_flow", "bounded", "FABRIC routes approved packets into CORE policy and analysis.", ("policy_decision.v1",)),
            ("jinx-core", "jinx-brain", "reachback", "bounded", "CORE asks BRAIN for doctrine and SOP references.", ("doctrine_reference.v1",)),
            ("jinx-c5isr", "jinx-bus", "cop_flow", "bounded", "C5ISR contributes COP and operator-review outputs through FABRIC.", ("event.v1", "cop_state.v1")),
            ("jinx-net", "jinx-bus", "network_flow", "bounded", "NET contributes validated timing and LOS review outputs through FABRIC.", ("network_issue.v1",)),
            ("jinx-intel", "jinx-bus", "intel_flow", "bounded", "INTEL contributes bounded context and ISR-derived notices through FABRIC.", ("intel_impact.v1", "isr_feed.v1")),
            ("jinx-sim", "jinx-bus", "simulation_flow", "bounded", "SIM injects replay and scenario outputs through FABRIC.", ("simulation_result",)),
            ("jinx-operator-mini", "jinx-c5isr", "edge_report", "bounded", "Operator Mini forwards human reports into the C5ISR intake lane.", ("operator_report.v1",)),
        )
        links = tuple(
            IntegratorTopologyLink(
                id=f"{source}-{target}",
                source=source,
                target=target,
                link_type=link_type,
                status=status,
                summary=summary_text,
                payloads=payloads,
            )
            for source, target, link_type, status, summary_text, payloads in edge_specs
            if source in selected and target in selected
        )

        return IntegratorTopologyDesign(
            name=name,
            summary=summary,
            design_kind="jinx_architecture",
            nodes=nodes,
            links=links,
        )

    def build_optasklink_network(
        self,
        plan: NetworkPlan,
        validation_run: NetworkValidationRun,
        issues: tuple[NetworkIssue, ...],
    ) -> IntegratorTopologyDesign:
        node_count = len(plan.nodes)
        nodes = tuple(
            IntegratorTopologyNode(
                id=node.id,
                label=node.label,
                node_type=node.node_type,
                domain="network",
                x=0.16 + (0.68 / max(node_count - 1, 1)) * index if node_count > 1 else 0.50,
                y=0.32 if index % 2 == 0 else 0.68,
                status="review_required" if any(node.id in issue.affected_nodes for issue in issues) else "planned",
                detail=f"{node.node_type} node from {plan.source_format}.",
            )
            for index, node in enumerate(plan.nodes)
        )
        timeslot_by_node: dict[str, list[str]] = {}
        for allocation in plan.timeslots:
            timeslot_by_node.setdefault(allocation.node_id, []).append(f"{allocation.slot_id}/{allocation.epoch}")

        los_links = [
            IntegratorTopologyLink(
                id=f"{plan.id}-los-{index}",
                source=link.from_node,
                target=link.to_node,
                link_type="los_path",
                status=link.status,
                summary=link.rationale,
                payloads=tuple(timeslot_by_node.get(link.from_node, ()) + timeslot_by_node.get(link.to_node, ())),
            )
            for index, link in enumerate(plan.los_links)
        ]
        slot_links = [
            IntegratorTopologyLink(
                id=f"{plan.id}-slot-{index}",
                source=allocation.node_id,
                target=allocation.node_id,
                link_type="timeslot_allocation",
                status="allocated",
                summary=f"{allocation.slot_id} in {allocation.epoch} assigned to {allocation.node_id}.",
                payloads=(allocation.purpose,),
            )
            for index, allocation in enumerate(plan.timeslots)
        ]
        summary = (
            f"Synthetic OPTASKLINK-style network design with {len(plan.nodes)} nodes, "
            f"{len(plan.timeslots)} timeslot allocations, and {len(issues)} review issue(s)."
        )
        return IntegratorTopologyDesign(
            name=plan.name,
            summary=summary,
            design_kind="optasklink_network",
            nodes=nodes,
            links=tuple([*los_links, *slot_links]),
            source_reference=validation_run.id,
        )

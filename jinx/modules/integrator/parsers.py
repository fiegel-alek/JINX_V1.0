"""Synthetic message-family parser stubs for JINX-Integrator."""

from jinx.common.types import ConfidenceScore, DataMode
from jinx.core.provenance import ProvenanceRecord
from jinx.modules.integrator.models import (
    IntegratorIntakeMessage,
    IntegratorParseResult,
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

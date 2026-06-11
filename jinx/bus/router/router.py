"""JINX-BUS policy-enforced message router."""

from dataclasses import dataclass, replace
from typing import Any

from jinx.boundary.entitlement import EntitlementBoundary
from jinx.bus.messages import FabricMessage
from jinx.common.types.enums import AuditEventType
from jinx.core.audit import AuditLog, AuditRecord
from jinx.core.policy import PolicyDecision, PolicyEngine


@dataclass(frozen=True, slots=True)
class BoundaryRoutingRule:
    source_module: str
    destination_module: str
    payload_schema: str
    allowed_fields: frozenset[str]
    abstract_replacements: dict[str, object] | None = None

    def matches(self, message: FabricMessage) -> bool:
        return (
            self.source_module == message.source_module
            and self.destination_module == message.destination
            and self.payload_schema == message.payload_schema
        )


@dataclass(frozen=True, slots=True)
class RouteResult:
    delivered: bool
    message: FabricMessage
    decision: PolicyDecision
    status: str = "delivered"
    redacted_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FabricRouteRecord:
    message: FabricMessage
    status: str
    decision: PolicyDecision
    redacted_fields: tuple[str, ...] = ()

    def to_document(self) -> dict[str, Any]:
        return {
            "id": self.message.id,
            "message_id": self.message.id,
            "topic": self.message.topic,
            "timestamp": self.message.timestamp.isoformat(),
            "source_module": self.message.source_module,
            "destination": self.message.destination,
            "payload_schema": self.message.payload_schema,
            "schema_version": self.message.schema_version,
            "sensitivity_label": self.message.sensitivity_label,
            "license_scope": self.message.license_scope,
            "provenance_ref": self.message.provenance_ref,
            "data_mode": self.message.data_mode.value,
            "simulation_flag": self.message.simulation_flag,
            "retry_count": self.message.retry_count,
            "confidence": self.message.confidence.value if self.message.confidence else None,
            "status": self.status,
            "delivered": self.status in {"delivered", "redacted"},
            "policy_allowed": self.decision.allowed,
            "policy_reason": self.decision.reason,
            "policy_timestamp": self.decision.timestamp.isoformat(),
            "redacted_fields": list(self.redacted_fields),
            "payload_keys": sorted(str(key) for key in self.message.payload.keys()),
            "payload_preview": self._payload_preview(),
        }

    def _payload_preview(self) -> dict[str, Any]:
        preview: dict[str, Any] = {}
        for key, value in list(self.message.payload.items())[:8]:
            if isinstance(value, str | int | float | bool) or value is None:
                preview[str(key)] = value
            elif isinstance(value, tuple | list):
                preview[str(key)] = list(value)[:6]
            else:
                preview[str(key)] = str(value)
        return preview


class MessageRouter:
    def __init__(
        self,
        policy_engine: PolicyEngine,
        audit_log: AuditLog,
        boundary_rules: tuple[BoundaryRoutingRule, ...] = (),
        boundary: EntitlementBoundary | None = None,
    ) -> None:
        self._policy_engine = policy_engine
        self._audit_log = audit_log
        self._boundary_rules = boundary_rules
        self._boundary = boundary or EntitlementBoundary()
        self._dead_letters: list[FabricMessage] = []
        self._delivered: list[FabricMessage] = []
        self._route_records: list[FabricRouteRecord] = []

    def route(self, message: FabricMessage) -> RouteResult:
        decision = self._policy_engine.may_route(
            source_module=message.source_module,
            destination_module=message.destination,
            payload_schema=message.payload_schema,
            data_mode=message.data_mode,
        )
        self._audit_policy_decision(message, decision)

        if not decision.allowed:
            self._dead_letters.append(message)
            self._route_records.append(FabricRouteRecord(message=message, status="denied", decision=decision))
            self._audit_log.append(
                AuditRecord(
                    event_type=AuditEventType.MODULE_CALL,
                    actor="jinx-bus",
                    summary=f"Message dead-lettered for {message.destination}",
                    metadata={
                        "message_id": message.id,
                        "topic": message.topic,
                        "destination": message.destination,
                        "payload_schema": message.payload_schema,
                        "status": "denied",
                    },
                )
            )
            return RouteResult(False, message, decision, status="denied")

        delivered_message, redacted_fields = self._apply_boundary_rules(message)
        status = "redacted" if redacted_fields else "delivered"
        self._delivered.append(delivered_message)
        self._route_records.append(
            FabricRouteRecord(
                message=delivered_message,
                status=status,
                decision=decision,
                redacted_fields=redacted_fields,
            )
        )
        self._audit_log.append(
            AuditRecord(
                event_type=AuditEventType.MODULE_CALL,
                actor=message.source_module,
                summary=f"Message routed to {message.destination}",
                metadata={
                    "message_id": delivered_message.id,
                    "topic": delivered_message.topic,
                    "destination": delivered_message.destination,
                    "payload_schema": delivered_message.payload_schema,
                    "status": status,
                },
            )
        )
        return RouteResult(True, delivered_message, decision, status=status, redacted_fields=redacted_fields)

    def delivered_messages(self) -> tuple[FabricMessage, ...]:
        return tuple(self._delivered)

    def dead_letters(self) -> tuple[FabricMessage, ...]:
        return tuple(self._dead_letters)

    def route_records(self) -> tuple[FabricRouteRecord, ...]:
        return tuple(self._route_records)

    def _audit_policy_decision(self, message: FabricMessage, decision: PolicyDecision) -> None:
        self._audit_log.append(
            AuditRecord(
                event_type=AuditEventType.POLICY_DECISION,
                actor="jinx-core.policy",
                summary=decision.reason,
                metadata={
                    "allowed": str(decision.allowed),
                    "message_id": message.id,
                    "topic": message.topic,
                    "source_module": message.source_module,
                    "destination": message.destination,
                    "payload_schema": message.payload_schema,
                },
            )
        )

    def _apply_boundary_rules(self, message: FabricMessage) -> tuple[FabricMessage, tuple[str, ...]]:
        for rule in self._boundary_rules:
            if not rule.matches(message):
                continue
            result = self._boundary.redact(
                payload=message.payload,
                allowed_fields=rule.allowed_fields,
                abstract_replacements=rule.abstract_replacements,
            )
            if result.redacted_fields:
                self._audit_log.append(
                    AuditRecord(
                        event_type=AuditEventType.BOUNDARY_REDACTION,
                        actor="jinx-boundary.entitlement",
                        summary=result.explanation,
                        metadata={
                            "message_id": message.id,
                            "source_module": message.source_module,
                            "destination": message.destination,
                            "payload_schema": message.payload_schema,
                            "redacted_fields": ",".join(result.redacted_fields),
                        },
                    )
                )
            return replace(message, payload=result.payload), result.redacted_fields
        return message, ()

"""JINX-BUS policy-enforced message router."""

from dataclasses import dataclass, replace

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
            return RouteResult(False, message, decision)

        delivered_message = self._apply_boundary_rules(message)
        self._delivered.append(delivered_message)
        self._audit_log.append(
            AuditRecord(
                event_type=AuditEventType.MODULE_CALL,
                actor=message.source_module,
                summary=f"Message routed to {message.destination}",
                metadata={
                    "message_id": delivered_message.id,
                    "destination": delivered_message.destination,
                    "payload_schema": delivered_message.payload_schema,
                },
            )
        )
        return RouteResult(True, delivered_message, decision)

    def delivered_messages(self) -> tuple[FabricMessage, ...]:
        return tuple(self._delivered)

    def dead_letters(self) -> tuple[FabricMessage, ...]:
        return tuple(self._dead_letters)

    def _audit_policy_decision(self, message: FabricMessage, decision: PolicyDecision) -> None:
        self._audit_log.append(
            AuditRecord(
                event_type=AuditEventType.POLICY_DECISION,
                actor="jinx-core.policy",
                summary=decision.reason,
                metadata={
                    "allowed": str(decision.allowed),
                    "message_id": message.id,
                    "source_module": message.source_module,
                    "destination": message.destination,
                    "payload_schema": message.payload_schema,
                },
            )
        )

    def _apply_boundary_rules(self, message: FabricMessage) -> FabricMessage:
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
            return replace(message, payload=result.payload)
        return message

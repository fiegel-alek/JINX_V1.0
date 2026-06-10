"""JINX-BUS policy-enforced message router."""

from dataclasses import dataclass

from jinx.bus.messages import FabricMessage
from jinx.common.types.enums import AuditEventType
from jinx.core.audit import AuditLog, AuditRecord
from jinx.core.policy import PolicyDecision, PolicyEngine


@dataclass(frozen=True, slots=True)
class RouteResult:
    delivered: bool
    message: FabricMessage
    decision: PolicyDecision


class MessageRouter:
    def __init__(self, policy_engine: PolicyEngine, audit_log: AuditLog) -> None:
        self._policy_engine = policy_engine
        self._audit_log = audit_log
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

        self._delivered.append(message)
        self._audit_log.append(
            AuditRecord(
                event_type=AuditEventType.MODULE_CALL,
                actor=message.source_module,
                summary=f"Message routed to {message.destination}",
                metadata={
                    "message_id": message.id,
                    "destination": message.destination,
                    "payload_schema": message.payload_schema,
                },
            )
        )
        return RouteResult(True, message, decision)

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

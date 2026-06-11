"""Shared enumerations for safe JINX contracts."""

from enum import StrEnum


class AdvisoryLabel(StrEnum):
    OBSERVATION = "observation"
    ASSESSMENT = "assessment"
    WARNING = "warning"
    RECOMMENDATION = "recommendation"
    SIMULATION_RESULT = "simulation_result"
    CONFIDENCE_LIMITED_INFERENCE = "confidence_limited_inference"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class ProhibitedOutputLabel(StrEnum):
    ORDER = "order"
    COMMAND = "command"
    FIRE_MISSION = "fire_mission"
    AUTONOMOUS_ACTION = "autonomous_action"
    FINAL_DECISION = "final_decision"


class DataMode(StrEnum):
    SYNTHETIC = "synthetic"
    MOCK = "mock"
    OPEN = "open"
    AUTHORIZED = "authorized"
    LIVE_CONTROLLED_ADAPTER = "live_controlled_adapter"


class SafetyClassification(StrEnum):
    CORE_PLATFORM = "core_platform"
    ADVISORY_REASONING = "advisory_reasoning"
    SIMULATION = "simulation"
    MOCK_ADAPTER = "mock_adapter"
    CONTROLLED_REAL_ADAPTER = "controlled_real_adapter"


class AuditEventType(StrEnum):
    INPUT_RECEIVED = "input_received"
    OUTPUT_EMITTED = "output_emitted"
    MODULE_CALL = "module_call"
    POLICY_DECISION = "policy_decision"
    BOUNDARY_REDACTION = "boundary_redaction"
    CONFIDENCE_CHANGE = "confidence_change"
    USER_OVERRIDE = "user_override"
    SIMULATION_EVENT = "simulation_event"
    ADAPTER_USAGE = "adapter_usage"


class EventType(StrEnum):
    COMMUNICATIONS_AVAILABLE = "communications_available"
    COMMUNICATIONS_CHECK = "communications_check"
    COMMUNICATIONS_LOSS = "communications_loss"
    CONFLICTING_REPORT = "conflicting_report"
    HAZARD = "hazard"
    ISR_UPDATE = "isr_update"
    MEDICAL_EVENT = "medical_event"
    MISSION_IMPACT = "mission_impact"
    MOVEMENT_DELAY = "movement_delay"
    WEATHER_IMPACT = "weather_impact"
    ROUTE_ISSUE = "route_issue"
    LOGISTICS_ISSUE = "logistics_issue"
    POSITION_UPDATE = "position_update"
    STATUS_UPDATE = "status_update"
    UNKNOWN_REQUIRES_REVIEW = "unknown_requires_review"


class OperatorReportType(StrEnum):
    POSITION_UPDATE = "position_update"
    STATUS_UPDATE = "status_update"
    COMMUNICATIONS_CHECK = "communications_check"
    MEDICAL = "medical"
    LOGISTICS = "logistics"
    OBSERVATION = "observation"
    HAZARD = "hazard"
    REQUEST_INFORMATION = "request_information"
    UNKNOWN_REQUIRES_REVIEW = "unknown_requires_review"


class HumanCommandType(StrEnum):
    COORDINATION = "coordination"
    INFORMATION_REQUEST = "information_request"
    STATUS_REQUEST = "status_request"
    HUMAN_DIRECTION = "human_direction"
    REVIEW_DECISION = "review_decision"

"""Default roles for early JINX development."""

from jinx.core.identity import AccessControl, Role


def build_default_access_control() -> AccessControl:
    access = AccessControl()
    for role in (
        Role(
            name="system_administrator",
            permissions=frozenset({"admin:all", "audit:read", "config:write"}),
            description="Administers the JINX platform.",
        ),
        Role(
            name="commander",
            permissions=frozenset(
                {"human_command:submit", "cop:read", "advisory:review", "operator_report:review", "isr:read"}
            ),
            description="Provides human command input and reviews advisories.",
        ),
        Role(
            name="c5isr_manager",
            permissions=frozenset(
                {
                    "operator_report:review",
                    "operator_report:submit",
                    "audit:read",
                    "brain:query",
                    "cop:read",
                    "cop:write",
                    "advisory:review",
                    "intel:submit",
                    "isr:read",
                    "isr:write",
                    "mission:write",
                    "sim:inject",
                }
            ),
            description="Manages C5ISR report review and COP state.",
        ),
        Role(
            name="operator",
            permissions=frozenset({"operator_report:submit", "cop_advisory:read"}),
            description="Submits field reports and reads C5ISR advisories.",
        ),
        Role(
            name="network_manager",
            permissions=frozenset({"network:review", "advisory:review"}),
            description="Reviews network-domain issues.",
        ),
        Role(
            name="intel_analyst",
            permissions=frozenset(
                {"brain:query", "intel:review", "intel:submit", "isr:read", "isr:write", "advisory:review"}
            ),
            description="Reviews intelligence-derived summaries and impacts.",
        ),
        Role(
            name="auditor",
            permissions=frozenset({"audit:read", "brain:query", "provenance:read"}),
            description="Reviews audit and provenance trails.",
        ),
    ):
        access.register_role(role)
    return access

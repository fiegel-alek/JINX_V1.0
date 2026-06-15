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
                {
                    "brain:chat",
                    "human_command:submit",
                    "cop:read",
                    "ops:read",
                    "advisory:review",
                    "operator_report:review",
                    "isr:read",
                    "sim:read",
                }
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
                    "brain:chat",
                    "brain:query",
                    "cop:read",
                    "cop:write",
                    "ops:read",
                    "advisory:review",
                    "intel:submit",
                    "isr:read",
                    "isr:write",
                    "mission:write",
                    "net:read",
                    "net:submit",
                    "net:review",
                    "sim:read",
                    "sim:inject",
                    "sim:run",
                }
            ),
            description="Manages C5ISR report review and COP state.",
        ),
        Role(
            name="operator",
            permissions=frozenset(
                {
                    "brain:chat",
                    "operator:read",
                    "operator_report:submit",
                    "cop_advisory:read",
                    "ops:read",
                }
            ),
            description="Submits field reports and reads C5ISR advisories.",
        ),
        Role(
            name="network_manager",
            permissions=frozenset(
                {
                    "advisory:review",
                    "brain:chat",
                    "brain:query",
                    "cop:read",
                    "net:read",
                    "net:submit",
                    "net:review",
                    "ops:read",
                    "sim:read",
                    "sim:run",
                }
            ),
            description="Reviews network-domain issues.",
        ),
        Role(
            name="intel_analyst",
            permissions=frozenset(
                {
                    "brain:chat",
                    "brain:query",
                    "intel:review",
                    "intel:submit",
                    "isr:read",
                    "isr:write",
                    "ops:read",
                    "advisory:review",
                }
            ),
            description="Reviews intelligence-derived summaries and impacts.",
        ),
        Role(
            name="auditor",
            permissions=frozenset(
                {"audit:read", "brain:chat", "brain:query", "ops:read", "provenance:read", "sim:read"}
            ),
            description="Reviews audit and provenance trails.",
        ),
        Role(
            name="simulation_operator",
            permissions=frozenset({"brain:chat", "brain:query", "sim:read", "sim:inject", "sim:run"}),
            description="Runs synthetic scenarios and simulation-only control workflows.",
        ),
    ):
        access.register_role(role)
    return access

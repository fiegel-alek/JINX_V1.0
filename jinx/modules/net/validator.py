"""Synthetic JINX-NET network validation."""

from jinx.modules.net.models import NetworkIssue, NetworkStatus


class NetworkValidator:
    def validate(self, status: NetworkStatus) -> tuple[NetworkIssue, ...]:
        issues: list[NetworkIssue] = []
        if status.timeslot_conflicts:
            issues.append(
                NetworkIssue(
                    issue_type="timeslot_conflict",
                    summary="Synthetic MTDL timeslot conflict requires human network review.",
                    affected_nodes=status.timeslot_conflicts,
                    confidence=status.confidence,
                    provenance=status.provenance,
                )
            )
        if status.los_warnings:
            issues.append(
                NetworkIssue(
                    issue_type="los_warning",
                    summary="Synthetic line-of-sight warning requires human network review.",
                    affected_nodes=status.los_warnings,
                    confidence=status.confidence,
                    provenance=status.provenance,
                )
            )
        return tuple(issues)

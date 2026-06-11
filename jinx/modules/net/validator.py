"""Synthetic JINX-NET network validation."""

from collections import defaultdict

from jinx.modules.net.models import NetworkIssue, NetworkPlan, NetworkStatus, NetworkValidationRun


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

    def validate_plan(self, plan: NetworkPlan) -> tuple[NetworkValidationRun, tuple[NetworkIssue, ...]]:
        issues: list[NetworkIssue] = []
        issues.extend(self._timeslot_conflicts(plan))
        issues.extend(self._los_issues(plan))
        issues.extend(self._missing_timeslot_issues(plan))
        issues.extend(self._topology_issues(plan))
        run = NetworkValidationRun(
            plan_id=plan.id,
            issue_ids=tuple(issue.id for issue in issues),
            confidence=plan.confidence,
            summary=(
                f"Synthetic NET validation found {len(issues)} advisory issue(s). "
                "Human network-manager review is required before any configuration change."
            ),
        )
        return run, tuple(issues)

    def _timeslot_conflicts(self, plan: NetworkPlan) -> tuple[NetworkIssue, ...]:
        by_slot: dict[tuple[str, str], list[str]] = defaultdict(list)
        for allocation in plan.timeslots:
            by_slot[(allocation.epoch, allocation.slot_id)].append(allocation.node_id)
        issues = []
        for (epoch, slot_id), node_ids in by_slot.items():
            unique_nodes = tuple(dict.fromkeys(node_ids))
            if len(unique_nodes) < 2:
                continue
            issues.append(
                NetworkIssue(
                    issue_type="timeslot_conflict",
                    summary=f"Synthetic timeslot {slot_id} in {epoch} is assigned to multiple nodes.",
                    affected_nodes=unique_nodes,
                    confidence=plan.confidence,
                    provenance=plan.provenance,
                    severity="high",
                    recommended_human_actions=(
                        "Ask the network manager to review the synthetic timeslot map.",
                        "Run a replay after human-approved deconfliction.",
                    ),
                )
            )
        return tuple(issues)

    def _los_issues(self, plan: NetworkPlan) -> tuple[NetworkIssue, ...]:
        issues = []
        for link in plan.los_links:
            if link.status not in {"degraded", "blocked"}:
                continue
            issues.append(
                NetworkIssue(
                    issue_type="los_warning",
                    summary=f"Synthetic LOS path {link.from_node} to {link.to_node} is {link.status}: {link.rationale}",
                    affected_nodes=(link.from_node, link.to_node),
                    confidence=plan.confidence,
                    provenance=plan.provenance,
                    severity="high" if link.status == "blocked" else "medium",
                    recommended_human_actions=(
                        "Review terrain, altitude, and relay assumptions in simulation.",
                        "Coordinate with C5ISR before changing mission communication assumptions.",
                    ),
                )
            )
        return tuple(issues)

    def _missing_timeslot_issues(self, plan: NetworkPlan) -> tuple[NetworkIssue, ...]:
        allocated_nodes = {allocation.node_id for allocation in plan.timeslots}
        missing = tuple(node.id for node in plan.nodes if node.id not in allocated_nodes)
        if not missing:
            return ()
        return (
            NetworkIssue(
                issue_type="missing_timeslot",
                summary="Synthetic network plan has nodes without assigned timeslots.",
                affected_nodes=missing,
                confidence=plan.confidence,
                provenance=plan.provenance,
                severity="medium",
                recommended_human_actions=(
                    "Review whether omitted nodes are listen-only, inactive, or incorrectly configured.",
                    "Preserve the issue as advisory until a network manager validates the plan.",
                ),
            ),
        )

    def _topology_issues(self, plan: NetworkPlan) -> tuple[NetworkIssue, ...]:
        if len(plan.nodes) <= 1:
            return (
                NetworkIssue(
                    issue_type="sparse_topology",
                    summary="Synthetic network plan has fewer than two nodes; network feasibility is limited.",
                    affected_nodes=tuple(node.id for node in plan.nodes),
                    confidence=plan.confidence,
                    provenance=plan.provenance,
                    severity="low",
                ),
            )
        return ()

"""License-aware BRAIN context builder."""

from collections.abc import Mapping

from jinx.brain.context_builder.models import BoundedBrainContext

INTEL_KEYS = frozenset({"isr_feeds", "intelligence_summaries", "intelligence_impacts"})
NET_TERMS = ("tdma", "timeslot", "mids", "link-16", "network")


class BrainContextBuilder:
    def build(
        self,
        raw_context: Mapping[str, object],
        allowed_modules: frozenset[str],
        source: str = "jinx-core",
    ) -> BoundedBrainContext:
        if not raw_context:
            raise ValueError("raw_context is required")
        if not allowed_modules:
            raise ValueError("allowed_modules is required")

        context: dict[str, object] = {}
        redactions: list[str] = []
        provenance_refs: list[str] = []

        for key, value in raw_context.items():
            if key in INTEL_KEYS and "jinx-intel" not in allowed_modules:
                redactions.append(f"{key}: blocked because JINX-INTEL is not licensed")
                continue
            if key == "net" and "jinx-net" not in allowed_modules:
                redactions.append("net: blocked because JINX-NET is not licensed")
                continue
            context[key] = self._redact_net_inference(value, redactions, allowed_modules)
            provenance_refs.extend(self._provenance_refs(value))

        uncertainty = [
            "Context is bounded by role, license, and module scope.",
            "BRAIN may not see unlicensed, unavailable, or unreviewed data.",
        ]
        if redactions:
            uncertainty.append("Some context was redacted before reasoning.")

        return BoundedBrainContext(
            source=source,
            allowed_modules=allowed_modules,
            context=context or {"redacted": True},
            redactions=tuple(redactions),
            uncertainty=tuple(uncertainty),
            provenance_refs=tuple(dict.fromkeys(provenance_refs)),
        )

    def _redact_net_inference(
        self,
        value: object,
        redactions: list[str],
        allowed_modules: frozenset[str],
    ) -> object:
        if "jinx-net" in allowed_modules:
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if any(term in lowered for term in NET_TERMS):
                redactions.append("network-domain details abstracted because JINX-NET is not licensed")
                return "Communications-domain review recommended."
        if isinstance(value, Mapping):
            return {
                key: self._redact_net_inference(item, redactions, allowed_modules)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._redact_net_inference(item, redactions, allowed_modules) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact_net_inference(item, redactions, allowed_modules) for item in value)
        return value

    def _provenance_refs(self, value: object) -> list[str]:
        refs: list[str] = []
        if isinstance(value, Mapping):
            candidate = value.get("id") or value.get("event_id") or value.get("report_id")
            if candidate:
                refs.append(str(candidate))
            for item in value.values():
                refs.extend(self._provenance_refs(item))
        elif isinstance(value, (list, tuple)):
            for item in value:
                refs.extend(self._provenance_refs(item))
        return refs

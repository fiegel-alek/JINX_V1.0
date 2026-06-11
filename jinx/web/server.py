"""Dependency-free HTTP/HTTPS-ready server for JINX."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import ssl
from typing import Any
from urllib.parse import urlparse

from jinx.api import JINXAPIHandlers
from jinx.app import JINXApplicationService
from jinx.core.persistence import SQLiteJINXDatabase
from jinx.modules.sim import default_c5isr_scenario_packs

ROLE_PERMISSIONS = {
    "operator": frozenset({"brain:chat", "operator_report:submit", "cop:read", "ops:read"}),
    "commander": frozenset({"human_command:submit", "cop:read", "operator_report:review", "isr:read", "ops:read"}),
    "c5isr_manager": frozenset(
        {
            "audit:read",
            "brain:query",
            "brain:chat",
            "ops:read",
            "operator_report:submit",
            "operator_report:review",
            "cop:read",
            "cop:write",
            "intel:submit",
            "isr:read",
            "isr:write",
            "mission:write",
            "net:read",
            "net:submit",
            "net:review",
            "sim:inject",
            "sim:run",
        }
    ),
    "network_manager": frozenset(
        {
            "audit:read",
            "brain:chat",
            "brain:query",
            "cop:read",
            "net:read",
            "net:submit",
            "net:review",
            "ops:read",
            "sim:run",
        }
    ),
    "intel_analyst": frozenset({"brain:chat", "brain:query", "cop:read", "intel:submit", "isr:read", "isr:write", "ops:read"}),
    "auditor": frozenset({"audit:read", "brain:chat", "brain:query", "cop:read", "isr:read", "ops:read"}),
    "system_administrator": frozenset({"admin:all"}),
}

PACKAGE_PROFILES = {
    "full": {
        "label": "Full JINX Package",
        "modules": ("core", "brain", "c5isr", "net", "intel", "sim", "bus"),
        "apps": ("/apps/ops", "/apps/c5isr", "/apps/net", "/apps/intel"),
    },
    "c5isr": {
        "label": "JINX-C5ISR Package",
        "modules": ("core", "brain", "c5isr", "sim", "bus"),
        "apps": ("/apps/c5isr",),
    },
    "net": {
        "label": "JINX-NET Package",
        "modules": ("core", "brain", "net", "sim", "bus"),
        "apps": ("/apps/net",),
    },
    "intel": {
        "label": "JINX-INTEL Package",
        "modules": ("core", "brain", "intel", "sim", "bus"),
        "apps": ("/apps/intel",),
    },
}

PACKAGE_PERMISSION_PREFIXES = {
    "full": (),
    "c5isr": ("net:", "intel:", "isr:", "ops:"),
    "net": ("operator_report:", "cop:", "mission:", "intel:", "isr:", "human_command:", "ops:"),
    "intel": ("operator_report:", "cop:", "mission:", "net:", "human_command:", "ops:"),
}

NET_REDACTIONS = {
    "JINX-NET": "communications-domain",
    "jinx-net": "communications-domain",
    "network manager": "communications-domain reviewer",
    "Network manager": "Communications-domain reviewer",
    "network-domain": "communications-domain",
    "network": "communications-domain",
    "Network": "Communications-domain",
    "MTDL": "communications",
    "TDMA": "timing",
    "timeslot": "timing allocation",
    "LOS": "communications path",
}


class JINXHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        static_root: Path,
        database: SQLiteJINXDatabase,
        bind_and_activate: bool = True,
    ) -> None:
        self.database = database
        self.api_handlers = JINXAPIHandlers(JINXApplicationService(database=database))
        handler = partial(JINXRequestHandler, directory=str(static_root))
        super().__init__(server_address, handler, bind_and_activate=bind_and_activate)


class JINXRequestHandler(SimpleHTTPRequestHandler):
    server: JINXHTTPServer

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            app_path = self._app_path(parsed.path)
            if app_path is not None:
                self.path = app_path
                super().do_GET()
                return
            if parsed.path == "/api/health":
                self._send_json({"status": "ok", "service": "jinx"})
                return
            if parsed.path == "/api/entitlements":
                package = self._package()
                self._send_json({"package": package, **PACKAGE_PROFILES[package]})
                return
            if parsed.path == "/api/cop":
                self._require_permission("cop:read")
                documents = self.server.database.list_documents("cop_states")
                latest = documents[-1] if documents else {"id": None, "name": "empty", "tracks": []}
                self._send_json(latest)
                return
            if parsed.path == "/api/cop/layers":
                self._require_permission("cop:read")
                self._send_json(self.server.api_handlers.service.layer_config_document())
                return
            if parsed.path == "/api/mission-context":
                self._require_permission("cop:read")
                try:
                    mission = self.server.database.get_document("mission_contexts", "active")
                except KeyError:
                    mission = {"id": None, "mission_statement": "No mission context loaded.", "tasks": []}
                self._send_json({"mission": mission})
                return
            if parsed.path == "/api/mission-impacts":
                self._require_permission("cop:read")
                self._send_json({"mission_impacts": self.server.database.list_documents("mission_impacts")})
                return
            if parsed.path == "/api/review-center":
                self._require_permission("cop:read")
                self._send_json(self.server.api_handlers.service.review_center_document())
                return
            if parsed.path == "/api/timeline":
                self._require_permission("cop:read")
                self._send_json(self.server.api_handlers.service.timeline_document())
                return
            if parsed.path == "/api/operator-reports":
                self._require_permission("cop:read")
                self._send_json({"operator_reports": self.server.database.list_documents("operator_reports")})
                return
            if parsed.path == "/api/events":
                self._require_permission("cop:read")
                self._send_json({"events": self.server.database.list_documents("events")})
                return
            if parsed.path == "/api/advisories":
                self._require_permission("cop:read")
                self._send_json({"advisories": self.server.database.list_documents("cop_advisories")})
                return
            if parsed.path == "/api/conflicts":
                self._require_permission("cop:read")
                self._send_json({"conflicts": self.server.database.list_documents("conflicts")})
                return
            if parsed.path == "/api/recommendations":
                self._require_permission("cop:read")
                self._send_json({"recommendations": self.server.database.list_documents("recommendations")})
                return
            if parsed.path == "/api/core/analysis-runs":
                self._require_permission("cop:read")
                self._send_json(self.server.api_handlers.service.analysis_runs_document())
                return
            if parsed.path == "/api/core/explanations":
                self._require_permission("cop:read")
                self._send_json(self.server.api_handlers.service.explanations_document())
                return
            if parsed.path == "/api/core/context":
                self._require_permission("ops:read")
                self._send_json(self.server.api_handlers.service.core_context_document())
                return
            if parsed.path == "/api/core/ops-console":
                self._require_permission("ops:read")
                self._send_json(self.server.api_handlers.service.core_ops_console_document())
                return
            if parsed.path == "/api/core/operator-loop":
                self._require_permission("ops:read")
                self._send_json(self.server.api_handlers.service.operator_loop_document())
                return
            if parsed.path == "/api/core/fabric":
                self._require_permission("ops:read")
                self._send_json(self.server.api_handlers.service.fabric_monitor_document())
                return
            if parsed.path == "/api/core/policy-decisions":
                self._require_permission("audit:read")
                self._send_json(self.server.api_handlers.service.policy_decisions_document())
                return
            if parsed.path == "/api/core/audit":
                self._require_permission("audit:read")
                self._send_json(self.server.api_handlers.service.audit_document())
                return
            if parsed.path == "/api/core/provenance":
                self._require_permission("audit:read")
                self._send_json(self.server.api_handlers.service.provenance_document())
                return
            if parsed.path == "/api/core/module-boundaries":
                self._require_permission("audit:read")
                self._send_json(self.server.api_handlers.service.module_boundary_document())
                return
            if parsed.path == "/api/brain/references":
                self._require_permission("brain:query")
                self._send_json(self.server.api_handlers.query_brain({"tags": "review"}))
                return
            if parsed.path == "/api/brain/chat-sessions":
                self._require_permission("brain:chat")
                self._send_json(self.server.api_handlers.service.brain_chat_sessions_document())
                return
            if parsed.path == "/api/brain/chat-messages":
                self._require_permission("brain:chat")
                self._send_json(self.server.api_handlers.service.brain_chat_messages_document())
                return
            if parsed.path == "/api/brain/contexts":
                self._require_permission("brain:chat")
                self._send_json(self.server.api_handlers.service.brain_contexts_document())
                return
            if parsed.path == "/api/brain/explanations":
                self._require_permission("brain:chat")
                self._send_json(self.server.api_handlers.service.brain_explanations_document())
                return
            if parsed.path == "/api/brain/options":
                self._require_permission("brain:chat")
                self._send_json(self.server.api_handlers.service.brain_options_document())
                return
            if parsed.path == "/api/brain/checklists":
                self._require_permission("brain:query")
                self._send_json(self.server.api_handlers.service.brain_checklists_document())
                return
            if parsed.path == "/api/brain/learning-proposals":
                self._require_permission("brain:chat")
                self._send_json(self.server.api_handlers.service.learning_proposals_document())
                return
            if parsed.path == "/api/intelligence-summaries":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.intelligence_summaries_document())
                return
            if parsed.path == "/api/intel/summaries":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.intelligence_summaries_document())
                return
            if parsed.path == "/api/intelligence-impacts":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.intelligence_impacts_document())
                return
            if parsed.path == "/api/intel/impacts":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.intelligence_impacts_document())
                return
            if parsed.path == "/api/intel/correlations":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.intelligence_correlations_document())
                return
            if parsed.path == "/api/intel/module-notices":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.intelligence_module_notices_document())
                return
            if parsed.path == "/api/isr-feeds":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.isr_feeds_document())
                return
            if parsed.path == "/api/intel/isr-feeds":
                self._require_permission("isr:read")
                self._send_json(self.server.api_handlers.service.isr_feeds_document())
                return
            if parsed.path == "/api/net/plans":
                self._require_permission("net:read")
                self._send_json(self.server.api_handlers.service.network_plans_document())
                return
            if parsed.path == "/api/net/issues":
                self._require_permission("net:read")
                self._send_json(self.server.api_handlers.service.network_issues_document())
                return
            if parsed.path == "/api/net/validation-runs":
                self._require_permission("net:read")
                self._send_json(self.server.api_handlers.service.network_validation_runs_document())
                return
            if parsed.path == "/api/net/advisories":
                self._require_permission("net:read")
                self._send_json(self.server.api_handlers.service.network_advisories_document())
                return
            if parsed.path == "/api/human-commands":
                self._require_permission("cop:read")
                self._send_json({"human_commands": self.server.database.list_documents("human_commands")})
                return
            if parsed.path == "/api/modules":
                self._require_permission("cop:read")
                self._send_json(
                    {
                        "modules": [
                            {"name": "JINX-Core", "status": "online", "role": "AI advisory processing"},
                            {"name": "JINX-BRAIN", "status": "online", "role": "Doctrine/SOP knowledge"},
                            {"name": "JINX-C5ISR", "status": "online", "role": "COP and operator intake"},
                            {"name": "JINX-NET", "status": "stubbed", "role": "Synthetic MTDL validation"},
                            {"name": "JINX-INTEL", "status": "online", "role": "Synthetic/authorized fusion"},
                            {"name": "JINX-SIM", "status": "online", "role": "Synthetic scenario replay"},
                            {"name": "JINX-BUS", "status": "online", "role": "Policy-enforced routing"},
                        ]
                    }
                )
                return
            if parsed.path == "/api/sim/c5isr-scenarios":
                self._require_permission("cop:read")
                self._send_json(
                    {
                        "scenario_packs": [
                            {
                                "id": pack.id,
                                "name": pack.name,
                                "summary": pack.summary,
                                "injects": list(pack.injects),
                                "expected_outputs": list(pack.expected_outputs),
                            }
                            for pack in default_c5isr_scenario_packs()
                        ]
                    }
                )
                return
            if parsed.path == "/api/sim/runs":
                self._require_permission("cop:read")
                self._send_json({"simulation_runs": self.server.database.list_documents("simulation_runs")})
                return
            if parsed.path == "/":
                self.path = "/index.html"
            super().do_GET()
        except PermissionError as exc:
            self._send_json({"error": str(exc)}, status=403)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/operator-reports":
                self._require_permission("operator_report:submit")
                self._send_json(self.server.api_handlers.submit_operator_report(payload), status=201)
                return
            if parsed.path == "/api/human-commands":
                self._require_permission("human_command:submit")
                self._send_json(self.server.api_handlers.submit_human_command(payload), status=201)
                return
            if parsed.path == "/api/operator-reports/review":
                self._require_permission("operator_report:review")
                self._send_json(self.server.api_handlers.review_operator_report(payload), status=200)
                return
            if parsed.path == "/api/cop/tracks/validate":
                self._require_permission("cop:write")
                self._send_json(self.server.api_handlers.validate_cop_track(payload), status=200)
                return
            if parsed.path == "/api/mission-context":
                self._require_permission("mission:write")
                self._send_json(self.server.api_handlers.submit_mission_context(payload), status=201)
                return
            if parsed.path == "/api/intelligence-summaries":
                self._require_permission("intel:submit")
                self._send_json(self.server.api_handlers.submit_intelligence_summary(payload), status=201)
                return
            if parsed.path == "/api/intel/summaries":
                self._require_permission("intel:submit")
                self._send_json(self.server.api_handlers.submit_intelligence_summary(payload), status=201)
                return
            if parsed.path == "/api/isr-feeds":
                self._require_permission("isr:write")
                self._send_json(self.server.api_handlers.submit_isr_feed_snapshot(payload), status=201)
                return
            if parsed.path == "/api/intel/isr-feeds":
                self._require_permission("isr:write")
                self._send_json(self.server.api_handlers.submit_isr_feed_snapshot(payload), status=201)
                return
            if parsed.path == "/api/net/plans":
                self._require_permission("net:submit")
                self._send_json(self.server.api_handlers.submit_network_plan(payload), status=201)
                return
            if parsed.path == "/api/brain/query":
                self._require_permission("brain:query")
                self._send_json(self.server.api_handlers.query_brain(payload), status=200)
                return
            if parsed.path == "/api/brain/chat":
                self._require_permission("brain:chat")
                self._send_json(self.server.api_handlers.ask_brain_chat(payload), status=201)
                return
            if parsed.path == "/api/sim/demo":
                self._require_permission("sim:inject")
                self._send_json(self._inject_demo_reports(), status=201)
                return
            if parsed.path == "/api/sim/run-c5isr":
                self._require_permission("sim:run")
                self._send_json(self.server.api_handlers.run_c5isr_scenario(payload), status=201)
                return
            self._send_json({"error": "not found"}, status=404)
        except PermissionError as exc:
            self._send_json({"error": str(exc)}, status=403)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=400)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, str]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8")
        if not raw:
            return {}
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return {str(key): str(value) for key, value in payload.items()}

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        payload = self._redact_payload_for_package(payload)
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _role(self) -> str:
        return self.headers.get("X-JINX-Role", "operator")

    def _package(self) -> str:
        package = self.headers.get("X-JINX-Package", "full")
        return package if package in PACKAGE_PROFILES else "full"

    def _require_permission(self, permission: str) -> None:
        role = self._role()
        permissions = ROLE_PERMISSIONS.get(role, frozenset())
        if "admin:all" in permissions or permission in permissions:
            if self._package_allows(permission):
                return
            raise PermissionError(f"package {self._package()} lacks entitlement for {permission}")
        raise PermissionError(f"role {role} lacks permission {permission}")

    def _package_allows(self, permission: str) -> bool:
        denied_prefixes = PACKAGE_PERMISSION_PREFIXES[self._package()]
        return not any(permission.startswith(prefix) for prefix in denied_prefixes)

    @staticmethod
    def _app_path(path: str) -> str | None:
        mapping = {
            "/apps/ops": "/index.html",
            "/ops": "/index.html",
            "/apps/c5isr": "/c5isr.html",
            "/c5isr": "/c5isr.html",
            "/apps/net": "/net.html",
            "/net": "/net.html",
            "/apps/intel": "/intel.html",
            "/intel": "/intel.html",
        }
        return mapping.get(path)

    def _redact_payload_for_package(self, payload: Any) -> Any:
        if self._package() != "c5isr":
            return payload
        return self._redact_net_terms(payload)

    def _redact_net_terms(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._redact_net_terms(item)
                for key, item in value.items()
                if not str(key).startswith("network_") and str(key) not in {"net", "net_detail"}
            }
        if isinstance(value, list):
            return [self._redact_net_terms(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._redact_net_terms(item) for item in value)
        if isinstance(value, str):
            redacted = value
            for needle, replacement in NET_REDACTIONS.items():
                redacted = redacted.replace(needle, replacement)
            return redacted
        return value

    def _inject_demo_reports(self) -> dict[str, Any]:
        mission_response = self.server.api_handlers.submit_mission_context(
            {
                "mission_statement": "Synthetic C5ISR mission monitors Route Alpha and Area Alpha.",
                "commander_intent": "Maintain coherent COP confidence and surface mission impacts for review.",
                "task_title": "Monitor Route Alpha",
                "task_purpose": "Identify confidence-limited route, communications, and weather impacts.",
                "assigned_to": "operator-alpha",
                "route": "Route Alpha",
                "named_area": "Area Alpha",
                "timeline": "T+00 to T+60",
            }
        )
        demo_reports = (
            {
                "reporter_id": "operator-alpha",
                "device_id": "operator-mini-001",
                "report_type": "position_update",
                "summary": "Synthetic position update from operator alpha near Route Alpha.",
                "location": "grid-alpha",
            },
            {
                "reporter_id": "operator-bravo",
                "device_id": "operator-mini-002",
                "report_type": "communications_check",
                "summary": "Synthetic communications check from operator bravo.",
                "location": "grid-bravo",
            },
            {
                "reporter_id": "operator-charlie",
                "device_id": "operator-mini-003",
                "report_type": "hazard",
                "summary": "Synthetic hazard observation requiring C5ISR review.",
                "location": "grid-charlie",
            },
        )
        responses = [self.server.api_handlers.submit_operator_report(report) for report in demo_reports]
        intel_response = self.server.api_handlers.submit_intelligence_summary(
            {
                "source_category": "synthetic_isr_summary",
                "summary": (
                    "Synthetic ISR summary: weather visibility and communications assumptions may affect "
                    "the current operator reports."
                ),
                "reliability": "0.72",
                "related_locations": "grid-alpha,grid-bravo",
                "related_entities": "operator-alpha,operator-bravo",
            }
        )
        feed_response = self.server.api_handlers.submit_isr_feed_snapshot(
            {
                "feed_name": "Synthetic ISR Orbit Alpha",
                "feed_type": "synthetic_full_motion_video",
                "status": "available",
                "coverage_area": "grid-alpha to grid-charlie",
                "summary": "Synthetic ISR feed snapshot available for C5ISR review display.",
                "related_locations": "grid-alpha,grid-charlie",
            }
        )
        return {
            "injected": len(responses),
            "mission": mission_response,
            "reports": responses,
            "intel_summary": intel_response,
            "isr_feed": feed_response,
        }


def run_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    database_path: Path | None = None,
    static_root: Path | None = None,
    certfile: Path | None = None,
    keyfile: Path | None = None,
) -> JINXHTTPServer:
    database = SQLiteJINXDatabase(database_path or Path("data/jinx.sqlite3"))
    static_dir = static_root or Path(__file__).parent / "static"
    server = JINXHTTPServer((host, port), static_dir, database)

    if certfile is not None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(certfile), str(keyfile) if keyfile else None)
        server.socket = context.wrap_socket(server.socket, server_side=True)

    server.serve_forever()
    return server

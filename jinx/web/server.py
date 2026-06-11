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
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"status": "ok", "service": "jinx"})
            return
        if parsed.path == "/api/cop":
            documents = self.server.database.list_documents("cop_states")
            latest = documents[-1] if documents else {"id": None, "name": "empty", "tracks": []}
            self._send_json(latest)
            return
        if parsed.path == "/api/operator-reports":
            self._send_json({"operator_reports": self.server.database.list_documents("operator_reports")})
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/operator-reports":
                self._send_json(self.server.api_handlers.submit_operator_report(payload), status=201)
                return
            if parsed.path == "/api/human-commands":
                self._send_json(self.server.api_handlers.submit_human_command(payload), status=201)
                return
            self._send_json({"error": "not found"}, status=404)
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
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


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

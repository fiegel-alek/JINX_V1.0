"""Run the JINX web server."""

from pathlib import Path
import argparse

from jinx.web.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the JINX web/API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--database", type=Path, default=Path("data/jinx.sqlite3"))
    parser.add_argument("--certfile", type=Path)
    parser.add_argument("--keyfile", type=Path)
    args = parser.parse_args()
    run_server(
        host=args.host,
        port=args.port,
        database_path=args.database,
        certfile=args.certfile,
        keyfile=args.keyfile,
    )


if __name__ == "__main__":
    main()

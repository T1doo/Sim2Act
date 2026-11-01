"""Explicit TEST_ONLY SQLite programs; never an installed production launcher.

Runs the actual API, Worker and supervisor in separate Python processes. No
provider, PostgreSQL emulation, grant, secret or network outside loopback.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store
from sim2act.desktop_protocol import TEST_ONLY, Supervisor
from sim2act.desktop_service import run_api_role, run_worker_role
from sim2act.process_env import system_environment
from sim2act.worker import Worker

TOKEN = "public-desktop-supervisor-test-only"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--role", choices=["api", "worker"])
    parser.add_argument("--session")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--wrong-worker-pid", action="store_true")
    parser.add_argument("--preflight-delay", type=float, default=0)
    args = parser.parse_args()
    url = "sqlite:///" + str(args.root / "explicit-test-only.db")
    settings = Settings(url, args.root, mode="mock")
    if args.role:
        def store():
            return Store(url, test_only=True)
        if args.role == "api":
            def factory():
                db = store()
                return create_app(db, settings), db.engine.dispose
            result = run_api_role(factory, session=args.session, backend=TEST_ONLY,
                port=args.port, input_stream=sys.stdin, output_stream=sys.stdout)
        else:
            output = sys.stdout
            if args.wrong_worker_pid:
                class WrongPid:
                    def write(self, line):
                        value = json.loads(line)
                        if value["event"] == "ROLE_READY":
                            value["pid"] += 1
                        return sys.stdout.write(json.dumps(value) + "\n")
                    def flush(self):
                        sys.stdout.flush()
                output = WrongPid()
            result = run_worker_role(lambda: Worker(store(), settings),
                session=args.session, backend=TEST_ONLY,
                input_stream=sys.stdin, output_stream=output)
        raise SystemExit(result)

    def preflight():
        time.sleep(args.preflight_delay)
        args.root.mkdir(parents=True, exist_ok=True)
        db = Store(url, test_only=True)
        try:
            if not (args.root / "initialized-test-only").exists():
                db.initialize()
                db.user("explicit test-only principal", TOKEN)
                (args.root / "initialized-test-only").write_text("TEST_ONLY_SQLITE\n")
        finally:
            db.engine.dispose()

    def command(role, session, port):
        result = [sys.executable, "-B", "-u", str(Path(__file__).resolve()),
            "--root", str(args.root), "--role", role, "--session", session,
            "--port", str(port)]
        if args.wrong_worker_pid:
            result.append("--wrong-worker-pid")
        return result

    result = Supervisor(args.root, TEST_ONLY, hashlib.sha256(b"test-only-db-binding").hexdigest(),
        command, system_environment(), port=args.port, startup_seconds=15, stop_seconds=15,
        input_stream=sys.stdin, output_stream=sys.stdout).run(preflight)
    raise SystemExit(result)


if __name__ == "__main__":
    main()

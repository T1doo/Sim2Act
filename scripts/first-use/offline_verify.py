"""Synthetic first-use UI verification, not a production launcher or model demo.

Creates only its own temporary SQLite test database and a fixed synthetic test
identity. Uses real product HTTP routes/JavaScript and the normal Worker. Never
reads .env, accepts a DSN/token, contacts a model, or changes production storage.
Requires installed project dependencies and developer Node/jsdom.
"""

import argparse
import json
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from sqlalchemy import func, select

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, app_drafts, internal_app_runs, internal_instance_data, principals
from sim2act.worker import Worker


class NeverProvider:
    def request(self, *_args, **_kwargs):
        raise AssertionError("Model calls forbidden in synthetic first-use verification")

    complete = request


def verify():
    if not shutil.which("node"):
        return {"status": "BLOCKED", "phase": "developer_node", "error_type": "MissingTool"}
    module_probe = subprocess.run(
        ["node", "-e", "require.resolve('jsdom')"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )
    if module_probe.returncode:
        return {"status": "BLOCKED", "phase": "developer_jsdom", "error_type": "MissingTool"}
    with tempfile.TemporaryDirectory(prefix="sim2act-first-use-") as directory:
        root = Path(directory)
        settings = Settings("sqlite:///" + str(root / "fixture.db"), root, mode="mock")
        store = Store(settings.database_url, test_only=True)
        store.initialize()
        store.user("Synthetic first-use fixture", "synthetic-first-use-A")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(store, settings), host="127.0.0.1", port=port, log_level="critical"
            )
        )
        stop = threading.Event()
        errors = []

        def work():
            try:
                worker = Worker(store, settings, NeverProvider())
                while not stop.is_set():
                    worker.once()
                    stop.wait(0.05)
            except Exception as exc:
                errors.append(type(exc).__name__)

        api_thread = threading.Thread(target=server.run, daemon=True)
        worker_thread = threading.Thread(target=work, daemon=True)
        api_thread.start()
        worker_thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not api_thread.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError("API unavailable")
                time.sleep(0.02)
            driver = subprocess.run(
                [
                    "node",
                    str(Path(__file__).with_name("offline_ui.cjs")),
                    f"http://127.0.0.1:{port}",
                    str(root / "ui.json"),
                ],
                capture_output=True,
                text=True,
                timeout=75,
                check=False,
            )
            if not (root / "ui.json").exists():
                return {
                    "status": "FAIL",
                    "phase": "driver_before_receipt",
                    "error_type": "DriverUnavailable",
                }
            report = json.loads((root / "ui.json").read_text())
            if driver.returncode or errors:
                report["status"] = "FAIL"
                report["worker_errors"] = errors
                return report
            # Reopen persisted storage through a separate Store; never preseed results.
            cold = Store(settings.database_url, test_only=True)
            try:
                with cold.tx() as connection:
                    tables = {
                        "drafts": app_drafts,
                        "app_runs": internal_app_runs,
                        "result_versions": internal_instance_data,
                        "principals": principals,
                    }
                    counts = {
                        name: connection.execute(
                            select(func.count()).select_from(table)
                        ).scalar_one()
                        for name, table in tables.items()
                    }
                if counts != {"drafts": 1, "app_runs": 2, "result_versions": 2, "principals": 3}:
                    # Project and CSV creation each add their own runtime, not another user.
                    raise AssertionError("Unexpected persisted fixture counts")
                report["cold_store_counts"] = counts
            finally:
                cold.engine.dispose()
            report["model_mode"] = "mock"
            report["model_provider"] = "forbidden_by_assertion"
            report["production_installation"] = "NOT_RUN"
            report["windows"] = "NOT_RUN"
            report["fixture_cleanup"] = "owned_threads_stopped_and_temp_database_removed"
            return report
        finally:
            stop.set()
            server.should_exit = True
            worker_thread.join(10)
            api_thread.join(10)
            store.engine.dispose()
            if worker_thread.is_alive() or api_thread.is_alive():
                raise RuntimeError("Owned thread cleanup incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Synthetic result JSON file")
    args = parser.parse_args()
    try:
        report = verify()
    except Exception as exc:
        report = {"status": "FAIL", "phase": "controller", "error_type": type(exc).__name__}
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "browser": "NOT_RUN", "windows": "NOT_RUN"}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Local lifecycle. Children receive validated app settings, never owner/CI credentials."""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]


def process(record):
    try:
        p = psutil.Process(record["pid"])
        if not p.is_running() or p.status() in {psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD}:
            return None
        if abs(p.create_time() - record["created_at"]) > 0.01:
            return None
        expected = record.get("command")
        if not expected:
            # Backward-compatible verification for PID records from the first engineering run.
            expected = (
                [sys.executable, "-m", "sim2act.worker"]
                if record["kind"] == "worker"
                else [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "sim2act.api:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(record["port"]),
                    "--no-access-log",
                ]
            )
        if p.cmdline() != expected:
            return None
        return p
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied as e:
        raise RuntimeError(
            "Cannot verify owned process; retain PID record and inspect permissions"
        ) from e


def stop(records):
    for record in records:
        p = process(record)
        if p:
            p.terminate()
            for _ in range(100):
                if process(record) is None:
                    break
                time.sleep(0.1)
            else:
                p.kill()
                for _ in range(50):
                    if process(record) is None:
                        break
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Owned process did not stop")


def stop_launched(children):
    """Clean retained child handles even while startup argv is temporarily unavailable."""
    for child in children:
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["doctor", "start", "status", "stop"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    from sim2act.config import Settings

    if args.command == "status":
        from sim2act.status_report import collect_status

        settings = Settings.from_env()
        output = collect_status(
            settings.data_dir / "processes.json",
            process,
            lambda: httpx.get(f"http://127.0.0.1:{args.port}/health", timeout=3),
        )
        print(json.dumps(output, ensure_ascii=False))
        return

    from sim2act.db import Store
    from sim2act.process_env import application_environment

    if args.command == "doctor":
        from sim2act.db_readiness import cleanup_failed, inspect_database, unavailable

        engine = None
        mode = "UNKNOWN"
        try:
            if sys.version_info[:2] != (3, 12):
                report = unavailable("PYTHON_UNSUPPORTED")
            else:
                settings = Settings.from_env()
                mode = settings.mode.upper() if settings.mode in {"mock", "live"} else "UNKNOWN"
                engine = Store(settings.database_url).engine
                report = inspect_database(engine)
        except Exception:
            report = unavailable("CONFIGURATION_UNAVAILABLE")
        finally:
            if engine is not None:
                try:
                    engine.dispose()
                except Exception:
                    report = cleanup_failed(report)
        report.update(
            python=sys.version.split()[0],
            mode=mode,
            database=(
                "UP"
                if any(
                    c["check"] == "connection" and c["status"] == "PASS" for c in report["checks"]
                )
                else "OFFLINE"
            ),
        )
        print(json.dumps(report, ensure_ascii=False))
        if report["status"] != "STRUCTURAL_READY":
            raise SystemExit(1)
        return

    settings = Settings.from_env()
    data = settings.data_dir
    state = data / "processes.json"
    records = json.loads(state.read_text()) if state.exists() else []
    url = f"http://127.0.0.1:{args.port}"
    if args.command == "stop":
        stop(records)
        state.unlink(missing_ok=True)
        print("Owned API/worker stopped; database service and data preserved.")
    else:
        if any(process(r) for r in records):
            raise SystemExit("Owned process already running; inspect Status first")
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", args.port))
            except OSError:
                raise SystemExit("Port occupied; no process started") from None
        data.mkdir(parents=True, exist_ok=True)
        launched = []
        children = []
        try:
            for kind, command in [
                (
                    "api",
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "sim2act.api:create_app",
                        "--factory",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(args.port),
                        "--no-access-log",
                    ],
                ),
                ("worker", [sys.executable, "-m", "sim2act.worker"]),
            ]:
                with (data / (kind + ".log")).open("ab") as log:
                    p = subprocess.Popen(
                        command,
                        cwd=ROOT,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=log,
                        env=application_environment(settings),
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                        start_new_session=os.name != "nt",
                    )
                children.append(p)
                launched.append(
                    {
                        "kind": kind,
                        "pid": p.pid,
                        "created_at": psutil.Process(p.pid).create_time(),
                        "port": args.port,
                        "command": command,
                    }
                )
            for _ in range(30):
                if any(child.poll() is not None for child in children):
                    raise RuntimeError("API/worker exited; inspect local logs")
                try:
                    h = httpx.get(url + "/health", timeout=1).json()
                    if (
                        h.get("worker") == "UP"
                        and h.get("database") == "UP"
                        and all(process(r) for r in launched)
                    ):
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError("Startup health timed out")
            state.write_text(json.dumps(launched, indent=2))
            print(
                json.dumps(
                    {
                        "url": url,
                        "processes": launched,
                        "data_dir": str(data),
                        "mode": settings.mode.upper(),
                    }
                )
            )
        except BaseException:
            stop_launched(children)
            raise


if __name__ == "__main__":
    main()

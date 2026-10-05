"""Local process lifecycle. Credentials stay in inherited environment, never PID files."""

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["doctor", "start", "status", "stop"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    from sim2act.config import Settings
    from sim2act.db import Store

    settings = Settings.from_env()
    data = settings.data_dir
    state = data / "processes.json"
    records = json.loads(state.read_text()) if state.exists() else []
    url = f"http://127.0.0.1:{args.port}"
    if args.command == "doctor":
        if sys.version_info[:2] != (3, 12):
            raise SystemExit("Python 3.12 required")
        with Store(settings.database_url).engine.connect() as c:
            from sqlalchemy import text

            c.execute(text("SELECT 1"))
        print(
            json.dumps(
                {
                    "python": sys.version.split()[0],
                    "database": "UP",
                    "data_dir": str(data),
                    "mode": settings.mode.upper(),
                    "windows_native": "NOT_RUN",
                }
            )
        )
    elif args.command == "stop":
        stop(records)
        state.unlink(missing_ok=True)
        print("Owned API/worker stopped; database service and data preserved.")
    elif args.command == "status":
        output = {r["kind"]: {"pid": r["pid"], "alive": process(r) is not None} for r in records}
        try:
            output["health"] = httpx.get(url + "/health", timeout=3).json()
        except httpx.HTTPError:
            output["health"] = "OFFLINE"
        print(json.dumps(output, ensure_ascii=False))
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
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                        start_new_session=os.name != "nt",
                    )
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
                if not all(process(r) for r in launched):
                    raise RuntimeError("API/worker exited; inspect local logs")
                try:
                    h = httpx.get(url + "/health", timeout=1).json()
                    if h.get("worker") == "UP" and h.get("database") == "UP":
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
            stop(launched)
            raise


if __name__ == "__main__":
    main()

"""Local lifecycle. Children receive validated app settings, never owner/CI credentials."""

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]


def import_config(path):
    """Explicit private file only; never discover, execute or print its values."""
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    try:
        with path.open(encoding="utf-8-sig") as stream:
            content = stream.read(65537)
        if len(content) > 65536 or "\0" in content:
            raise ValueError
        values = {}
        for line in content.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            match = re.fullmatch(r"(SIM2ACT_[A-Z_]+|INTERN_API_TOKEN)=(.*)", line)
            if match is None or match[1] in values:
                raise ValueError
            if len((match[1] + "=" + match[2]).encode("utf-16-le")) // 2 > 32760:
                raise ValueError
            values[match[1]] = match[2]
    except (OSError, UnicodeError, ValueError):
        raise ValueError(
            "Selected configuration is missing, duplicated or malformed; edit it privately."
        ) from None
    os.environ.update(values)


def production_selection(path):
    """Five original selectors only; neither a credential nor an approval."""
    from sim2act.production_evidence import ACCOUNT_ID

    try:
        with Path(path).open(encoding="utf-8-sig") as stream:
            value = stream.read(4097)
        if len(value) > 4096:
            raise ValueError

        def unique(pairs):
            data = {}
            for key, item in pairs:
                if key in data:
                    raise ValueError
                data[key] = item
            return data

        value = json.loads(value, object_pairs_hook=unique)
        patterns = dict(
            user=r"user_[a-f0-9]{32}",
            project=r"proj_[a-f0-9]{32}",
            trial=r"[A-Za-z0-9_-]{1,100}",
            approval=r"[A-Za-z0-9_-]{1,100}",
            account=re.escape(ACCOUNT_ID),
        )
        if (
            type(value) is not dict
            or set(value) != set(patterns)
            or any(
                type(value[k]) is not str or re.fullmatch(pattern, value[k]) is None
                for k, pattern in patterns.items()
            )
        ):
            raise ValueError
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ValueError(
            "Select an existing five-field Intern trial selection; no credentials or extra fields."
        ) from None
    return value


def selection_worker_arguments(selection):
    return [
        part for name, value in selection.items() for part in ("--spec-production-" + name, value)
    ]


def check_selection(store, settings, selection):
    from sqlalchemy import select

    from sim2act.db import quotas
    from sim2act.spec_production import install

    # Original contract/approval/account/software/permission checks; this
    # constructs a Worker but never claims a Run or sends a model request.
    install(
        store,
        settings,
        user=selection["user"],
        project_id=selection["project"],
        trial_key=selection["trial"],
        approval_key=selection["approval"],
        account_id=selection["account"],
    )
    with store.engine.connect() as connection:
        exists = connection.execute(
            select(quotas.c.subject).where(quotas.c.subject == settings.quota_subject)
        ).first()
    if exists is None:
        raise ValueError("QUOTA_SUBJECT_NOT_INITIALIZED")


def validation_store(settings):
    """Bound only the explicit diagnostic/prelaunch connection, not Run leases."""
    from sqlalchemy.engine import make_url

    from sim2act.db import Store

    url = make_url(settings.database_url)
    if url.password == "LOCAL_PASSWORD":
        raise ValueError("Template database credential must be replaced privately")
    options = url.query.get("options", "")
    if type(options) is not str:
        raise ValueError("Unsupported diagnostic connection options")
    url = url.update_query_dict(
        dict(
            connect_timeout="5", options=options + " -c statement_timeout=5000 -c lock_timeout=1000"
        )
    )
    return Store(url.render_as_string(hide_password=False))


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
    parser.add_argument("--config", help="Explicit private KEY=value file; never auto-discovered")
    parser.add_argument(
        "--spec-selection", help="Existing five-field approved trial JSON, no credentials"
    )
    args = parser.parse_args()
    if args.spec_selection and args.command not in {"doctor", "start"}:
        parser.error("--spec-selection belongs to doctor or start only")
    try:
        if args.config:
            import_config(args.config)
        selected = production_selection(args.spec_selection) if args.spec_selection else None
    except ValueError as error:
        parser.exit(1, str(error) + "\n")
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
                store = validation_store(settings)
                engine = store.engine
                report = inspect_database(engine)
                if selected:
                    from sim2act.spec_production import configuration_issues

                    report["production_configuration_missing"] = configuration_issues(
                        store, settings
                    )
                if selected and report["status"] == "STRUCTURAL_READY":
                    try:
                        check_selection(store, settings, selected)
                        report["trial_selection"] = "CURRENT_APPROVED_TRIAL"
                    except Exception as error:
                        report["status"] = "BLOCKED"
                        report["trial_selection"] = "REJECTED_OR_UNAVAILABLE"
                        reason = (
                            "QUOTA_SUBJECT_NOT_INITIALIZED"
                            if isinstance(error, ValueError)
                            and str(error) == "QUOTA_SUBJECT_NOT_INITIALIZED"
                            else "ORIGINAL_TRIAL_APPROVAL_ACCOUNT_OR_CONFIGURATION_REQUIRED"
                        )
                        report["checks"].append(
                            dict(
                                check="trial_selection",
                                status="BLOCKED",
                                reason=reason,
                            )
                        )
                elif selected:
                    report["trial_selection"] = "NOT_CHECKED_DATABASE_BLOCKED"
                report["execution_performed"] = False
                report["model_requests"] = 0
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
        report["next_steps"] = (
            []
            if report["status"] == "STRUCTURAL_READY"
            else [
                "Select the existing PostgreSQL application-role URL in the explicit private config; replace LOCAL_PASSWORD.",
                "For schema/permission failures, use the existing migration operator/database administrator; this check does not repair or grant access.",
                "For QUOTA_SUBJECT_NOT_INITIALIZED, the existing migration operator must initialize the same fixed Intern quota subject.",
                "For trial selection, restore the original approved scope under this software/material version, current permissions and fixed account; never rebind an old unconfigured key.",
            ]
        )
        print(json.dumps(report, ensure_ascii=False))
        if report["status"] != "STRUCTURAL_READY":
            raise SystemExit(1)
        return

    try:
        settings = Settings.from_env()
        if selected:
            selected_store = validation_store(settings)
            try:
                check_selection(selected_store, settings, selected)
            finally:
                selected_store.engine.dispose()
    except Exception:
        parser.exit(
            1,
            "Configuration or original approved trial selection rejected; run doctor with the same config/selection. No process started.\n",
        )
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
                (
                    "worker",
                    [sys.executable, "-m", "sim2act.worker"]
                    + (selection_worker_arguments(selected) if selected else []),
                ),
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

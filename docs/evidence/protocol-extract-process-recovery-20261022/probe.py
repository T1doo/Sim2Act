"""One owned SQLite process restart; synthetic clocks, existing Mock fixture.

No product changes, G0, real models, external HTTP or UNKNOWN response import.
Run only with the repository's existing virtualenv and an unused output root.
"""

import argparse
import dataclasses
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]


def save(path, value):
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    pending.replace(path)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serve(app):
    import uvicorn

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=False)
    thread.start()
    end = time.monotonic() + 15
    while not server.started and thread.is_alive() and time.monotonic() < end:
        time.sleep(0.01)
    if not server.started:
        server.should_exit = True
        thread.join(10)
        raise AssertionError(f"Owned API failed to start; thread still alive={thread.is_alive()}")
    return server, thread, port


def stop(server, thread):
    end = time.monotonic() + 10
    server.should_exit = True
    thread.join(max(0, end - time.monotonic()))
    assert not thread.is_alive(), "Owned API did not exit normally"
    for worker in threading.enumerate():
        if worker.name == "AnyIO worker thread":
            worker.join(max(0, end - time.monotonic()))
            assert not worker.is_alive(), "Owned API request thread did not exit normally"


def cleanup(root, processes):
    """One shared ten-second allowance; evidence errors cannot skip reaping."""
    end = time.monotonic() + 10
    errors = []
    denied = set()
    owned = [p for p in processes if p is not None]
    try:
        (root / "stop-api").touch()
    except OSError as error:
        errors.append(repr(error))
    for proc in owned:
        if proc.poll() is None:
            try:
                proc.terminate()
            except OSError as error:
                errors.append(repr(error))
                if isinstance(error, PermissionError):
                    denied.add(proc.pid)
    grace = min(end, time.monotonic() + 5)
    for proc in owned:
        if proc.poll() is None:
            try:
                proc.wait(timeout=max(0, grace - time.monotonic()))
            except subprocess.TimeoutExpired:
                pass
    for proc in owned:
        if proc.poll() is None and proc.pid not in denied:
            try:
                proc.kill()
            except OSError as error:
                errors.append(repr(error))
    for proc in owned:
        if proc.poll() is None:
            try:
                proc.wait(timeout=max(0, end - time.monotonic()))
            except subprocess.TimeoutExpired:
                errors.append(f"Unconfirmed terminal PID {proc.pid}")
    record = dict(
        processes=[dict(pid=p.pid, exit_code=p.poll()) for p in owned],
        unknown_processes_touched=0,
        denied_pids=sorted(denied),
        errors=errors,
        status="CONFIRMED"
        if not errors and all(p.poll() is not None for p in owned)
        else "UNKNOWN",
    )
    save(root / "cleanup.json", record)  # A save error propagates after reaping.
    return record


def original(root):
    import httpx
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    from test_protocol_extract_completion import prepared, snapshot

    from sim2act.api import create_app

    class Factory:
        def mktemp(self, name):
            path = root / name
            path.mkdir()
            return path

    statements = []

    def record(c, cursor, statement, parameters, context, many):
        statements.append(dict(statement=statement, parameters=parameters, many=many))

    event.listen(Engine, "before_cursor_execute", record)
    fixture = prepared.__wrapped__(Factory())
    data = next(fixture)  # Existing original Source2 + normal1 + interrupted1.
    server = thread = None
    try:
        server, thread, port = serve(create_app(data["env"][0], data["settings"]))
        with httpx.Client(trust_env=False, timeout=5) as client:
            response = client.get(
                f"http://127.0.0.1:{port}/api/projects/{data['pid']}/protocol/runs/{data['interrupted']}",
                headers={"Authorization": "Bearer secret test token"},
            )
        assert response.status_code == 200 and response.json()["result"] is None
        assert len(data["sends"]) == 4
        settings = dataclasses.asdict(data["settings"])
        settings["data_dir"] = str(settings["data_dir"])
        request = dict(
            expected_version=data["current"]["version"],
            expected_fence=data["current"]["fence"],
            request_key="process-complete-known",
        )
        save(
            root / "original.json",
            dict(
                pid=os.getpid(),
                api_port=port,
                root=str(data["root"]),
                user=data["user"],
                project=data["pid"],
                run=data["interrupted"],
                settings=settings,
                request=request,
                current=data["current"],
                captured=data["captured"],
                normal=data["normal"],
                original_api_get=response.json(),
                before=snapshot(data["env"][0]),
                sidecar_sha256=sha(data["root"] / (data["interrupted"] + ".json")),
                resume_at=data["end"] + 31,
                mock_requests=len(data["sends"]),
            ),
        )
    finally:
        if server is not None:
            stop(server, thread)
        try:
            next(fixture)
        except StopIteration:
            pass
        else:
            raise AssertionError("Fixture did not close")
    save(
        root / "original-exit.json",
        dict(
            pid=os.getpid(),
            api_thread_joined=True,
            fixture_closed=True,
            no_live_worker_threads=True,
            normal_return=True,
        ),
    )
    event.remove(Engine, "before_cursor_execute", record)
    save(root / "original-sql.json", statements)


def restarted_api(root):
    from sqlalchemy import event

    from sim2act.api import create_app
    from sim2act.config import Settings
    from sim2act.db import Store
    from sim2act.model import InternModel
    from sim2act.model_budget import BudgetedProvider
    from sim2act.worker import Worker

    original = json.loads((root / "original.json").read_text())
    time.time = lambda: original["resume_at"]  # Explicit test-only business clock.
    settings = dict(original["settings"])
    settings["data_dir"] = Path(settings["data_dir"])
    settings = Settings(**settings)
    forbidden_calls = []

    def forbidden(*args, **kwargs):
        forbidden_calls.append("send/reserve/accept")
        save(root / "forbidden-call.json", forbidden_calls)
        raise AssertionError("Restarted API attempted a model call/reservation/acceptance")

    for owner, name in (
        (InternModel, "request"),
        (InternModel, "request_serialized"),
        (BudgetedProvider, "call"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "reserve"),
    ):
        setattr(owner, name, forbidden)
    store = Store(settings.database_url, test_only=True)  # No initialize/migrate/reset.
    statements = []

    def record(c, cursor, statement, parameters, context, many):
        statements.append(dict(statement=statement, parameters=parameters, many=many))

    event.listen(store.engine, "before_cursor_execute", record)
    server = thread = None
    normal = False
    try:
        server, thread, port = serve(create_app(store, settings))
        save(
            root / "ready.json", dict(pid=os.getpid(), port=port, test_clock=original["resume_at"])
        )
        end = time.monotonic() + 90
        while not (root / "stop-api").exists() and thread.is_alive() and time.monotonic() < end:
            time.sleep(0.02)
        assert (root / "stop-api").exists(), "No normal stop request within API allowance"
        normal = True
    finally:
        if server is not None:
            stop(server, thread)
        event.remove(store.engine, "before_cursor_execute", record)
        store.engine.dispose()
        save(root / "api-sql.json", statements)
        save(
            root / "api-exit.json",
            dict(
                pid=os.getpid(),
                api_thread_joined=thread is not None and not thread.is_alive(),
                store_disposed=True,
                forbidden_calls=forbidden_calls,
                normal_return=normal and not forbidden_calls,
            ),
        )
    assert not forbidden_calls


def run(root):
    import httpx
    from sqlalchemy import select, update
    from test_protocol_extract_completion import snapshot

    from sim2act.db import Store, events, protocol_jobs, runs
    from sim2act.errors import DomainError

    def interrupted(signum, frame):
        raise TimeoutError("Owned probe interrupted; cleanup only, no retry")

    signal.signal(signal.SIGTERM, interrupted)

    root.mkdir()  # Refuse any reused root; one attempt, no automatic retry.
    frozen = json.loads(
        (
            REPO / "docs/evidence/protocol-extract-completion-20261022/final-source-manifest.json"
        ).read_text()
    )
    assert all(sha(REPO / name) == digest for name, digest in frozen.items())
    probe_digest = sha(Path(__file__).resolve())
    save(root / "preflight.json", dict(probe_sha256=probe_digest, frozen_source_count=len(frozen)))
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    receipts = []
    deadline = time.monotonic() + 180
    env = dict(os.environ)
    env.pop("SIM2ACT_TEST_DATABASE_URL", None)
    env.pop("SIM2ACT_RECORD_PG_CONFIG", None)

    def launch(mode):
        assert sha(Path(__file__).resolve()) == probe_digest
        assert all(sha(REPO / name) == digest for name, digest in frozen.items())
        log = (root / (mode + ".log")).open("wb")
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), mode, str(root)],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log.close()
        return proc

    def wait(proc):
        code = proc.wait(timeout=max(0.1, deadline - time.monotonic()))
        receipts.append(dict(pid=proc.pid, exit_code=code))
        assert code == 0, receipts
        assert sha(Path(__file__).resolve()) == probe_digest

    old = new = None
    try:
        old = launch("original")
        wait(old)  # Reaped exit0 BEFORE the new API is even spawned.
        original = json.loads((root / "original.json").read_text())
        assert json.loads((root / "original-exit.json").read_text())["pid"] == old.pid
        assert original["current"]["lease_until"] < original["resume_at"]
        assert original["resume_at"] < original["current"]["created_at"] + 300
        new = launch("api")
        startup = time.monotonic() + 20
        while (
            not (root / "ready.json").exists() and new.poll() is None and time.monotonic() < startup
        ):
            time.sleep(0.02)
        ready = json.loads((root / "ready.json").read_text())
        assert ready["pid"] == new.pid != old.pid and old.poll() == 0
        base = f"http://127.0.0.1:{ready['port']}/api/projects/{original['project']}/protocol/runs/{original['run']}"
        http = []
        with httpx.Client(
            trust_env=False, timeout=15, headers={"Authorization": "Bearer secret test token"}
        ) as client:

            def request(method, path, payload=None):
                response = client.request(method, path, json=payload)
                http.append(
                    dict(
                        method=method,
                        path=path,
                        request=payload,
                        status=response.status_code,
                        response=response.json(),
                    )
                )
                assert response.status_code == 200, response.text
                return response.json()

            first = request("POST", base + "/complete-extraction", original["request"])
            assert (
                first["status"] == "SUCCEEDED"
                and first["provider_requests"] == 0
                and not first["cached"]
            )
            done = request("GET", base)
            assert done["result"]["compiled_plan"] == original["captured"]["compiled"]
            assert done["result"]["protocol_result"] == original["captured"]["result"]

            # Same received Run: fingerprint/receipt exactly, not Python loose equality alone.
            def canonical(value):
                return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

            assert canonical(done["result"]["compiled_plan"]) == canonical(
                original["captured"]["compiled"]
            )
            assert canonical(done["result"]["protocol_result"]) == canonical(
                original["captured"]["result"]
            )
            cached = request("POST", base + "/complete-extraction", original["request"])
            assert cached == dict(first, cached=True)
        save(root / "http.json", http)
        (root / "stop-api").touch()
        wait(new)
        store = Store(original["settings"]["database_url"], test_only=True)
        try:
            after = snapshot(store)
            assert {name for name in after if after[name] != original["before"][name]} == {
                "runs",
                "protocol_jobs",
                "events",
            }
            side = Path(original["root"]) / (original["run"] + ".json")
            assert sha(side) == original["sidecar_sha256"]
            with store.engine.connect() as c:
                row = dict(
                    c.execute(select(runs).where(runs.c.id == original["run"])).mappings().one()
                )
                job = dict(
                    c.execute(
                        select(protocol_jobs).where(protocol_jobs.c.run_id == original["run"])
                    )
                    .mappings()
                    .one()
                )
                assert row["created_at"] == original["current"]["created_at"]
                assert row["fence"] == original["current"]["fence"] + 1
                accepted = c.execute(
                    select(events.c.data).where(
                        events.c.run_id == original["run"],
                        events.c.kind == "PROTOCOL_EXTRACT_ACCEPTED_V2",
                    )
                ).scalar_one()
                recovered = c.execute(
                    select(events.c.data).where(
                        events.c.run_id == original["run"],
                        events.c.kind == "PROTOCOL_EXTRACT_RECOVERED_V2",
                    )
                ).scalar_one()
                assert recovered["completed_at"] < min(
                    accepted["origin"]["deadline"], accepted["origin"]["provider_deadline"]
                )
            stale = None
            try:
                with store.tx() as c:
                    store.guard(c, original["run"], original["request"]["expected_fence"])
                    c.execute(
                        update(runs)
                        .where(runs.c.id == original["run"])
                        .values(error={"stale_write": True})
                    )
            except DomainError as error:
                stale = error.public()
            assert stale and stale["code"] == "VERSION_CONFLICT"
            assert snapshot(store) == after
            save(
                root / "after.json",
                dict(
                    tables=after,
                    run=row,
                    job=job,
                    accepted=accepted,
                    recovered=recovered,
                    stale_worker_guard_rejection=stale,
                    stale_write_reached=False,
                    sidecar_sha256=sha(side),
                ),
            )
        finally:
            store.engine.dispose()
        assert not (root / "forbidden-call.json").exists()
        assert all(sha(REPO / name) == digest for name, digest in frozen.items())
        assert sha(Path(__file__).resolve()) == probe_digest
        result = dict(
            classification="SYNTHETIC_SQLITE_SEPARATE_PROCESS_RECOVERY_NOT_G0",
            source=source,
            processes=receipts,
            original_exit_confirmed_before_new_spawn=True,
            mock_requests=4,
            recovery_mock_requests=0,
            real_model_requests=0,
            http="owned loopback API only; no external business HTTP",
            budget_seconds=180,
            cleanup_seconds=10,
            clock="explicit synthetic business clocks in both processes; not real-clock G0",
            exact_original_plan_and_receipt=True,
            immutable_accounting_tables=True,
            unchanged_sidecar=True,
            unchanged_original_created_at_and_deadlines=True,
            same_command_key_cached=True,
            old_fence_write_guard_rejected=True,
            no_database_reset=True,
            source_hashes_unchanged=True,
            probe_sha256=probe_digest,
            status="PASS",
        )
    finally:
        terminal = cleanup(root, (old, new))
    assert terminal["status"] == "CONFIRMED", terminal
    save(root / "result.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "original", "api"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        if args.mode != "run":
            proof = json.loads((args.root / "preflight.json").read_text())
            assert sha(Path(__file__).resolve()) == proof["probe_sha256"]
        {"run": run, "original": original, "api": restarted_api}[args.mode](args.root.resolve())
    except BaseException:
        traceback.print_exc()
        raise

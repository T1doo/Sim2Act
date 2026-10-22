"""One owned SQLite process restart; synthetic clocks, single Source Mock path.

No product changes, G0, real models, external HTTP or UNKNOWN response import.
Run only with the repository's existing virtualenv and an unused output root.
"""

import argparse
import dataclasses
import hashlib
import json
import os
import shutil
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
    import copy

    import httpx
    import pytest
    from sqlalchemy import event, select
    from sqlalchemy.engine import Engine
    from test_protocol_jobs import LIMITS, source_payload, wire
    from test_protocol_jobs import env as jobs_env

    from sim2act import protocol_jobs as jobs
    from sim2act.api import create_app
    from sim2act.db import attempts, events, fingerprint, meta, operations, runs
    from sim2act.db import protocol_request_slots as slots
    from sim2act.model import InternModel
    from sim2act.model_budget import BudgetedProvider, initialize_ledger
    from sim2act.protocol_api import ProtocolAttemptRunner
    from sim2act.protocol_reviews import evaluation_contract
    from sim2act.protocol_source_completion import READY

    class StopBoundary(BaseException):
        pass

    statements, sends = [], []
    ticks = [1800000000.0]
    patch = pytest.MonkeyPatch()
    patch.delenv("SIM2ACT_TEST_DATABASE_URL", raising=False)
    patch.setattr(time, "time", lambda: ticks[0])
    fixture_root = root / "owned-source"
    fixture_root.mkdir()
    fixture = jobs_env.__wrapped__(fixture_root)
    data = next(fixture)
    store, user, pid, material, _, worker, _ = data
    server = thread = None
    normal = False

    def record(c, cursor, statement, parameters, context, many):
        statements.append(dict(statement=statement, parameters=parameters, many=many))

    def snapshot():
        with store.engine.connect() as c:
            return {
                t.name: sorted(fingerprint(dict(r)) for r in c.execute(select(t)).mappings())
                for t in meta.sorted_tables
            }

    event.listen(Engine, "before_cursor_execute", record)
    try:
        accepted = jobs.enqueue(
            store, user, pid, "source", source_payload(material), "original-source-process", LIMITS
        )
        rid = accepted["run_id"]
        contract, _ = evaluation_contract("protocol.synthetic.a-source.v1")
        pending = [wire(rid=material), wire(contract["expected_output"])]

        def factory(worker, run, snapshot):
            def transport(request):
                assert len(sends) < 2, "Source process Mock cap exceeded; no retry"
                assert request.url == InternModel.ENDPOINT
                sends.append(
                    dict(run_id=rid, body_sha256=hashlib.sha256(request.content).hexdigest())
                )
                ticks[0] += 7
                return httpx.Response(200, json=pending.pop(0))

            model = InternModel(
                dataclasses.replace(worker.s, live_enabled=True, token="synthetic-only"),
                httpx.MockTransport(transport),
            )
            path = fixture_root / (rid + ".json")
            initialize_ledger(path, snapshot["scope"])

            def authorize(scope):
                with store.tx() as c:
                    for ref in scope["resource_ids"]:
                        store.authorize(c, user, run["runtime_id"], pid, ref, "resource.read")
                return True

            provider = BudgetedProvider(
                model,
                path,
                snapshot["scope"],
                "source_a",
                authorize=authorize,
                clock=lambda: ticks[0],
            )
            return ProtocolAttemptRunner(worker, run, snapshot, provider)

        worker.protocol_runner_factory = factory
        captured = {}
        original_complete = jobs.complete_in_tx
        claimed = store.claim(worker.id, worker.s.lease_seconds)
        assert claimed and claimed["id"] == rid
        # Freeze the completion command before original process exit.
        request = dict(
            expected_version=claimed["version"],
            expected_fence=claimed["fence"],
            request_key="process-complete-source-known",
        )

        def cut(store, c, current, snapshot, result, compiled, fence):
            assert current["id"] == rid and compiled is None and fence == claimed["fence"]
            attempt_rows = list(
                c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings()
            )
            slot_rows = list(c.execute(select(slots).where(slots.c.run_id == rid)).mappings())
            op_rows = list(
                c.execute(select(operations).where(operations.c.run_id == rid)).mappings()
            )
            ready = list(
                c.execute(
                    select(events.c.data).where(events.c.run_id == rid, events.c.kind == READY)
                ).scalars()
            )
            assert len(ready) == 1 and len(attempt_rows) == len(slot_rows) == 2
            assert all(a["status"] == "RECEIVED" for a in attempt_rows + slot_rows)
            assert len(op_rows) == 1 and op_rows[0]["status"] == "VERIFIED"
            last_aid = ready[0]["origins"][-1]["attempt_id"]
            mirrors = list(
                c.execute(
                    select(events.c.data).where(events.c.run_id == last_aid, events.c.kind == READY)
                ).scalars()
            )
            assert len(mirrors) == 1 and fingerprint(ready[0]) == fingerprint(mirrors[0])
            assert ready[0]["result_fingerprint"] == fingerprint(result)
            assert not c.execute(
                select(events.c.id).where(
                    events.c.run_id == rid, events.c.kind == "PROTOCOL_COMPLETED"
                )
            ).first()
            captured.update(
                result=copy.deepcopy(result),
                ready=copy.deepcopy(ready[0]),
                operations=[dict(o) for o in op_rows],
                attempts=[dict(a) for a in attempt_rows],
                slots=[dict(s) for s in slot_rows],
            )
            raise StopBoundary()

        with patch.context() as boundary:
            boundary.setattr(jobs, "complete_in_tx", cut)
            try:
                jobs.process_job(worker, claimed)
            except StopBoundary:
                pass
            else:
                raise AssertionError("Real Source READY boundary not reached")
        assert jobs.complete_in_tx is original_complete and len(sends) == 2 and not pending
        with store.tx() as c:
            current = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
            assert current["result"] is None and current["status"] == "RUNNING"
            assert list(
                c.execute(
                    select(events.c.data).where(events.c.run_id == rid, events.c.kind == READY)
                ).scalars()
            ) == [captured["ready"]]
        server, thread, port = serve(create_app(store, worker.s))
        with httpx.Client(trust_env=False, timeout=5) as client:
            response = client.get(
                f"http://127.0.0.1:{port}/api/projects/{pid}/protocol/runs/{rid}",
                headers={"Authorization": "Bearer secret test token"},
            )
        assert response.status_code == 200 and response.json()["result"] is None
        settings = dataclasses.asdict(worker.s)
        settings["data_dir"] = str(settings["data_dir"])
        save(
            root / "original.json",
            dict(
                pid=os.getpid(),
                api_port=port,
                root=str(fixture_root),
                user=user,
                project=pid,
                run=rid,
                settings=settings,
                request=request,
                current=current,
                captured=captured,
                original_api_get=response.json(),
                before=snapshot(),
                sidecar_sha256=sha(fixture_root / (rid + ".json")),
                resume_at=ticks[0] + 31,
                mock_requests=len(sends),
            ),
        )
        normal = True
    finally:
        try:
            if server is not None:
                stop(server, thread)
        finally:
            try:
                next(fixture)
            except StopIteration:
                pass
            else:
                raise AssertionError("Owned fixture generator did not close")
            finally:
                save(
                    root / "original-budget.json",
                    dict(
                        mock_cap=2,
                        mock_requests=len(sends),
                        sends=sends,
                        real_model_requests=0,
                        external_business_http=0,
                        automatic_retry=False,
                        lease_seconds=worker.s.lease_seconds,
                        run_seconds=worker.s.run_seconds,
                        clock="explicit synthetic business clock; not real-clock G0",
                    ),
                )
                event.remove(Engine, "before_cursor_execute", record)
                save(root / "original-sql.json", statements)
                patch.undo()
    alive = [t.name for t in threading.enumerate() if t is not threading.main_thread()]
    assert not alive, alive
    save(
        root / "original-exit.json",
        dict(
            pid=os.getpid(),
            api_thread_joined=True,
            fixture_closed=True,
            store_disposed=True,
            alive_threads=alive,
            normal_return=normal,
        ),
    )


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
        (BudgetedProvider, "preflight"),
        (BudgetedProvider, "accept_candidate"),
        (Worker, "reserve"),
        (Worker, "__init__"),
        (Store, "claim"),
    ):
        setattr(owner, name, forbidden)
    from sim2act.protocol_api import ProtocolAttemptRunner

    ProtocolAttemptRunner.__init__ = forbidden
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
        stopped_normally = False
        alive = None
        try:
            if server is not None:
                stop(server, thread)
            alive = [t.name for t in threading.enumerate() if t is not threading.main_thread()]
            assert not alive, alive
            stopped_normally = True
        finally:
            event.remove(store.engine, "before_cursor_execute", record)
            store.engine.dispose()
            save(root / "api-sql.json", statements)
            save(
                root / "api-exit.json",
                dict(
                    pid=os.getpid(),
                    api_thread_joined=thread is not None and not thread.is_alive(),
                    store_disposed=True,
                    alive_threads=alive,
                    forbidden_calls=forbidden_calls,
                    normal_return=normal and stopped_normally and not forbidden_calls,
                ),
            )
    assert not forbidden_calls


def run(root):
    import httpx
    from sqlalchemy import select, update

    from sim2act.db import fingerprint, meta

    def snapshot(store):
        with store.engine.connect() as c:
            return {
                t.name: sorted(fingerprint(dict(r)) for r in c.execute(select(t)).mappings())
                for t in meta.sorted_tables
            }

    from sim2act.db import Store, events, protocol_jobs, runs
    from sim2act.errors import DomainError

    def interrupted(signum, frame):
        raise TimeoutError("Owned probe interrupted; cleanup only, no retry")

    signal.signal(signal.SIGTERM, interrupted)

    root.mkdir()  # Refuse any reused root; one attempt, no automatic retry.
    manifest_path = Path(__file__).resolve().with_name("frozen-source-manifest.json")
    frozen = json.loads(manifest_path.read_text())
    manifest_digest = sha(manifest_path)
    assert all(sha(REPO / name) == digest for name, digest in frozen.items())
    probe_digest = sha(Path(__file__).resolve())
    started_at = time.monotonic()
    save(
        root / "preflight.json",
        dict(
            probe_sha256=probe_digest,
            manifest_sha256=manifest_digest,
            frozen_source_count=len(frozen),
            work_seconds=180,
            cleanup_seconds=10,
            mock_cap=2,
            loopback_http_cap=4,
            retry=False,
        ),
    )
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    receipts, launches = [], []
    deadline = time.monotonic() + 180
    env = dict(os.environ)
    env.pop("SIM2ACT_TEST_DATABASE_URL", None)
    env.pop("SIM2ACT_RECORD_PG_CONFIG", None)

    def launch(mode):
        assert sha(Path(__file__).resolve()) == probe_digest
        assert sha(manifest_path) == manifest_digest
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
        launches.append(dict(mode=mode, pid=proc.pid, spawned_monotonic=time.monotonic()))
        save(root / "launches.json", launches)
        return proc

    def wait(proc):
        code = proc.wait(timeout=max(0.1, deadline - time.monotonic()))
        receipts.append(dict(pid=proc.pid, exit_code=code, reaped_monotonic=time.monotonic()))
        assert code == 0, receipts
        assert sha(Path(__file__).resolve()) == probe_digest

    old = new = None
    try:
        old = launch("original")
        wait(old)  # Reaped exit0 BEFORE the new API is even spawned.
        original = json.loads((root / "original.json").read_text())
        old_exit = json.loads((root / "original-exit.json").read_text())
        assert old_exit["pid"] == old.pid and old_exit["normal_return"]
        assert (
            old_exit["api_thread_joined"]
            and old_exit["fixture_closed"]
            and old_exit["store_disposed"]
        )
        assert old_exit["alive_threads"] == []
        assert original["current"]["lease_until"] < original["resume_at"]
        assert original["resume_at"] < original["current"]["created_at"] + 300
        shutil.copyfile(Path(original["root"]) / "jobs.sqlite", root / "before.sqlite")
        shutil.copyfile(
            Path(original["root"]) / (original["run"] + ".json"),
            root / "original-received-sidecar.json",
        )
        new = launch("api")
        assert receipts[0]["reaped_monotonic"] < launches[-1]["spawned_monotonic"]
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
                assert len(http) < 3, "Loopback recovery HTTP cap exceeded; no retry"
                response = client.request(method, path, json=payload)
                try:
                    value = response.json()
                    json_ok = True
                except ValueError:
                    value = dict(non_json_response=response.text)
                    json_ok = False
                http.append(
                    dict(
                        method=method,
                        path=path,
                        request=payload,
                        status=response.status_code,
                        response=value,
                        json_ok=json_ok,
                    )
                )
                save(root / "http.json", http)
                assert response.status_code == 200 and json_ok, response.text
                return value

            first = request("POST", base + "/complete-source", original["request"])
            assert (
                first["status"] == "WAITING_APPROVAL"
                and first["provider_requests"] == 0
                and not first["cached"]
            )
            done = request("GET", base)
            assert done["status"] == "WAITING_APPROVAL" and done["semantic_status"] == "UNKNOWN"
            assert "compiled_plan" not in done["result"]
            assert done["result"]["protocol_result"] == original["captured"]["result"]

            # Same received Run: fingerprint/receipt exactly, not Python loose equality alone.
            def canonical(value):
                return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

            assert canonical(done["result"]["protocol_result"]) == canonical(
                original["captured"]["result"]
            )
            cached = request("POST", base + "/complete-source", original["request"])
            assert canonical(cached) == canonical(dict(first, cached=True))
        save(root / "http.json", http)
        (root / "stop-api").touch()
        wait(new)
        new_exit = json.loads((root / "api-exit.json").read_text())
        assert new_exit["pid"] == new.pid and new_exit["normal_return"]
        assert new_exit["api_thread_joined"] and new_exit["store_disposed"]
        assert new_exit["alive_threads"] == [] and new_exit["forbidden_calls"] == []
        shutil.copyfile(Path(original["root"]) / "jobs.sqlite", root / "after.sqlite")
        api_statements = json.loads((root / "api-sql.json").read_text())
        writes = [
            r
            for r in api_statements
            if r["statement"].split()[0].upper()
            in {"UPDATE", "INSERT", "DELETE", "CREATE", "DROP", "ALTER", "REPLACE"}
        ]
        assert len(writes) == 7
        assert sum(r["statement"].startswith("UPDATE ") for r in writes) == 3
        assert sum(r["statement"].startswith("INSERT INTO events ") for r in writes) == 4
        assert all(
            r["statement"].startswith(
                ("UPDATE runs ", "UPDATE protocol_jobs ", "INSERT INTO events ")
            )
            for r in writes
        )
        save(
            root / "sql-summary.json",
            dict(
                api_statement_count=len(api_statements),
                writes=writes,
                ddl=0,
                deletes=0,
                new_attempts=0,
                new_slots=0,
            ),
        )
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
                        events.c.kind == "PROTOCOL_SOURCE_READY_V2",
                    )
                ).scalar_one()
                recovered = c.execute(
                    select(events.c.data).where(
                        events.c.run_id == original["run"],
                        events.c.kind == "PROTOCOL_SOURCE_RECOVERED_V2",
                    )
                ).scalar_one()
                assert recovered["completed_at"] < min(
                    x
                    for origin in accepted["origins"]
                    for x in (origin["deadline"], origin["provider_deadline"])
                )
                assert fingerprint(accepted) == fingerprint(original["captured"]["ready"])
                assert row["version"] == original["current"]["version"] + 1
                assert row["lease_until"] == 0 and row["error"] is None
                assert first["result_fingerprint"] == job["result_fingerprint"]
                assert row["result"] == job["result_snapshot"]
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
        assert sha(manifest_path) == manifest_digest
        elapsed = time.monotonic() - started_at
        assert elapsed <= 180, "Work allowance expired; no retry"
        result = dict(
            classification="SYNTHETIC_SQLITE_SEPARATE_PROCESS_RECOVERY_NOT_G0",
            source=source,
            processes=receipts,
            launches=launches,
            manifest_sha256=manifest_digest,
            original_exit_confirmed_before_new_spawn=True,
            mock_requests=2,
            mock_cap=2,
            recovery_mock_requests=0,
            recovery_reservations=0,
            total_loopback_http=4,
            real_model_requests=0,
            http="owned loopback API only; no external business HTTP",
            budget_seconds=180,
            cleanup_seconds=10,
            clock="explicit synthetic business clocks in both processes; not real-clock G0",
            exact_original_source_result_and_receipts=True,
            status_after_completion="WAITING_APPROVAL",
            semantic_status="UNKNOWN",
            immutable_accounting_tables=True,
            unchanged_sidecar=True,
            unchanged_original_created_at_and_deadlines=True,
            same_command_key_cached=True,
            old_fence_write_guard_rejected=True,
            no_database_reset=True,
            source_hashes_unchanged=True,
            probe_sha256=probe_digest,
            work_elapsed_seconds=elapsed,
            status="PASS",
        )
    except BaseException as exc:
        save(
            root / "failure.json",
            dict(
                status="UNKNOWN",
                error=repr(exc),
                owned_processes=[
                    dict(pid=p.pid, exit_code=p.poll()) for p in (old, new) if p is not None
                ],
                no_automatic_retry=True,
            ),
        )
        raise
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
            manifest_path = Path(__file__).resolve().with_name("frozen-source-manifest.json")
            assert sha(manifest_path) == proof["manifest_sha256"]
            frozen = json.loads(manifest_path.read_text())
            assert all(sha(REPO / name) == digest for name, digest in frozen.items())
        {"run": run, "original": original, "api": restarted_api}[args.mode](args.root.resolve())
    except BaseException:
        traceback.print_exc()
        raise

"""Complete source-read proof boundaries, independent of trial five-slot admission.

The source is produced by the existing Worker/adapter and verified completely.
No successful source, receipts, lease or approval is fabricated or renewed here.
"""

import json
import sqlite3
import threading
from dataclasses import replace
from types import SimpleNamespace

import conftest
import httpx
import pytest
import test_natural_spec_apps as apps
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_pb_natural_specs import drive_to_success

from sim2act import pb_natural_specs as pb
from sim2act.api import create_app
from sim2act.contracts import Limits
from sim2act.db import Store, attempts, fingerprint, runs
from sim2act.errors import DomainError


@pytest.fixture(scope="module")
def prefix(tmp_path_factory):
    root = tmp_path_factory.mktemp("actual-natural-source")
    environment = conftest.env.__wrapped__(root)
    env = next(environment)
    data = apps.setup(env)
    original_async = httpx.MockTransport.handle_async_request
    original_sync = httpx.MockTransport.handle_request
    try:
        generation, _, release, inst, generated = apps.ready(data, style="ordered")
        assert len(generated) == 3
        source_id = apps.enqueue(data, release, inst)
        sent = []
        claims = drive_to_success(data, source_id, apps.transport(sent, apps.SOURCE))
        state = apps.inspect(data, inst, source_id)
        assert state.status_code == 200 and state.json()["status"] == "SUCCEEDED", state.text
        assert len(sent) == 2
        limits = Limits(**{k: getattr(data[1], k) for k in Limits.model_fields})
        with data[0].tx() as c:
            binding, proof = pb.source(data[0], c, data[3], data[4], source_id, limits)
            rows = [dict(r) for r in c.execute(select(attempts.c.id, attempts.c.status,
                attempts.c.mode).where(attempts.c.run_id == source_id)).mappings()]
            source = dict(c.execute(select(runs.c.id, runs.c.status, runs.c.version,
                runs.c.fence, runs.c.created_at, runs.c.lease_until)
                .where(runs.c.id == source_id)).mappings().one())
        assert len(rows) == 2 and all(r["status"] == "VERIFIED" and r["mode"] == "MOCK" for r in rows)
        assert httpx.MockTransport.handle_async_request is original_async
        assert httpx.MockTransport.handle_request is original_sync
        saved = root / "actual-successful-source.db"
        with sqlite3.connect(data[0].engine.url.database) as origin, sqlite3.connect(saved) as copy:
            origin.backup(copy)
        (root / "ACTUAL_SOURCE.json").write_text(json.dumps(dict(
            generation_run=generation, source=source, source_attempts=rows,
            actual_generation_sends=3, actual_source_sends=2,
            original_worker_claims=claims, proof=proof, proof_fingerprint=fingerprint(proof),
            source_goal=binding["goal"], limits=limits.model_dump(),
            trial_budget_installed=False, real_models=0, source_history_fabricated=False,
            lease_and_run_timestamps_unchanged=True), indent=2))
        yield SimpleNamespace(data=data, source_id=source_id, limits=limits, saved=saved)
    finally:
        data[2].close()
        environment.close()


@pytest.fixture
def cloned(prefix, tmp_path):
    target = tmp_path / "isolated-actual-source-copy.db"
    with sqlite3.connect(prefix.saved) as origin, sqlite3.connect(target) as copy:
        origin.backup(copy)
    store = Store("sqlite:///" + str(target), test_only=True)
    settings = replace(prefix.data[1], database_url=str(store.engine.url))
    client = TestClient(create_app(store, settings))
    client.headers["Authorization"] = "Bearer synthetic-test-A"
    try:
        yield store, settings, client, *prefix.data[3:]
    finally:
        client.close()
        store.engine.dispose()


@pytest.mark.parametrize("change", ["nested_copy", "write", "failed_write", "limits", "store", "authority", "recursion", "exit", "exception", "user", "project", "source", "thread", "limits_mutation"])
def test_source_read_segment_complete_proof_and_invalidation(prefix, cloned, monkeypatch, change):
    from sqlalchemy import insert
    from sqlalchemy.exc import IntegrityError

    store, user, pid = cloned[0], cloned[3], cloned[4]
    limits = prefix.limits.model_copy(deep=True)
    original = pb._source
    calls = []

    def counted(*args, **kwargs):
        calls.append(change)
        return original(*args, **kwargs)

    monkeypatch.setattr(pb, "_source", counted)
    other = Store(cloned[1].database_url, test_only=True)
    try:
        with store.tx() as c:
            info = c.info
            with pb._source_reads(store, c):
                first = pb.source(store, c, user, pid, prefix.source_id, limits)
                assert len(calls) == 1
                if change == "nested_copy":
                    first[0]["segment_mutation"] = True
                    with pb._source_reads(store, c):
                        second = pb.source(store, c, user, pid, prefix.source_id, limits)
                    assert "segment_mutation" not in second[0] and len(calls) == 1
                elif change == "write":
                    c.execute(update(runs).where(runs.c.id == prefix.source_id).values(version=runs.c.version))
                    assert "pb_source_reads" not in c.info
                    pb.source(store, c, user, pid, prefix.source_id, limits)
                    assert len(calls) == 2
                elif change == "failed_write":
                    with pytest.raises(IntegrityError):
                        c.execute(insert(runs).from_select([col.name for col in runs.c],
                            select(runs).where(runs.c.id == prefix.source_id)))
                    assert "pb_source_reads" not in c.info
                    pb.source(store, c, user, pid, prefix.source_id, limits)
                    assert len(calls) == 2
                elif change == "limits":
                    different = limits.model_copy(update=dict(max_total_tokens=limits.max_total_tokens + 1))
                    try:
                        pb.source(store, c, user, pid, prefix.source_id, different)
                    except DomainError:
                        pass
                    assert len(calls) == 2
                elif change == "store":
                    pb.source(other, c, user, pid, prefix.source_id, limits)
                    assert len(calls) == 2
                elif change in ("user", "project", "source"):
                    with pytest.raises(DomainError):
                        pb.source(store, c, "user_" + "0" * 32 if change == "user" else user,
                            "proj_" + "0" * 32 if change == "project" else pid,
                            "run_" + "0" * 32 if change == "source" else prefix.source_id, limits)
                    assert len(calls) == 2
                elif change == "thread":
                    checked = []
                    token = c.info["pb_source_reads"]
                    thread = threading.Thread(target=lambda: checked.append(
                        pb._source_reads_current(store, c, token)))
                    thread.start()
                    thread.join(timeout=5)
                    assert not thread.is_alive() and checked == [False]
                    assert pb._source_reads_current(store, c, token) and len(calls) == 1
                elif change == "limits_mutation":
                    original_recheck = store.recheck_proof_authorities
                    checked = []
                    def changed(connection, proof):
                        original_recheck(connection, proof)
                        limits.max_total_tokens += 1
                        checked.append(True)
                    monkeypatch.setattr(store, "recheck_proof_authorities", changed)
                    try:
                        pb.source(store, c, user, pid, prefix.source_id, limits)
                    except DomainError:
                        pass
                    assert checked == [True] and len(calls) == 2
                elif change == "authority":
                    checked = []
                    def revoked(connection, proof):
                        checked.append(proof["_call_authorities"])
                        raise DomainError("GRANT_REVOKED")
                    monkeypatch.setattr(store, "recheck_proof_authorities", revoked)
                    with pytest.raises(DomainError, match="revoked|GRANT|权限|授权"):
                        pb.source(store, c, user, pid, prefix.source_id, limits)
                    assert len(checked) == 1 and checked[0] and len(calls) == 1
                    assert not c.info["pb_source_reads"].results
                elif change == "recursion":
                    token = c.info["pb_source_reads"]
                    token.results.clear()
                    def recurse(*args, **kwargs):
                        calls.append(change)
                        return pb.source(*args, **kwargs)
                    monkeypatch.setattr(pb, "_source", recurse)
                    with pytest.raises(DomainError, match="Recursive source"):
                        pb.source(store, c, user, pid, prefix.source_id, limits)
                    assert len(calls) == 2 and not token.results and not token.inflight
                elif change == "exception":
                    with pytest.raises(RuntimeError, match="segment exit"):
                        with pb._source_reads(store, c):
                            raise RuntimeError("segment exit")
                    # Caught nested exception leaves only the original outer read call.
                    pb.source(store, c, user, pid, prefix.source_id, limits)
                    assert len(calls) == 2
            assert "pb_source_reads" not in c.info
            if change == "exit":
                pb.source(store, c, user, pid, prefix.source_id, limits)
                assert len(calls) == 2
        assert "pb_source_reads" not in info
        with store.engine.connect() as connection:
            with connection.begin():
                assert pb._source_transaction(store, connection) is None
                with pb._source_reads(store, connection):
                    assert "pb_source_reads" not in connection.info
        with pytest.raises(RuntimeError, match="outer segment"):
            with store.tx() as connection, pb._source_reads(store, connection):
                outer_info = connection.info
                raise RuntimeError("outer segment")
        assert "pb_source_reads" not in outer_info
    finally:
        other.engine.dispose()

"""Real SQL cell reads, not old-ID parameter matching, define the privacy gate."""

import copy
import json
from fractions import Fraction

import pytest
from fastapi.testclient import TestClient
from sql_private_barrier import PrivateReadBarrier
from sqlalchemy import event, func, insert, select, update
from sqlalchemy.exc import DatabaseError
from test_csv_dag_instances import create, enqueue
from test_csv_logic_reuse import authorize
from test_project_column_material_reuse import (
    FREE,
    NoModel,
    accept,
    binding,
    register,
    source,
    work,
)

from sim2act.api import create_app
from sim2act.db import (
    Store,
    attempts,
    events,
    fingerprint,
    grants,
    operations,
    protocol_jobs,
    resources,
    run_contracts,
    runs,
)
from sim2act.protocol_jobs import NAMESPACE, is_protocol_job, protocol_run_ids
from sim2act.protocol_pool import _protocol_attempts
from sim2act.worker import Worker


def ordinary(env, key):
    response = env[2].post(f"/api/projects/{env[5]}/runs", json=dict(
        goal="synthetic scheduler scope", resource_refs=[env[6]], request_key=key))
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def historical(env):
    rid = ordinary(env, "protected-history")
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status="SUCCEEDED",
            context={"messages": [{"role": "user", "content": "old private history"}]},
            result={"private": "old successful synthetic result"}))
        before = copy.deepcopy(dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one()))
    return rid, before


@pytest.mark.parametrize("sql", [
    "SELECT context FROM runs",
    "SELECT result FROM runs WHERE id IN (?, ?)",
    "SELECT r.context FROM runs r JOIN run_contracts c ON c.run_id = r.id WHERE c.run_id = ?",
    'SELECT "r"."result" FROM "runs" AS "r" WHERE "r"."id" = ?',
    "SELECT context FROM runs WHERE id IN (SELECT run_id FROM run_contracts WHERE run_id = ?)",
    "WITH saved AS (SELECT result FROM runs WHERE id = ?) SELECT * FROM saved",
    "SELECT max(context) FROM runs",
    "SELECT count(*) FROM runs WHERE result IS NOT NULL",
    "SELECT main.runs.context FROM main.runs WHERE id = ?",
    "WITH private_read_runs AS (SELECT context FROM main.runs WHERE id = ?) SELECT * FROM private_read_runs",
    'WITH "private_read_runs" AS (SELECT result FROM main.runs WHERE id = ?) SELECT * FROM "private_read_runs"',
    '/* leading comment */ WITH private_read_runs AS (SELECT context FROM main.runs WHERE id = ?) SELECT * FROM private_read_runs',
])
def test_cell_barrier_rejects_actual_private_access_in_every_query_shape(env, sql):
    rid, before = historical(env)
    count = sql.count("?")
    with PrivateReadBarrier(env[0], {rid}) as barrier:
        with env[0].engine.connect() as c:
            assert c.execute(select(runs.c.id, runs.c.status)).first()
        assert not barrier.evaluated
        with pytest.raises(DatabaseError):
            with env[0].engine.connect() as c:
                c.exec_driver_sql(sql, tuple([rid] * count)).all()
        assert barrier.blocked
    with env[0].tx() as c:
        assert dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one()) == before


def test_claim_does_not_evaluate_unrelated_historical_private_cells(env, tmp_path):
    rid, before = historical(env)
    target = ordinary(env, "current-target")
    with PrivateReadBarrier(env[0], {rid}) as barrier:
        try:
            claimed = env[0].claim("current-target-worker", 30)
            assert claimed["id"] == target
            assert not barrier.blocked
        finally:
            (tmp_path / "cell-barrier.json").write_text(json.dumps(dict(
                old_run=rid, target_run=target, blocked=barrier.blocked,
                evaluated=barrier.evaluated, sql=barrier.statements), indent=2))
    with env[0].tx() as c:
        assert dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one()) == before


@pytest.mark.parametrize("mask", range(1, 32))
def test_every_surviving_protocol_marker_combination_stops_generic_recovery(env, mask):
    """Fault-injected incomplete ledgers; no accepted protocol result is claimed."""
    rid = ordinary(env, "marker-mask-" + str(mask))
    with env[0].tx() as c:
        saved = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        context = copy.deepcopy(saved["context"])
        if mask & 4:
            context["kind"] = NAMESPACE
        result = {"private": "retained synthetic marker history"}
        if mask & 8:
            result["protocol_result"] = {"kind": "model-protocol.v1"}
        c.execute(update(runs).where(runs.c.id == rid).values(
            status="RUNNING", lease_until=0, fence=1, context=context, result=result))
        if mask & 1:
            c.execute(insert(protocol_jobs).values(run_id=rid, project_id=env[5],
                principal_id=env[3], runtime_id="synthetic-marker-only", kind="source",
                accepted_snapshot={}, fingerprint=fingerprint({}), created_at=0))
        if mask & 2:
            env[0].event(c, rid, "PROTOCOL_ACCEPTED", {})
        if mask & 16:
            snapshot = copy.deepcopy(c.execute(select(run_contracts.c.snapshot).where(
                run_contracts.c.run_id == rid)).scalar_one())
            snapshot["goal"]["constraints"] = [NAMESPACE]
            c.execute(update(run_contracts).where(run_contracts.c.run_id == rid).values(
                snapshot=snapshot, fingerprint=fingerprint(snapshot)))
        before_events = c.execute(select(events.c.id).where(events.c.run_id == rid)).scalars().all()
    assert is_protocol_job(env[0], rid)
    assert env[0].claim("must-not-downgrade", 30) is None
    with env[0].tx() as c:
        current = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert current["status"] == "WAITING_RESOURCE" and current["fence"] == 2
        assert current["context"] == context and current["result"] == result
        assert c.execute(select(func.count()).select_from(attempts)).scalar_one() == 0
        added = c.execute(select(events.c.kind).where(
            events.c.run_id == rid, events.c.id.not_in(before_events))).scalars().all()
        assert added == ["PROTOCOL_RECOVERY_STATE"]


@pytest.mark.parametrize("field,value", [
    ("context", None), ("context", [NAMESPACE]), ("context", NAMESPACE),
    ("context", {"kind": [NAMESPACE]}), ("context", {"kind": {"name": NAMESPACE}}),
    ("context", {"kind": NAMESPACE + ".suffix"}),
    ("result", {"protocol_result": [{"kind": "model-protocol.v1"}]}),
    ("result", {"protocol_result": {"kind": ["model-protocol.v1"]}}),
    ("result", [{"protocol_result": {"kind": "model-protocol.v1"}}]),
    ("constraints", NAMESPACE), ("constraints", {"name": NAMESPACE}),
    ("constraints", None), ("constraints", [[NAMESPACE]]),
    ("constraints", [NAMESPACE + ".suffix"]),
    ("snapshot", [NAMESPACE]), ("goal", [{"constraints": [NAMESPACE]}]),
    ("fingerprint", "invalid"),
])
def test_marker_projection_retains_exact_types_and_contract_seal(env, field, value):
    rid = ordinary(env, "lookalike")
    with env[0].tx() as c:
        if field in {"context", "result"}:
            c.execute(update(runs).where(runs.c.id == rid).values(**{field: value}))
        else:
            snapshot = copy.deepcopy(c.execute(select(run_contracts.c.snapshot).where(
                run_contracts.c.run_id == rid)).scalar_one())
            snapshot["goal"]["constraints"] = [NAMESPACE]
            if field == "constraints":
                snapshot["goal"]["constraints"] = value
            elif field == "snapshot":
                snapshot = value
            elif field == "goal":
                snapshot["goal"] = value
            c.execute(update(run_contracts).where(run_contracts.c.run_id == rid).values(
                snapshot=snapshot, fingerprint=value if field == "fingerprint" else fingerprint(snapshot)))
    assert not is_protocol_job(env[0], rid)


def test_candidate_oracle_requires_scope_and_batches_without_silent_cap(env):
    rid = ordinary(env, "bounded-oracle")
    with env[0].tx() as c:
        env[0].event(c, rid, "PROTOCOL_ACCEPTED", {})
        with pytest.raises(ValueError):
            protocol_run_ids(c)
        with pytest.raises(ValueError):
            protocol_run_ids(c, rid, candidates=[rid])
        assert protocol_run_ids(c, candidates=[]) == set()
        assert protocol_run_ids(c, candidates=["absent"] * 300) == set()
        assert protocol_run_ids(c, candidates=["absent-" + str(i) for i in range(600)] + [rid]) == {rid}


def test_pool_oracle_returns_ids_only_for_actual_attempt_candidates(env, tmp_path):
    unrelated, before = historical(env)
    eligible = ordinary(env, "ordinary-attempt-candidate")
    worker = Worker(env[0], env[1], NoModel())
    owned = env[0].claim(worker.id, 30)
    assert owned["id"] == eligible
    # Real reserve only, no provider dispatch; ordinary F1 Attempt remains unclassified.
    worker.reserve(eligible, owned["fence"], owned["context"])
    with env[0].tx() as c:
        c.execute(insert(attempts).values(id="synthetic-orphan-with-null-run", run_id=None))
    returned_columns = []

    def columns(conn, cursor, sql, params, context, many):
        if cursor.description:
            returned_columns.append({"sql": sql, "columns": [item[0] for item in cursor.description],
                                     "parameters": repr(params)})

    event.listen(env[0].engine, "after_cursor_execute", columns)
    try:
        with PrivateReadBarrier(env[0], {unrelated}) as barrier:
            with env[0].engine.connect() as c:
                assert _protocol_attempts(c) == []
            assert not barrier.blocked
            # Candidate marker predicates necessarily evaluate their JSON; only
            # namespace membership IDs may be returned to the caller.
            classified = [s for s in returned_columns if 'FROM "private_read_runs"' in s["sql"]]
            assert len(classified) == 1 and classified[0]["columns"] == ["id"]
            assert eligible in classified[0]["parameters"] and unrelated not in classified[0]["parameters"]
            # json_each may inspect candidate constraints; no snapshot may be
            # projected for this ordinary non-protocol frozen contract.
            contracts = [s for s in returned_columns if 'FROM "private_read_run_contracts"' in s["sql"]]
            assert len(contracts) == 1
            (tmp_path / "pool-marker-projection.json").write_text(json.dumps(dict(
                candidate_run=eligible, unrelated_run=unrelated, result=[],
                returned_columns=returned_columns, evaluated=barrier.evaluated,
                blocked=barrier.blocked), indent=2))
    finally:
        event.remove(env[0].engine, "after_cursor_execute", columns)
    with env[0].tx() as c:
        assert dict(c.execute(select(runs).where(runs.c.id == unrelated)).mappings().one()) == before


@pytest.mark.parametrize("field,raw", [
    ("context", '{"kind":"plain","kind":"protocol_jobs.v1"}'),
    ("result", '{"protocol_result":{"kind":"plain"},"protocol_result":{"kind":"model-protocol.v1"}}'),
    ("result", '{"protocol_result":{"kind":"plain","kind":"model-protocol.v1"}}'),
    ("snapshot", '{"goal":{"constraints":[],"constraints":["protocol_jobs.v1"]}}'),
    ("snapshot", '{"goal":{"constraints":[]},"goal":{"constraints":["protocol_jobs.v1"]}}'),
])
def test_duplicate_key_last_protocol_marker_never_downgrades(env, field, raw):
    rid = ordinary(env, "duplicate-key-" + field)
    with env[0].tx() as c:
        c.execute(update(runs).where(runs.c.id == rid).values(status="RUNNING", lease_until=0, fence=1))
        if field == "snapshot":
            c.exec_driver_sql("UPDATE run_contracts SET snapshot=?, fingerprint=? WHERE run_id=?",
                             (raw, fingerprint(json.loads(raw)), rid))
        else:
            c.exec_driver_sql("UPDATE runs SET " + field + "=? WHERE id=?", (raw, rid))
    assert is_protocol_job(env[0], rid)
    assert env[0].claim("duplicate-marker-must-stop", 30) is None
    with env[0].tx() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one() == "WAITING_RESOURCE"


def test_contract_marker_candidate_is_rechecked_after_duplicate_key_decoding(env):
    rid = ordinary(env, "contract-last-ordinary")
    raw = '{"goal":{"constraints":["protocol_jobs.v1"],"constraints":[]}}'
    with env[0].tx() as c:
        c.exec_driver_sql("UPDATE run_contracts SET snapshot=?, fingerprint=? WHERE run_id=?",
                         (raw, fingerprint(json.loads(raw)), rid))
    assert not is_protocol_job(env[0], rid)


def test_data_free_actual_worker_and_cold_typed_inputs_keep_all_old_private_rows(env, tmp_path):
    rel, old_resource, group = source(env)
    reply = env[2].get('/api/internal/instances/' + next(
        entry['instance_id'] for entry in group['entries'] if entry['release_id'] == rel['id']))
    assert reply.status_code == 200, reply.text
    old_instance = reply.json()
    seeded, _ = enqueue(env, old_instance, rel, column="quantity", key="old-typed-history")
    work(env, seeded)
    obj, _ = authorize(env, rel)
    aid, target_resource = register(env, FREE)
    with env[0].tx() as c:
        c.execute(update(grants).where(grants.c.resource_id == old_resource).values(revoked=True))
    # Keep the original CSV and every old Run/Operation/contract. Revoke only.
    body = binding(env, aid, target_resource, obj=obj,
                   column="net", key="current-target-after-revoke")
    path = f"/api/internal/csv-logics/{obj['id']}/material-plans"
    from sim2act.db import app_drafts, meta, operation_intents

    tables = (runs, resources, operations, operation_intents, run_contracts, app_drafts,
              *[t for t in meta.sorted_tables if t.name.startswith("internal_")])
    with env[0].tx() as c:
        before = {t.name: copy.deepcopy([dict(r) for r in c.execute(select(t)).mappings()]) for t in tables}
    old_runs = {row['id'] for row in before['runs']}
    old_resources = {row['id'] for row in before['resources']} - {body['expected_resource_id']}
    with PrivateReadBarrier(env[0], old_runs, old_resources) as negative:
        for table, key, column in ((operations, "id", "receipt"),
                                   (operation_intents, "operation_id", "request")):
            oid = before[table.name][0][key]
            with pytest.raises(DatabaseError):
                with env[0].engine.connect() as c:
                    c.execute(select(table.c[column]).where(table.c[key] == oid)).all()
        assert {cell["table"] for cell in negative.blocked} == {"operations", "operation_intents"}
        (tmp_path / 'actual-old-operation-negative.json').write_text(json.dumps(dict(
            blocked=negative.blocked, sql=negative.statements), indent=2))
    barrier = PrivateReadBarrier(env[0], old_runs, old_resources)
    cold_store = None
    with barrier:
        try:
            value, accepted, _, _ = accept(env, path, body, key="guarded-target")
            job = work(env, accepted)
            proof = env[2].get('/api/csv-dag/runs/' + job['id']).json()
            assert proof['status'] == 'SUCCEEDED'
            output = proof['result']['output_by_step']['report']
            assert output['resource_id'] == body['expected_resource_id']
            assert Fraction(output['sum']) == Fraction('8.75') and output['count'] == 3
            approval = env[2].post(f"/api/csv-dag/runs/{job['id']}/release-approvals", json=dict(
                expected_plan_fingerprint=value['plan']['plan_fingerprint'], request_key="guarded-release"))
            assert approval.status_code == 201, approval.text
            committed = env[2].post('/api/internal/approvals/' + approval.json()['id'] + '/commit',
                                   json=dict(fingerprint=approval.json()['fingerprint']))
            assert committed.status_code == 200, committed.text
            new = committed.json()
            instance = create(env, new, key="guarded-instance")
            cold_store = Store(env[1].database_url, test_only=True)
            barrier.attach(cold_store)
            cold = TestClient(create_app(cold_store, env[1]))
            cold.headers['Authorization'] = 'Bearer synthetic-test-A'
            try:
                for column in ('net', 'units'):
                    reply = cold.post(f"/api/internal/instances/{instance['id']}/runs", json=dict(
                        expected_revision=instance['revision'], expected_release_fingerprint=new['fingerprint'],
                        input={'column': column}, request_key='guarded-cold-' + column))
                    assert reply.status_code == 202, reply.text
                    work(env, reply.json())
                detail = cold.get('/api/internal/instances/' + instance['id'])
                assert detail.status_code == 200, detail.text
                got = detail.json()
                assert got['data_version'] == 2
                assert {Fraction(r['data']['result']['sum']) for r in got['data']} == {Fraction('8.75'), Fraction(13)}
                assert new['snapshot']['execution_source']['default_column'] == 'net'
            finally:
                cold.close()
            assert not barrier.blocked
            (tmp_path / 'actual-target-proof.json').write_text(json.dumps(dict(
                target_proof=proof, target_release=new, cold_instance=got), indent=2))
        finally:
            (tmp_path / 'cell-barrier.json').write_text(json.dumps(dict(
                protected_old_runs=sorted(old_runs), protected_old_resources=sorted(old_resources),
                blocked=barrier.blocked, evaluated=barrier.evaluated, sql=barrier.statements), indent=2))
    if cold_store is not None:
        cold_store.engine.dispose()
    with env[0].tx() as c:
        after = {t.name: [dict(r) for r in c.execute(select(t)).mappings()] for t in tables}
    for name in before:
        assert all(row in after[name] for row in before[name]), name
    # The revoked old CSV still physically exists with exactly its old bytes/hash.
    assert next(row for row in before['resources'] if row['id'] == old_resource) in after['resources']

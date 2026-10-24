"""Real SQLite metadata reads; no Store/Worker/transport/model or business writes."""

import copy

import pytest
from sqlalchemy import create_engine, delete, event, literal, select, update
from sqlalchemy.dialects import postgresql, sqlite

from sim2act import natural_live_admission as gate
from sim2act import pa_trial_dispatch as trial
from sim2act.db import delivery_graph_requests as rows
from sim2act.db import events
from sim2act.errors import DomainError
from sim2act.pa_trial_dispatch import REQUEST


def legacy_metadata(c, run, aid, kind, *, _guard=None):
    """Late failure accounting reads digest/identity projections, never body_b64."""
    selected = gate._trial_result(c.execute(select(rows.c.kind, rows.c.snapshot['request']['trial']['contract_fingerprint'].as_string().label('trial_fp'), rows.c.snapshot['request']['attempt_id'].as_string().label('key_attempt'), rows.c.snapshot['request']['family'].as_string().label('key_family'), rows.c.snapshot['request']['wire_sha256'].as_string().label('wire_sha256'), *[rows.c.snapshot['response'][k].as_string().label(k) for k in ('run_id', 'attempt_id', 'principal_id', 'project_id', 'runtime_id', 'phase', 'sha256', 'canonical_sha256', 'omission')], rows.c.snapshot['response']['byte_count'].as_integer().label('byte_count'), rows.c.snapshot['response']['received_complete'].as_boolean().label('complete')).where(rows.c.principal_id == run['principal_id'], rows.c.app_id == run['id'], rows.c.request_key == aid, rows.c.kind.in_([kind, kind + '_seal']))), _guard)
    values = gate._trial_result([dict(r) for r in gate._trial_result(selected.mappings(), _guard)], _guard)
    if not values:
        return None
    gate.require(len(values) == 2 and {r.pop('kind') for r in values} == {kind, kind + '_seal'})
    gate.require(values[0] == values[1])
    value = values[0]
    gate.require(value['phase'] == ('RESERVED_REQUEST' if kind == REQUEST else 'RECEIVED_DECODED_BODY'))
    gate.require(value['run_id'] == run['id'] and value['attempt_id'] == aid and (value['key_attempt'] == aid) and (value['key_family'] == kind) and all((value[k] == run[k] for k in ('principal_id', 'project_id', 'runtime_id'))))
    anchors = gate._trial_result(gate._trial_result(gate._trial_result(c.execute(select(events.c.data).where(events.c.run_id == run['id'], events.c.kind == 'PA_TRIAL_BODY', events.c.data['attempt_id'].as_string() == aid, events.c.data['family'].as_string() == kind)), _guard).scalars(), _guard).all(), _guard)
    gate.require(len(anchors) == 1 and all((anchors[0].get(k) == value[field] for k, field in (('decoded_sha256', 'sha256'), ('canonical_sha256', 'canonical_sha256'), ('byte_count', 'byte_count'), ('complete', 'complete'), ('omission', 'omission')))))
    return value


def seed(c, run=None, aid="attempt", kind=trial.RESPONSE):
    run = run or dict(id="run", principal_id="user", project_id="project", runtime_id="runtime")
    request = dict(trial=dict(contract_fingerprint="a" * 64), attempt_id=aid,
                   family=kind, wire_sha256="b" * 64)
    response = dict(**{k: run[k] for k in ("principal_id", "project_id", "runtime_id")},
        run_id=run["id"], attempt_id=aid, sha256="c" * 64, canonical_sha256="d" * 64,
        phase="RESERVED_REQUEST" if kind == trial.REQUEST else "RECEIVED_DECODED_BODY",
        omission="NONE", byte_count=12, received_complete=True, body_b64="not projected")
    for family in (kind, kind + "_seal"):
        c.execute(rows.insert().values(app_id=run["id"], principal_id=run["principal_id"],
            kind=family, request_key=aid, request_fingerprint="e" * 64,
            fingerprint="f" * 64, snapshot=dict(request=request, response=response)))
    anchor = dict(attempt_id=aid, family=kind, decoded_sha256=response["sha256"],
        canonical_sha256=response["canonical_sha256"], byte_count=12,
        complete=True, omission="NONE")
    c.execute(events.insert().values(id=run["id"] + aid + kind, run_id=run["id"],
                                    kind="PA_TRIAL_BODY", data=anchor))
    return run


@pytest.fixture
def connection():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as c:
            rows.create(c)
            events.create(c)
            yield c
    finally:
        engine.dispose()


def exact(value):
    if type(value) is dict:
        return (dict, tuple((key, exact(item)) for key, item in value.items()))
    return (type(value), value)


def observe(c, implementation, run, *, aid="attempt", kind=trial.RESPONSE, hook=None):
    queries, guards = [], []

    def sql(_c, _cursor, statement, parameters, _context, _many):
        queries.append((statement, parameters))

    def guard():
        guards.append(len(queries))
        if hook is not None:
            hook(len(guards))

    event.listen(c, "before_cursor_execute", sql)
    try:
        try:
            result = ("OK", exact(implementation(c, run, aid, kind, _guard=guard)))
        except (DomainError, RuntimeError, KeyError, TypeError) as error:
            result = ("ERROR", type(error), getattr(error, "code", None), str(error))
        return result, queries, guards
    finally:
        event.remove(c, "before_cursor_execute", sql)


@pytest.mark.parametrize("case", ["request", "response", "empty", "single", "seal-drift",
    "wrong-phase", "wrong-owner", "wrong-anchor", "duplicate-anchor", "no-anchor"])
def test_original_metadata_results_sql_and_guards(connection, case):
    c = connection
    kind = trial.REQUEST if case == "request" else trial.RESPONSE
    run = seed(c, kind=kind)
    if case in ("empty", "single"):
        statement = delete(rows)
        if case == "single":
            statement = statement.where(rows.c.kind == kind + "_seal")
        c.execute(statement)
    if case in ("seal-drift", "wrong-phase", "wrong-owner"):
        for row in c.execute(select(rows)).mappings():
            data = copy.deepcopy(row["snapshot"])
            if case == "seal-drift" and row["kind"] == kind + "_seal":
                data["response"]["byte_count"] += 1
            if case == "wrong-phase":
                data["response"]["phase"] = "UNKNOWN"
            if case == "wrong-owner":
                data["response"]["principal_id"] = "another-user"
            c.execute(update(rows).where(rows.c.kind == row["kind"]).values(snapshot=data))
    if case == "wrong-anchor":
        anchor = dict(c.execute(select(events.c.data)).scalar_one(), byte_count=99)
        c.execute(update(events).values(data=anchor))
    if case == "duplicate-anchor":
        anchor = c.execute(select(events)).mappings().one()
        c.execute(events.insert().values(**dict(anchor, id="duplicate")))
    if case == "no-anchor":
        c.execute(delete(events))
    old = observe(c, legacy_metadata, run, kind=kind)
    new = observe(c, trial._metadata, run, kind=kind)
    assert old == new
    assert old[0][0] == ("OK" if case in ("request", "response", "empty") else "ERROR")
    if case in ("request", "response"):
        assert len(old[1]) == 2
        assert len(old[0][1][1]) == 15  # kind was validated and removed
        assert "body_b64" not in str(old[0])


def test_identity_isolation_and_original_nonexact_input_semantics(connection):
    c = connection
    run = seed(c)
    for field in ("principal_id", "id"):
        other = dict(run, **{field: "other"})
        seed(c, other, aid=field)
        for values in (other, dict(run, **{field: None})):
            assert observe(c, legacy_metadata, values) == observe(c, trial._metadata, values)
    class Text(str):
        pass
    for aid, kind in [(None, trial.RESPONSE), (Text("attempt"), Text(trial.RESPONSE)),
                      ("' OR 1=1 --", trial.RESPONSE), ("attempt", None)]:
        assert observe(c, legacy_metadata, run, aid=aid, kind=kind) == observe(
            c, trial._metadata, run, aid=aid, kind=kind)
    mapping = c.execute(select(*(literal(value).label(key) for key, value in run.items()))).mappings().one()
    assert observe(c, legacy_metadata, mapping) == observe(c, trial._metadata, mapping)


@pytest.mark.parametrize("mutation", ["run", "anchor", "delete", "guard-error"])
def test_midread_mutation_original_rejection_and_exception(connection, mutation):
    c = connection
    run = seed(c)
    outcomes = []
    for implementation in (legacy_metadata, trial._metadata):
        local = dict(run)
        with c.begin_nested() as savepoint:
            def change(index, local=local):
                if index != 3:
                    return
                if mutation == "run":
                    local["project_id"] = "mutated"
                elif mutation == "anchor":
                    c.execute(update(events).values(data=dict(attempt_id="attempt", family=trial.RESPONSE)))
                elif mutation == "delete":
                    c.execute(delete(events))
                else:
                    raise RuntimeError("original-guard-error")
            outcomes.append(observe(c, implementation, local, hook=change))
            savepoint.rollback()
    assert outcomes[0] == outcomes[1]
    assert outcomes[0][0][0] == "ERROR"


def test_fresh_projection_after_writes_and_rollback(connection):
    c = connection
    run = seed(c)
    original = trial._metadata(c, run, "attempt", trial.RESPONSE)
    with c.begin_nested() as savepoint:
        for row in c.execute(select(rows)).mappings():
            snapshot = copy.deepcopy(row["snapshot"])
            snapshot["response"]["byte_count"] = 19
            c.execute(update(rows).where(rows.c.kind == row["kind"]).values(snapshot=snapshot))
        anchor = dict(c.execute(select(events.c.data)).scalar_one(), byte_count=19)
        c.execute(update(events).values(data=anchor))
        current = trial._metadata(c, run, "attempt", trial.RESPONSE)
        assert current == legacy_metadata(c, run, "attempt", trial.RESPONSE)
        assert type(current["complete"]) is bool and type(current["byte_count"]) is int
        assert current["byte_count"] == 19 and original["byte_count"] == 12
        savepoint.rollback()
    assert trial._metadata(c, run, "attempt", trial.RESPONSE) == original


def test_sqlite_and_postgres_projection_structure_and_parameters(connection):
    run = seed(connection)
    statements = []
    def capture(_c, clause, _many, _params, _options):
        statements.append(clause)
    event.listen(connection, "before_execute", capture)
    try:
        legacy_metadata(connection, run, "attempt", trial.RESPONSE)
        trial._metadata(connection, run, "attempt", trial.RESPONSE)
    finally:
        event.remove(connection, "before_execute", capture)
    assert len(statements) == 4 and len(trial._JOURNAL_METADATA_PROJECTION.selected_columns) == 16
    for dialect in (sqlite.dialect(), postgresql.dialect()):
        for before, after in zip(statements[:2], statements[2:], strict=True):
            old, new = before.compile(dialect=dialect), after.compile(dialect=dialect)
            assert str(old) == str(new) and old.params == new.params

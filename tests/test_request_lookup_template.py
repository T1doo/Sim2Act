"""Fresh full SQLite reads; no Worker, admission, Mock transport or model."""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, delete, event, select, update

from sim2act import delivery_graph_apps as graph
from sim2act import text_logic_reuse as logic
from sim2act.contracts import Strict
from sim2act.db import delivery_graph_requests as requests
from sim2act.db import fingerprint
from sim2act.errors import DomainError


def legacy_lookup(c, user, aid, kind, key):
    return c.execute(select(requests).where(
        requests.c.app_id == aid, requests.c.principal_id == user,
        requests.c.kind == kind, requests.c.request_key == key,
    )).mappings().first()


class Body(Strict):
    value: int


@pytest.fixture
def connection():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as c:
            requests.create(c)
            yield c
    finally:
        engine.dispose()


def test_full_row_parameter_isolation_and_nonstring_fallback(connection):
    c = connection
    for user, aid, kind, key in [
        ("u", "a", "k", "q"), ("other", "a", "k", "q"),
        ("u", "other", "k", "q"), ("u", "a", "other", "q"),
        ("u", "a", "k", "other"), ("u", "a", "k", "' OR 1=1 --"),
    ]:
        graph.remember(c, user, aid, kind, key, Body(value=1),
                       {"scope": [user, aid, kind, key], "nested": [None, True, "中文"]})
    observed, supplied = [], []

    def before_execute(_c, clause, _many, _parameters, _options):
        supplied.append(clause)

    def observe(_c, _cursor, statement, parameters, context, _many):
        observed.append((statement, parameters, context.compiled.statement))

    class Text(str):
        pass

    values = [
        ("u", "a", "k", "q"), ("other", "a", "k", "q"),
        ("u", "other", "k", "q"), ("u", "a", "other", "q"),
        ("u", "a", "k", "other"), ("u", "a", "k", "' OR 1=1 --"),
        ("missing", "a", "k", "q"),
    ]
    for position in range(4):
        for value in (None, Text(("u", "a", "k", "q")[position])):
            args = ["u", "a", "k", "q"]
            args[position] = value
            values.append(tuple(args))
    event.listen(c, "before_cursor_execute", observe)
    event.listen(c, "before_execute", before_execute)
    try:
        for args in values:
            before = len(observed)
            old, new = legacy_lookup(c, *args), graph.lookup(c, *args)
            assert len(observed) == before + 2
            assert observed[-2][:2] == observed[-1][:2]
            assert (supplied[-1] is graph._REQUEST_LOOKUP_QUERY) == all(type(v) is str for v in args)
            assert (None if old is None else dict(old)) == (None if new is None else dict(new))
            if new is not None:
                assert type(new) is type(old) and new is not old
                assert set(new) == set(requests.c.keys())
    finally:
        event.remove(c, "before_cursor_execute", observe)
        event.remove(c, "before_execute", before_execute)


def test_fresh_full_rows_after_write_delete_and_rollback(connection):
    c = connection
    graph.remember(c, "u", "a", "k", "q", Body(value=1), {"value": "original"})
    original = graph.lookup(c, "u", "a", "k", "q")
    with c.begin_nested() as savepoint:
        value = {"request": {"value": 2}, "response": {"value": "new", "extra": [False, None]}}
        c.execute(update(requests).values(snapshot=value, fingerprint=fingerprint(value)))
        fresh = graph.lookup(c, "u", "a", "k", "q")
        assert dict(fresh) == dict(legacy_lookup(c, "u", "a", "k", "q"))
        assert fresh["snapshot"] == value
        assert original["snapshot"]["response"] == {"value": "original"}
        savepoint.rollback()
    assert dict(graph.lookup(c, "u", "a", "k", "q")) == dict(original)
    c.execute(delete(requests))
    assert graph.lookup(c, "u", "a", "k", "q") is None
    graph.remember(c, "u", "a", "k", "q", Body(value=3), {"value": "reinserted"})
    assert graph.lookup(c, "u", "a", "k", "q")["snapshot"]["response"] == {"value": "reinserted"}


def test_original_pair_seals_errors_order_and_intervening_write(connection):
    c = connection
    candidate = graph.lookup
    for case in ("valid", "missing", "bad-hash", "different-seal", "request-hash", "between"):
        kind = "pair-" + case
        logic.remember(c, "u", "a", kind, "q", Body(value=1), {"answer": [True, None, "原文"]})
        seal = (requests.c.kind == kind + "_seal")
        if case == "missing":
            c.execute(delete(requests).where(seal))
        elif case == "bad-hash":
            c.execute(update(requests).where(seal).values(fingerprint="bad"))
        elif case == "different-seal":
            value = {"request": {"value": 1}, "response": {"answer": "different"}}
            c.execute(update(requests).where(seal).values(snapshot=value, fingerprint=fingerprint(value)))
        elif case == "request-hash":
            c.execute(update(requests).where(seal).values(request_fingerprint="bad"))
        outcomes = []
        for implementation in (legacy_lookup, candidate):
            calls = []
            with c.begin_nested() as savepoint:
                def lookup(*args, _calls=calls, _impl=implementation, _case=case, _seal=seal):
                    _calls.append(args[1:])
                    row = _impl(*args)
                    if _case == "between" and len(_calls) == 1:
                        c.execute(delete(requests).where(_seal))
                    return row

                with patch.object(graph, "lookup", lookup):
                    try:
                        body, response = logic.pair(c, "u", "a", kind, "q", Body)
                        outcome = ("OK", body.model_dump(), response)
                    except DomainError as error:
                        outcome = ("ERROR", error.code, error.message)
                outcomes.append(outcome)
                assert calls == [("u", "a", kind, "q"), ("u", "a", kind + "_seal", "q")]
                savepoint.rollback()
        assert outcomes[0] == outcomes[1]
        assert outcomes[0][0] == ("OK" if case == "valid" else "ERROR")

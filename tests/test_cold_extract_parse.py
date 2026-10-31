"""Synthetic persisted pair error ownership; zero model/worker execution."""

from contextlib import contextmanager
import copy
import sys

import pytest
from sqlalchemy import event, insert
from test_cold_binding_fact_leaves import graph_origin as graph_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import pb_natural_specs as pb
from sim2act import natural_spec_runtime as runtime
from sim2act.db import delivery_graph_requests, fingerprint, new_id, task_extractions
from sim2act.errors import DomainError


@pytest.fixture
def malformed_extract(graph_origin):
    # Exercise the actual persisted-pair boundary with the complete default
    # code witness intact. The former fixture replaced unrelated origin and
    # scope producers before Graph creation and never reached this boundary.
    f = graph_origin
    key, rid = "synthetic-malformed-persisted-extract", new_id("run")
    request = dict(review=dict(source_run_id=rid,
        expected_source_proof_fingerprint="a" * 64,
        expected_source_recipe_fingerprint=fingerprint(f.draft["candidate"]["spec_recipe"]),
        card_id=f.origin[3]["card_id"], expected_goal_version=f.origin[3]["version"],
        expected_goal_fingerprint=f.origin[3]["fingerprint"],
        expected_source_hash=f.origin[2]["hash"],
        recipe=copy.deepcopy(f.draft["candidate"]["spec_recipe"]),
        name="Synthetic extraction", request_key=key),
        expected_review_fingerprint="b" * 64, consent=pb.CONSENT,
        artifact_write_consent=pb.natural.CONSENT)
    # Only a required stored field is removed. Both independently stored seals
    # remain identical, with correct complete snapshot/request fingerprints.
    pb.ExtractInput.model_validate(request)
    del request["expected_review_fingerprint"]
    snapshot = dict(request=request, response={})
    with f.store.tx() as c:
        c.execute(insert(task_extractions).values(task_id=rid, principal_id=f.user,
            request_key=key, request_fingerprint=fingerprint(request),
            app_id=f.draft["id"], snapshot={}))
        for kind in (pb.EXTRACT, pb.EXTRACT + "_seal"):
            c.execute(insert(delivery_graph_requests).values(app_id=f.draft["id"],
                principal_id=f.user, kind=kind, request_key=key,
                request_fingerprint=fingerprint(request), snapshot=snapshot,
                fingerprint=fingerprint(snapshot)))
    f.extract_key = key
    return f


@contextmanager
def observe_entries(callback, *codes):
    monitor = sys.monitoring
    slot = next(i for i in (3, 5, 4) if monitor.get_tool(i) is None)
    monitor.use_tool_id(slot, "Persisted-pair error boundary observation")
    try:
        monitor.register_callback(slot, monitor.events.PY_START, callback)
        for code in codes:
            monitor.set_local_events(slot, code, monitor.events.PY_START)
        yield
    finally:
        for code in codes:
            monitor.set_local_events(slot, code, 0)
        monitor.register_callback(slot, monitor.events.PY_START, None)
        monitor.free_tool_id(slot)


def test_owned_malformed_extract_pair_matches_old_controlled_error(malformed_extract):
    f, parsed = malformed_extract, []
    parser_code = pb.ExtractInput.model_validate.__func__.__code__
    with f.store.tx() as c:
        with pytest.raises(DomainError) as old:
            # Use the same original controlled boundary as pb.verify, without
            # replacing its unrelated scope authorization just to reach pair.
            pb.controlled(pb.pair)(c, f.user, f.draft['id'], pb.EXTRACT, f.extract_key, pb.ExtractInput)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as strict, observe_entries(
                lambda *args: parsed.append('owned-parse'), parser_code):
            with read_scope(f, c) as guard:
                pb._cold_extract_pair(f.store, c, f.user, f.draft['id'], f.extract_key, guard)
        assert not guard.active
    assert strict.value.public() == old.value.public()
    assert strict.value.code == "VERSION_CONFLICT"
    assert strict.value.message == "Malformed persisted DeliveryGraph binding"
    assert parsed == ["owned-parse"]


def test_guard_valueerror_is_original_and_stops_before_second_lookup_or_parse(malformed_extract):
    f, lookups, parsed = malformed_extract, [], []
    changed = [False]
    original = ValueError("synthetic original read-pin callback")

    def after_sql(c, cursor, statement, params, context, executemany):
        if "FROM delivery_graph_requests" in statement:
            lookups.append(statement)
            changed[0] = True

    guard_code = runtime._ColdGraphRead.check.__code__
    parser_code = pb.ExtractInput.model_validate.__func__.__code__

    def entered(code, offset):
        if code is parser_code:
            parsed.append('unexpected-parse')
            pytest.fail("Owned parse ran after the first lookup's guard failure")
        if changed[0]:
            raise original

    event.listen(f.store.engine, "after_cursor_execute", after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(ValueError) as caught:
                with read_scope(f, c) as guard, observe_entries(entered, guard_code, parser_code):
                    pb._cold_extract_pair(f.store, c, f.user, f.draft['id'], f.extract_key, guard)
        assert caught.value is original and not guard.active
        assert len(lookups) == 1 and parsed == []
    finally:
        event.remove(f.store.engine, "after_cursor_execute", after_sql)

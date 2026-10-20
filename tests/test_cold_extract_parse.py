"""Synthetic persisted pair error ownership; zero model/worker execution."""

import copy

import pytest
from sqlalchemy import event, insert
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act.db import delivery_graph_requests, fingerprint, new_id, task_extractions
from sim2act.errors import DomainError


@pytest.fixture
def malformed_extract(local_origin, monkeypatch):
    f = local_origin
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
    monkeypatch.setattr(spec, "scope_gate", lambda *a, **k: True)
    f.extract_key = key
    return f


def test_owned_malformed_extract_pair_matches_old_controlled_error(malformed_extract, monkeypatch):
    f, parsed = malformed_extract, []
    original_parser = pb._persisted_extract_input

    def parser(value):
        parsed.append("owned-parse")
        return original_parser(value)

    monkeypatch.setattr(pb, "_persisted_extract_input", parser)
    with f.store.tx() as c:
        with pytest.raises(DomainError) as old:
            pb.verify(f.store, c, f.user, f.draft, f.limits)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as strict:
            with read_scope(f, c) as guard:
                pb._cold_verify_prefix(f.store, c, f.user, f.draft, f.limits, guard, "cold")
        assert not guard.active
    assert strict.value.public() == old.value.public()
    assert strict.value.code == "VERSION_CONFLICT"
    assert strict.value.message == "Malformed persisted DeliveryGraph binding"
    assert parsed == ["owned-parse"]


def test_guard_valueerror_is_original_and_stops_before_second_lookup_or_parse(
        malformed_extract, monkeypatch):
    f, lookups, parsed = malformed_extract, [], []
    changed = [False]
    original = ValueError("synthetic original read-pin callback")

    def after_sql(c, cursor, statement, params, context, executemany):
        if "FROM delivery_graph_requests" in statement:
            lookups.append(statement)
            changed[0] = True

    def parser(value):
        parsed.append(value)
        pytest.fail("Owned parse ran after the first lookup's guard failure")

    monkeypatch.setattr(pb, "_persisted_extract_input", parser)
    event.listen(f.store.engine, "after_cursor_execute", after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(ValueError) as caught:
                with read_scope(f, c) as guard:
                    check = guard.check

                    def checked(store, connection):
                        if changed[0]:
                            raise original
                        return check(store, connection)

                    monkeypatch.setattr(guard, "check", checked)
                    pb._cold_verify_prefix(f.store, c, f.user, f.draft, f.limits, guard, "cold")
        assert caught.value is original and not guard.active
        assert len(lookups) == 1 and parsed == []
    finally:
        event.remove(f.store.engine, "after_cursor_execute", after_sql)

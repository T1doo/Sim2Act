"""Isolated real SQLite/pairs/Grants; no full PB ancestry, executor or model.

The existing exact synthetic read-pin fixture is reused. Its own_project stub
is restored. Only the job gate's unrelated app-family proof is a stand-in;
use.scope_gate, job header/association SQL, paired seals and authority are real.
This file is an unexecuted external candidate for the root writer to apply.
"""

import copy
import time

import pytest
from sqlalchemy import event, insert, select, update
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import delivery_graph_apps as graph
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act import text_logic_reuse
from sim2act.contracts import GoalCardRunSource
from sim2act.db import (
    Store,
    app_drafts,
    delivery_graph_requests,
    fingerprint,
    internal_app_runs,
    internal_instances,
    internal_run_bindings,
    new_id,
    runs,
)
from sim2act.errors import DomainError
from sim2act.text_workflows import RunScopeInput


@pytest.fixture
def scope_rows(local_origin, env, monkeypatch):
    f = local_origin
    _, _, _, _, _, pid, resource = env
    monkeypatch.setattr(f.store, "own_project", Store.own_project.__get__(f.store, Store))
    with f.store.tx() as c:
        runtime = f.store.own_project(c, f.user, pid)["runtime_id"]
    f.scope_rid, f.scope_aid = new_id("run"), new_id("app")
    iid, arid, release_id = new_id("instance"), new_id("apprun"), new_id("release")
    candidate = copy.deepcopy(f.draft["candidate"])
    candidate["spec_task"] = dict(kind=pb.KIND)  # Scope classification only.
    f.audit_header = dict(principal_id=f.user, project_id=pid, runtime_id=runtime)
    f.job_header = dict(**f.audit_header, request_key="internal:" + arid)
    f.scope_meta = RunScopeInput(app_id=f.scope_aid, principal_id=f.user, project_id=pid,
        runtime_id=runtime, resource_id=resource, run_id=f.scope_rid, instance_id=iid,
        app_run_id=arid, release_id=release_id)
    request = use.ReviewInput(expected_revision=1, expected_release_fingerprint="a" * 64,
        expected_app_fingerprint=fingerprint(candidate),
        expected_recipe_fingerprint=fingerprint(candidate["spec_recipe"]),
        resource_id=resource, card_id=new_id("goal"), expected_goal_version=1,
        expected_goal_fingerprint="b" * 64, expected_source_hash="c" * 64,
        request_key="synthetic-scope-use")
    f.commit = use.CommitInput(review=request, expected_review_fingerprint="d" * 64,
        consent=use.CONSENT)
    f.scope_snapshot = dict(instance_id=iid, app_run_id=arid, run_id=f.scope_rid,
        expected_revision=1, runtime_id=runtime, pb_use=f.commit.model_dump())
    f.scope_release = dict(id=release_id, fingerprint="a" * 64,
        snapshot=dict(draft=dict(id=f.scope_aid, project_id=pid, runtime_id=runtime,
            candidate=candidate, fingerprint=fingerprint(candidate))))
    with f.store.tx() as c:
        c.execute(insert(app_drafts).values(id=f.scope_aid, project_id=pid, runtime_id=runtime,
            name="Synthetic scope-only PB row", candidate=candidate,
            fingerprint=fingerprint(candidate), created_at=time.time()))
        c.execute(insert(runs).values(id=f.scope_rid, **f.job_header, status="QUEUED",
            fingerprint="e" * 64, created_at=time.time(), resource_refs=[resource], context={}))
        c.execute(insert(internal_instances).values(id=iid, project_id=pid, principal_id=f.user,
            source_app_id=f.scope_aid, runtime_id=runtime, release_id=release_id,
            revision=1, data_version=0, history=[]))
        c.execute(insert(internal_app_runs).values(id=arid, instance_id=iid, release_id=release_id,
            principal_id=f.user, request_key="synthetic-scope-use", fingerprint="e" * 64,
            input={}, status="QUEUED"))
        c.execute(insert(internal_run_bindings).values(run_id=f.scope_rid, app_run_id=arid,
            snapshot=f.scope_snapshot, fingerprint="e" * 64))
        f.store.event(c, f.scope_rid, "ACCEPTED", dict(namespace="INTERNAL_APPRUN",
            instance_id=iid, app_run_id=arid))
        for kind in (use.PB.meta, spec.RUN_META):
            text_logic_reuse.remember(c, f.user, f.scope_rid, kind, "accepted",
                f.scope_meta, f.scope_meta.model_dump())
        text_logic_reuse.remember(c, f.user, iid, use.PB.use, request.request_key, f.commit,
            dict(run_id=f.scope_rid, app_run_id=arid, reviewed=dict(approved_grant_state=[])))
        f.store.add_grants(c, f.user, runtime, pid, resource, ["resource.read"])
        f.store.add_grants(c, f.user, runtime, pid, pid, ["artifact.save_text"])
        f.scope_job = dict(c.execute(select(runs).where(runs.c.id == f.scope_rid)).mappings().one())
    f.sql, f.pairs, f.authorities, f.family_calls = [], [], [], []
    original_pair, original_use_pair = text_logic_reuse.pair, use._use_pair
    original_scope_pair = spec._cold_scope_pair
    original_authorize = f.store.authorize

    def real_pair(c, user, lid, kind, key, model):
        f.pairs.append((lid, kind, key))
        return original_pair(c, user, lid, kind, key, model)

    def real_use_pair(c, user, lid, kind, key, model, *, _graph_read=None):
        f.pairs.append((lid, kind, key))
        return original_use_pair(c, user, lid, kind, key, model, _graph_read=_graph_read)

    def real_scope_pair(store, c, user, lid, guard, *, run_scope=False):
        # Strict Run metadata uses its owned collector so that external checked
        # errors retain identity; observe that real pair as well as legacy pair.
        f.pairs.append((lid, spec.RUN_META if run_scope else spec.META,
            'accepted' if run_scope else 'scope'))
        return original_scope_pair(store, c, user, lid, guard, run_scope=run_scope)

    def real_authorize(c, user, runtime_id, project_id, rid, tool):
        f.authorities.append((user, runtime_id, project_id, rid, tool))
        return original_authorize(c, user, runtime_id, project_id, rid, tool)

    def unrelated_family(store, c, user, aid, *, _graph_read=None):
        assert store is f.store and user == f.user and aid == f.scope_aid
        assert _graph_read is not None
        f.family_calls.append(aid)
        return True

    def sql_done(c, cursor, statement, parameters, context, executemany):
        f.sql.append(statement)

    monkeypatch.setattr(use, "_use_pair", real_use_pair)
    monkeypatch.setattr(spec, "pair", real_pair)
    monkeypatch.setattr(spec, "_cold_scope_pair", real_scope_pair)
    monkeypatch.setattr(f.store, "authorize", real_authorize)
    monkeypatch.setattr(spec, "scope_gate", unrelated_family)
    event.listen(f.store.engine, "after_cursor_execute", sql_done)
    try:
        yield f
    finally:
        event.remove(f.store.engine, "after_cursor_execute", sql_done)


def audit_scope(f, c, guard, header=None, role="audit"):
    return use.scope_gate(f.store, c, f.user, f.scope_rid,
        f.audit_header if header is None else header, _graph_read=guard, _scope_role=role)


def job_scope(f, c, guard):
    return spec.job_scope_gate(f.store, c, f.user, f.scope_rid, _graph_read=guard)


def assert_sticky_without_io(f, c, guard):
    assert not guard.active
    before = (list(f.sql), list(f.pairs), list(f.authorities), list(f.family_calls))
    for call in (lambda: audit_scope(f, c, guard), lambda: job_scope(f, c, guard)):
        with pytest.raises(DomainError) as caught:
            call()
        assert caught.value.code == "VERSION_CONFLICT"
    assert (f.sql, f.pairs, f.authorities, f.family_calls) == before


def test_real_scope_audit_job_then_each_reenters_with_full_distinct_headers(scope_rows):
    f = scope_rows
    with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
        for call in (audit_scope, job_scope, audit_scope, job_scope):
            assert call(f, c, guard) is True
            assert guard.active
        audit = guard.inputs["pb-use-scope:" + f.scope_rid + ":audit"]
        job = guard.inputs["pb-use-scope:" + f.scope_rid + ":job"]
        assert set(audit["header"]) == {"principal_id", "project_id", "runtime_id"}
        assert set(job["header"]) == {*audit["header"], "request_key"}
        assert dict(audit["header"]) == f.audit_header
        assert dict(job["header"]) == f.job_header
        assert audit["meta"] == audit["seal"] == job["meta"] == job["seal"] == f.scope_meta.model_dump()
        assert len(f.pairs) == 10 and len(f.authorities) == 10
        assert len(f.family_calls) == 4
    assert not guard.active


def test_strict_scope_missing_header_keeps_typeerror_and_invalidates_before_io(scope_rows):
    f = scope_rows
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                before = (list(f.sql), list(f.pairs), list(f.authorities), list(f.family_calls))
                with pytest.raises(TypeError) as caught:
                    use.scope_gate(f.store, c, f.user, f.scope_rid, _graph_read=guard)
                assert 'header' in str(caught.value)
                assert not guard.active
                assert (f.sql, f.pairs, f.authorities, f.family_calls) == before
                assert_sticky_without_io(f, c, guard)


@pytest.mark.parametrize(("role", "field"), [
    ("audit", "principal_id"), ("audit", "project_id"), ("audit", "runtime_id"),
    ("job", "principal_id"), ("job", "project_id"), ("job", "runtime_id"), ("job", "request_key"),
])
def test_either_header_value_drift_stops_before_next_pair_location_or_authority(scope_rows, role, field):
    f = scope_rows
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as caught:
            with read_scope(f, c) as guard:
                assert audit_scope(f, c, guard) and job_scope(f, c, guard)
                wrong = dict(f.audit_header if role == "audit" else f.job_header)
                wrong[field] += "-changed"
                pair_count, sql_count = len(f.pairs), len(f.sql)
                authorities, families = list(f.authorities), list(f.family_calls)
                try:
                    audit_scope(f, c, guard, wrong, role)
                except DomainError:
                    assert f.pairs[pair_count:] == [(f.scope_rid, use.PB.meta, "accepted")]
                    assert not any("FROM app_drafts" in sql for sql in f.sql[sql_count:])
                    assert f.authorities == authorities and f.family_calls == families
                    assert_sticky_without_io(f, c, guard)
                    raise
        assert caught.value.code == "VERSION_CONFLICT" and not guard.active


@pytest.mark.parametrize("shape", ["unknown-role", "audit-with-job-header", "job-with-audit-header"])
def test_unknown_role_or_nonexact_header_shape_is_rejected_sticky(scope_rows, shape):
    f = scope_rows
    role, header = {"unknown-role": ("unknown", f.audit_header),
        "audit-with-job-header": ("audit", f.job_header),
        "job-with-audit-header": ("job", f.audit_header)}[shape]
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                try:
                    audit_scope(f, c, guard, header, role)
                except DomainError:
                    assert not f.authorities and not f.family_calls
                    assert not any(key.startswith("pb-use-scope:") for key in guard.inputs)
                    assert_sticky_without_io(f, c, guard)
                    raise


def test_actual_review_numeric_callback_drift_ignores_shadow_dump_and_stops_next_consumer(local_origin, monkeypatch):
    f, calls, shadow_calls = local_origin, [], []
    base = copy.deepcopy(f.draft)
    base["candidate"]["spec_task"] = dict(kind=pb.KIND)
    base["fingerprint"] = fingerprint(base["candidate"])
    release = dict(id=new_id("release"), fingerprint="b" * 64, snapshot=dict(draft=base))
    instance = dict(id=new_id("instance"), source_app_id=base["id"], runtime_id=base["runtime_id"],
        project_id=base["project_id"], revision=1)
    body = use.ReviewInput(expected_revision=1, expected_release_fingerprint=release["fingerprint"],
        expected_app_fingerprint=base["fingerprint"], expected_recipe_fingerprint=fingerprint(base["candidate"]["spec_recipe"]),
        resource_id=f.origin[2]["resource_id"], card_id=f.origin[3]["card_id"], expected_goal_version=1,
        expected_goal_fingerprint=f.origin[3]["fingerprint"], expected_source_hash=f.origin[2]["hash"], request_key="typed-numeric")
    raw = use.ReviewInput.model_dump(body)

    def target(*args, **kwargs):
        calls.append("target")
        body.expected_revision = True  # Same Python equality; a different JSON type.

        def shadow():
            shadow_calls.append("instance.model_dump")
            return raw

        object.__setattr__(body, "model_dump", shadow)
        return f.origin[2], GoalCardRunSource.model_validate(f.origin[3])

    def next_consumer(*args, **kwargs):
        calls.append("effective")
        pytest.fail("Equal-valued typed drift reached candidate expansion")

    monkeypatch.setattr(spec, "target", target)
    monkeypatch.setattr(use, "_review_effective_from_target", next_consumer)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                try:
                    use._cold_review_prefix(f.store, c, f.user, instance, release, body, f.limits, guard)
                except DomainError:
                    assert calls == ["target"] and not shadow_calls and not guard.active
                    with pytest.raises(DomainError):
                        use._cold_review_prefix(f.store, c, f.user, instance, release, body, f.limits, guard)
                    assert calls == ["target"] and not shadow_calls
                    raise


def test_real_malformed_commit_pair_preserves_public_conflict_in_strict_leaf(scope_rows):
    f = scope_rows
    with f.store.tx() as c:
        rows = c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == f.scope_snapshot["instance_id"],
            delivery_graph_requests.c.kind.in_([use.PB.use, use.PB.use + "_seal"]))).mappings().all()
        assert len(rows) == 2
        for row in rows:
            saved = copy.deepcopy(row["snapshot"])
            saved["request"]["review"]["expected_revision"] = True
            c.execute(update(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == row["app_id"],
                delivery_graph_requests.c.principal_id == row["principal_id"],
                delivery_graph_requests.c.kind == row["kind"],
                delivery_graph_requests.c.request_key == row["request_key"]).values(
                    snapshot=saved, request_fingerprint=fingerprint(saved["request"]), fingerprint=fingerprint(saved)))
        f.scope_snapshot["pb_use"]["review"]["expected_revision"] = True
    f.sql.clear()
    with f.store.tx() as c:
        with pytest.raises(DomainError) as public:
            use.bound(f.store, c, f.user, f.scope_job, f.scope_snapshot, f.scope_release, f.limits)
    assert public.value.code == "VERSION_CONFLICT"
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as strict:
            with read_scope(f, c) as guard:
                try:
                    use._cold_bound_prefix(f.store, c, f.user, f.scope_job, f.scope_snapshot,
                        f.scope_release, f.limits, guard)
                except DomainError as error:
                    assert error.public() == public.value.public()
                    assert_sticky_without_io(f, c, guard)
                    raise
    assert strict.value.public() == public.value.public() and not guard.active
    assert not any("FROM internal_instances" in sql for sql in f.sql)
    assert not f.authorities and not f.family_calls


def test_pair_lookup_callback_valueerror_is_not_normalized_as_persisted_parse(scope_rows):
    f = scope_rows
    original = ValueError("synthetic pair lookup callback")

    def fail_after_lookup(c, cursor, statement, parameters, context, executemany):
        if "FROM delivery_graph_requests" in statement:
            raise original

    event.listen(f.store.engine, "after_cursor_execute", fail_after_lookup)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(ValueError) as caught:
                with read_scope(f, c) as guard:
                    use._cold_bound_prefix(f.store, c, f.user, f.scope_job, f.scope_snapshot,
                        f.scope_release, f.limits, guard)
        assert caught.value is original and not guard.active
        assert not f.authorities and not f.family_calls
    finally:
        event.remove(f.store.engine, "after_cursor_execute", fail_after_lookup)


def test_first_real_pair_lookup_callback_drift_stops_before_seal_lookup(scope_rows, monkeypatch):
    f, lookups, changed = scope_rows, [], []
    original_lookup = graph.lookup

    def real_lookup(c, user, lid, kind, key):
        lookups.append((lid, kind, key))
        return original_lookup(c, user, lid, kind, key)

    def drift_after_first_lookup(c, cursor, statement, parameters, context, executemany):
        if "FROM delivery_graph_requests" in statement and not changed:
            changed.append("first-lookup")
            f.inputs["history"].append(dict(synthetic="lookup-callback-drift"))

    monkeypatch.setattr(graph, "lookup", real_lookup)
    event.listen(f.store.engine, "after_cursor_execute", drift_after_first_lookup)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError) as caught:
                with read_scope(f, c) as guard:
                    try:
                        use._cold_bound_prefix(f.store, c, f.user, f.scope_job, f.scope_snapshot,
                            f.scope_release, f.limits, guard)
                    except DomainError:
                        assert changed == ["first-lookup"]
                        assert lookups == [(f.scope_snapshot["instance_id"], use.PB.use,
                            f.commit.review.request_key)]
                        assert len([sql for sql in f.sql if "FROM delivery_graph_requests" in sql]) == 1
                        assert not any("FROM internal_instances" in sql for sql in f.sql)
                        assert not f.authorities and not f.family_calls
                        assert_sticky_without_io(f, c, guard)
                        assert len(lookups) == 1
                        raise
            assert caught.value.code == "VERSION_CONFLICT" and not guard.active
    finally:
        event.remove(f.store.engine, "after_cursor_execute", drift_after_first_lookup)


def test_strict_scope_guard_valueerror_preserves_original_object_outside_default_mapper(scope_rows, monkeypatch):
    f, raised = scope_rows, []
    original = ValueError("synthetic strict scope checkpoint")
    checkpoint = use._use_read_checkpoint
    pin = "pb-use-scope:" + f.scope_rid + ":audit"

    def fail_after_scope_pin(store, c, guard):
        checkpoint(store, c, guard)
        if guard is not None and pin in guard.inputs:
            raised.append("scope-checkpoint")
            raise original

    monkeypatch.setattr(use, "_use_read_checkpoint", fail_after_scope_pin)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with read_scope(f, c) as guard:
                try:
                    audit_scope(f, c, guard)
                except ValueError as error:
                    assert error is original and raised == ["scope-checkpoint"]
                    assert not f.authorities and not f.family_calls
                    assert_sticky_without_io(f, c, guard)
                    assert raised == ["scope-checkpoint"]
                    raise
        assert caught.value is original and not guard.active

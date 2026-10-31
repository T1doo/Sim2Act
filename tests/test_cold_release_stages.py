"""Synthetic lifecycle boundary units. No graph producer, authority, or model IO."""

import copy
from contextlib import contextmanager
import time

import pytest
from sqlalchemy import event, insert, text
from sqlalchemy.exc import OperationalError
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport

from sim2act import apps, lifecycle, text_continuations, text_logic_reuse
from sim2act import csv_dag_instances as csv_dag
from sim2act import csv_full_report_instances as full_report
from sim2act import csv_goal_revisions as csv_revision
from sim2act import local_record_apps as records
from sim2act import natural_logic_patches as logic
from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act.db import fingerprint, internal_approvals, internal_releases, new_id
from sim2act.errors import DomainError


@pytest.fixture
def saved(local_origin, monkeypatch):
    # These units deliberately replace lifecycle/compiler callbacks. They
    # exercise the original raw complete-graph path, not fixed-code ownership.
    # Real default-owner production boundaries have separate integration tests.
    monkeypatch.setattr(runtime, '_SOURCE_VIEW_TYPE', None)
    monkeypatch.setattr(lifecycle._release_owned_code, '_SOURCE_OK', False)
    f = local_origin
    f.rid, approval = new_id("release"), new_id("approval")
    snapshot = dict(namespace=lifecycle.NAMESPACE, formal_publication_enabled=False,
        draft=copy.deepcopy(f.draft), dependency_lock=f.draft["candidate"]["manifest"]["dependency_lock"],
        data_schema=lifecycle.record_schema(f.draft["candidate"]))
    with f.store.tx() as c:
        payload = dict(snapshot=snapshot)
        c.execute(insert(internal_approvals).values(id=approval, principal_id=f.user,
            project_id=f.draft["project_id"], kind="release", payload=payload,
            fingerprint=fingerprint(payload), expires_at=time.time()+300, consumed=True))
        c.execute(insert(internal_releases).values(id=f.rid, principal_id=f.user,
            project_id=f.draft["project_id"], approval_id=approval, snapshot=snapshot,
            fingerprint=fingerprint(snapshot)))
    monkeypatch.setattr(records, "reject_legacy", lambda *a, **k: f.trace.append("legacy_gate"))
    monkeypatch.setattr(full_report, "release_gate", lambda *a, **k: (f.trace.append("report_gate") or None))
    monkeypatch.setattr(text_continuations, "release_gate", lambda *a: f.trace.append("release_gate"))
    monkeypatch.setattr(csv_dag, "validate_family", lambda *a: f.trace.append("csv_family"))
    monkeypatch.setattr(logic, "validate_family", lambda *a: f.trace.append("logic_family"))
    monkeypatch.setattr(csv_revision, "validate_family", lambda *a: f.trace.append("revision_family"))
    original_schema = lifecycle.record_schema
    monkeypatch.setattr(lifecycle, "record_schema", lambda *a: (f.trace.append("schema") or original_schema(*a)))
    monkeypatch.setattr(lifecycle, "validate_source_bytes", lambda *a: f.trace.append("source_bytes"))
    monkeypatch.setattr(text_logic_reuse, "independent", lambda *a: (f.trace.append("independent") or False))
    f.inputs = dict(call=dict(run_id="synthetic-current", complete=[1, 2, 2]))
    return f


@contextmanager
def read_scope(f, c):
    with runtime._cold_graph_read(f.worker, c, f.inputs, f.roles, "pre") as guard:
        try:
            yield guard
        finally:
            if runtime._SOURCE_VIEW_TYPE is None:
                assert vars(guard).get('_source_fact_bindings') is None
                if type(guard.inputs) is dict:
                    assert not any(type(value) is tuple and len(value) == 2
                        and type(value[0]) is str and value[0] == 'sim2act:owned-source-fact.v1'
                        for value in guard.inputs.values())


def stages(f, c, guard):
    release = lifecycle._cold_release_prefix(f.store, c, f.user, f.rid, f.limits, guard, "cold")
    draft = release.release["snapshot"]["draft"]
    candidate = apps._cold_candidate_prefix(f.store, c, f.user, draft, f.limits, guard, "cold")
    return release, candidate


def test_actual_row_prefix_origin_position_same_draft_and_no_public_replay(saved):
    f = saved
    with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
        release, candidate = stages(f, c, guard)
        assert candidate.draft is release.release["snapshot"]["draft"]
        assert candidate.draft is not f.draft  # Actual SQL JSON object, not an equal caller copy.
        f.trace.append("origin_complete")
        with apps._cold_graph_origin_facts(f.worker, c, guard.inputs, "cold", f.roles,
                f.user, candidate.draft, f.limits, f.origin) as facts:
            result = lifecycle._cold_release_from_origin(f.store, c, f.user, release, candidate, facts)
            assert result is release.release
            assert facts.draft is candidate.draft
        assert "verify_origin" not in f.trace
        assert f.trace.index("schema") < f.trace.index("draft_gate") < f.trace.index("compile")
        assert f.trace.index("compile") < f.trace.index("origin_complete") < f.trace.index("source_bytes")
        assert f.trace[-1] == "independent"
    assert not guard.active


@pytest.mark.parametrize("where", ["own_project", "source_bytes"])
def test_callback_drift_rejects_before_next_private_stage(saved, monkeypatch, where):
    f = saved
    def drift(*args):
        f.trace.append(where)
        f.worker.s = copy.copy(f.worker.s)
    if where == "own_project":
        monkeypatch.setattr(f.store, "own_project", drift)
        original = lifecycle.immutable_release_pointer
        monkeypatch.setattr(lifecycle, "immutable_release_pointer",
            lambda *a, **k: (f.trace.append("immutable") or original(*a, **k)))
    else:
        monkeypatch.setattr(lifecycle, "validate_source_bytes", drift)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                release, candidate = stages(f, c, guard)
                with apps._cold_graph_origin_facts(f.worker, c, guard.inputs, "cold", f.roles,
                        f.user, candidate.draft, f.limits, f.origin) as facts:
                    lifecycle._cold_release_from_origin(f.store, c, f.user, release, candidate, facts)
        assert not guard.active
    assert ("immutable" if where == "own_project" else "independent") not in f.trace
    assert f.trace[-1] == where and "verify_origin" not in f.trace


def test_approval_select_drift_rejects_before_payload_fingerprint(saved, monkeypatch):
    f, changed = saved, [False]
    original = lifecycle.fingerprint
    def observed_fingerprint(value):
        assert not changed[0], "Approval payload consumed after callback drift"
        return original(value)
    def after_sql(c, cursor, statement, params, context, executemany):
        if "FROM internal_approvals" in statement:
            f.inputs["call"]["complete"].append("drift")
            changed[0] = True
    monkeypatch.setattr(lifecycle, "fingerprint", observed_fingerprint)
    event.listen(f.store.engine, "after_cursor_execute", after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError) as error:
                with read_scope(f, c) as guard:
                    lifecycle._cold_release_prefix(f.store, c, f.user, f.rid, f.limits, guard, "cold")
        assert changed[0] and error.value.code == "VERSION_CONFLICT" and not guard.active
        assert "csv_family" not in f.trace and "schema" not in f.trace
    finally:
        event.remove(f.store.engine, "after_cursor_execute", after_sql)


def test_release_gate_drift_stops_before_release_body_select(saved, monkeypatch):
    f, bodies = saved, []
    def drift(*args):
        f.worker.s = copy.copy(f.worker.s)
    def after_sql(c, cursor, statement, params, context, executemany):
        if "FROM internal_releases" in statement:
            bodies.append(statement)
    monkeypatch.setattr(text_continuations, "release_gate", drift)
    event.listen(f.store.engine, "after_cursor_execute", after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError):
                with read_scope(f, c) as guard:
                    lifecycle._cold_release_prefix(f.store, c, f.user, f.rid, f.limits, guard, "cold")
        assert not bodies and not guard.active
    finally:
        event.remove(f.store.engine, "after_cursor_execute", after_sql)


def test_original_callback_exception_is_not_overwritten(saved, monkeypatch):
    f = saved
    original = DomainError("PERMISSION_DENIED", "synthetic original gate exception")
    def gate(*args):
        f.worker.s = copy.copy(f.worker.s)
        raise original
    monkeypatch.setattr(text_continuations, "release_gate", gate)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as error:
            with read_scope(f, c) as guard:
                lifecycle._cold_release_prefix(f.store, c, f.user, f.rid, f.limits, guard, "cold")
    assert error.value is original and not guard.active
    assert "own_project" not in f.trace and "draft_gate" not in f.trace


@pytest.mark.parametrize("write", ["noop", "failed"])
def test_pre_origin_sqlite_write_invalidates_before_any_release_read(saved, write):
    f = saved
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                if write == "noop":
                    c.execute(text("UPDATE internal_releases SET fingerprint=fingerprint WHERE id='absent'"))
                else:
                    with pytest.raises(OperationalError):
                        c.execute(text("UPDATE synthetic_absent_table SET value=1"))
                lifecycle._cold_release_prefix(f.store, c, f.user, f.rid, f.limits, guard, "cold")
    assert not f.trace and not guard.active


def test_prefix_fields_and_equal_but_other_draft_cannot_be_rebound(saved):
    f = saved
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                release, candidate = stages(f, c, guard)
                other = copy.deepcopy(candidate.draft)
                with apps._cold_graph_origin_facts(f.worker, c, guard.inputs, "cold", f.roles,
                        f.user, other, f.limits, f.origin) as facts:
                    lifecycle._cold_release_from_origin(f.store, c, f.user, release, candidate, facts)
    assert "source_bytes" not in f.trace and "verify_origin" not in f.trace


def test_default_archival_early_return_preserved_but_strict_rejects(saved, monkeypatch):
    f = saved
    monkeypatch.setattr(text_continuations, "legacy_release", lambda *a: f.trace.append("archival"))
    with f.store.tx() as c:
        result = lifecycle.read_release(f.store, c, f.user, f.rid, f.limits, archival_software="synthetic")
        assert result["id"] == f.rid and f.trace[-1] == "archival"
    f.trace.clear()
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                lifecycle._read_release_prefix(f.store, c, f.user, f.rid, f.limits,
                    archival_software="synthetic", _graph_read=guard, _graph_key="strict-release")
    assert "archival" not in f.trace and "draft_gate" not in f.trace


@pytest.mark.parametrize("callee", ["draft_gate", "own_project", "source_family", "compile"])
def test_caught_candidate_prefix_error_invalidates_same_scope(saved, monkeypatch, callee):
    f = saved
    original = DomainError("PERMISSION_DENIED", "synthetic prefix callback failure")
    def fail(*args):
        raise original
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                release = lifecycle._cold_release_prefix(f.store, c, f.user, f.rid, f.limits, guard, "cold")
                draft = release.release["snapshot"]["draft"]
                module, name = {"draft_gate": (text_continuations, "draft_gate"),
                    "own_project": (f.store, "own_project"),
                    "source_family": (apps, "validate_source_family"),
                    "compile": (apps, "compile_preview")}[callee]
                monkeypatch.setattr(module, name, fail)
                with pytest.raises(DomainError) as error:
                    apps._cold_candidate_prefix(f.store, c, f.user, draft, f.limits, guard, "cold")
                assert error.value is original and not guard.active
                with pytest.raises(DomainError):
                    guard.check(f.store, c)


@pytest.mark.parametrize("where", ["candidate-facts", "release-candidate"])
def test_caught_wrong_type_cannot_resume_valid_stages(saved, where):
    f = saved
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                release, candidate = stages(f, c, guard)
                with apps._cold_graph_origin_facts(f.worker, c, guard.inputs, "cold", f.roles,
                        f.user, candidate.draft, f.limits, f.origin) as facts:
                    with pytest.raises(DomainError):
                        if where == "candidate-facts":
                            apps._cold_candidate_from_origin(f.store, c, f.user, candidate, {})
                        else:
                            lifecycle._cold_release_from_origin(f.store, c, f.user, release, None, facts)
                    assert not guard.active
                    if where == "release-candidate":
                        assert not facts.active
                    with pytest.raises(DomainError):
                        lifecycle._cold_release_from_origin(f.store, c, f.user, release, candidate, facts)


@pytest.mark.parametrize("entry", ["candidate", "release"])
def test_wrong_guard_rejection_never_calls_unknown_cleanup(saved, entry):
    f = saved
    class UnknownGuard:
        def invalidate(self):
            pytest.fail("Unknown guard cleanup must never be invoked")
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as error:
            if entry == "candidate":
                apps._cold_candidate_prefix(f.store, c, f.user, f.draft, f.limits, UnknownGuard(), "cold")
            else:
                lifecycle._cold_release_prefix(f.store, c, f.user, f.rid, f.limits, UnknownGuard(), "cold")
        assert error.value.code == "VERSION_CONFLICT"
        assert not f.trace

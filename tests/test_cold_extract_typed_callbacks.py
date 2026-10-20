"""Synthetic typed callback units; no Source proof, grant, Run or model execution."""

import copy
import time

import pytest
from sqlalchemy import event, insert
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act.contracts import GoalCardRunSource
from sim2act.db import app_drafts, fingerprint, new_id
from sim2act.errors import DomainError
from sim2act.pa_material_bindings import Metadata
from sim2act.text_workflows import RunScopeInput


def packets(f, c, guard):
    """Exact local packets stop at a callback boundary; they confer no authority."""
    rid, key = new_id("run"), "synthetic-owned-typed-callback"
    review = pb.ReviewInput(source_run_id=rid,
        expected_source_proof_fingerprint="a" * 64,
        expected_source_recipe_fingerprint=fingerprint(f.draft["candidate"]["spec_recipe"]),
        card_id=f.origin[3]["card_id"], expected_goal_version=f.origin[3]["version"],
        expected_goal_fingerprint=f.origin[3]["fingerprint"],
        expected_source_hash=f.origin[2]["hash"],
        recipe=copy.deepcopy(f.draft["candidate"]["spec_recipe"]),
        name="Synthetic typed callback", request_key=key)
    body = pb.ExtractInput(review=review, expected_review_fingerprint="b" * 64,
        consent=pb.CONSENT, artifact_write_consent=pb.natural.CONSENT)
    meta = Metadata(app_id=f.draft["id"], principal_id=f.user,
        project_id=f.draft["project_id"], runtime_id=f.draft["runtime_id"],
        resource_id=f.origin[2]["resource_id"], source_run_id=rid)
    checked = dict(review_fingerprint=body.expected_review_fingerprint,
        app_id=f.draft["id"], runtime_id=f.draft["runtime_id"],
        candidate_fingerprint=f.draft["fingerprint"],
        source_proof_fingerprint=review.expected_source_proof_fingerprint,
        approved_source_limits=f.limits.model_dump())
    frozen = pb.frozen_for(f.user, f.draft["project_id"], body, checked)
    marker = dict(snapshot=frozen, principal_id=f.user, task_id=rid,
        request_key=key, request_fingerprint=fingerprint(body.model_dump()))
    prefix = pb._ColdExtractionPrefix(guard, "unit-extraction", f.user, f.draft,
        f.limits, "cold", marker, body, frozen, meta)
    guard.add(prefix.key, prefix.fields())
    source_prefix = pb._ColdSourcePrefix(guard, "unit-source", f.user,
        f.draft["project_id"], rid, f.limits, "cold", dict(id=rid))
    scope = RunScopeInput(**{k: v for k, v in meta.model_dump().items() if k != "source_run_id"}, run_id=rid,
        instance_id=new_id("instance"), app_run_id=new_id("apprun"), release_id=new_id("release"))
    audit_prefix = pb._ColdSourceAuditPrefix(guard, "unit-source-audit", f.user,
        f.draft["project_id"], rid, scope, scope.model_dump(), f.draft, {})
    audit = pb._ColdSourceAuditFacts(audit_prefix, "unit-source-audit:complete", {}, {}, "a" * 64)
    typed = pb._ColdSourceTyped(source_prefix, "unit-source:typed", {}, {}, [], {}, {})
    source = pb._ColdSourceFacts(typed, audit, "unit-source:complete", {})
    guard.add(source.key, source.fields())
    goal = GoalCardRunSource.model_validate(f.origin[3])
    full_review = pb._ColdExtractionReview(prefix, source, "unit-extraction:review",
        checked, f.origin[2], goal)
    guard.add(full_review.key, full_review.fields())
    return prefix, source, full_review


def test_source_comparison_numeric_drift_rejects_before_target_io(local_origin, monkeypatch):
    f, target_calls = local_origin, []

    def compare(body, proof):
        assert type(body.expected_goal_version) is int and body.expected_goal_version == 1
        body.expected_goal_version = True  # Python == still says 1 == True.

    def target(*args, **kwargs):
        target_calls.append("target")
        pytest.fail("Target IO ran after the owned comparison changed ExtractInput")

    monkeypatch.setattr(pb, "_review_source_from_facts", compare)
    monkeypatch.setattr(spec, "target", target)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError) as caught:
            with read_scope(f, c) as guard:
                prefix, source, _ = packets(f, c, guard)
                pb._cold_review_from_source(f.store, c, f.user, prefix, source)
        assert caught.value.code == "VERSION_CONFLICT" and not guard.active
    assert target_calls == []


@pytest.mark.parametrize("where", ["name", "compile"])
def test_goal_numeric_drift_rejects_before_next_consumer_or_export(local_origin, monkeypatch, where):
    f, calls, goal_ref = local_origin, [], []
    # Name lookup is the only actual persisted read exercised here.
    with f.store.tx() as c:
        c.execute(insert(app_drafts).values(**f.draft, name="Synthetic typed callback", created_at=time.time()))

    def after_sql(c, cursor, statement, params, context, executemany):
        if "app_drafts.name" in statement and "FROM app_drafts" in statement:
            calls.append("name")
            if where == "name":
                goal_ref[0].version = True

    def compile_candidate(*args, **kwargs):
        calls.append("compile")
        if where == "name":
            pytest.fail("Compilation ran after the name callback changed the typed Goal")
        assert type(goal_ref[0].version) is int and goal_ref[0].version == 1
        goal_ref[0].version = True
        return f.origin[0], None, f.origin[1]

    monkeypatch.setattr(pb.natural, "compile_candidate", compile_candidate)
    event.listen(f.store.engine, "after_cursor_execute", after_sql)
    try:
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError) as caught:
                with read_scope(f, c) as guard:
                    prefix, _, reviewed = packets(f, c, guard)
                    goal_ref.append(reviewed.goal)
                    pb._cold_verify_from_review(f.store, c, f.user, prefix, reviewed)
            assert caught.value.code == "VERSION_CONFLICT" and not guard.active
            assert prefix.key + ":verified" not in guard.inputs
        assert calls == (["name"] if where == "name" else ["name", "compile"])
    finally:
        event.remove(f.store.engine, "after_cursor_execute", after_sql)

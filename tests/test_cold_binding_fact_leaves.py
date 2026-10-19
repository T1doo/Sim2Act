"""Synthetic local pins/SQLite and pure predicates, never full trial authority."""

import copy
import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from test_natural_spec_apps import recipe
from test_pb_live_source_contract import material

from sim2act import app_jobs, apps, text_continuations
from sim2act import natural_live_admission as gate
from sim2act import natural_specs as natural
from sim2act import pa_spec_apps as spec
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act.contracts import GoalCardRunSource, Limits
from sim2act.db import fingerprint, new_id
from sim2act.errors import DomainError
from sim2act.production_trial_admission import canonical_quota_subject
from sim2act.spec_production import ProductionTrialBinding
from sim2act.worker import Worker


def full_limits(**changes):
    return Limits(max_requests=4, max_tools=4, max_repairs=1, max_total_tokens=64000,
        max_output_tokens=1024, run_seconds=300).model_copy(update=changes)


def denied(call, code="VERSION_CONFLICT"):
    with pytest.raises(DomainError) as error:
        call()
    assert error.value.code == code
    return error.value.public()


@pytest.fixture(autouse=True)
def no_external_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Local facts tests cannot call external or Mock model transports")
    for transport in (httpx.HTTPTransport, httpx.AsyncHTTPTransport, httpx.MockTransport):
        for method in ("handle_request", "handle_async_request"):
            if hasattr(transport, method):
                monkeypatch.setattr(transport, method, forbidden)


@pytest.fixture
def local_origin(env, monkeypatch):
    store, settings, _, user, _, pid, _ = env
    old, target = material(1), material(2)
    limits = full_limits()
    goal = GoalCardRunSource(card_id=target.card_id, version=target.goal_version,
        fingerprint=target.goal_fingerprint, snapshot=target.goal_snapshot.model_dump())
    source = dict(resource_id=target.resource_id, hash=target.source_hash,
        content=target.content, format="txt")
    aid = new_id("app")
    candidate = natural.expand(recipe("ordered"), aid, goal.card_id, pid, source["hash"],
        source["resource_id"], goal.snapshot["content"], limits, "a" * 64)
    draft = dict(id=aid, project_id=pid, runtime_id="synthetic-cold-runtime",
        candidate=candidate, fingerprint=fingerprint(candidate))
    manifest, action, report = natural.compile_candidate(candidate, limits)
    contract = gate.PBTrialContract(trial_key="synthetic-origin", project_id=pid,
        principal_id=user, runtime_id=new_id("runtime"),
        quota_subject=canonical_quota_subject("synthetic-account"),
        software_fingerprint="b" * 64, authorization_fingerprint="c" * 64,
        bindings=[old, target], stage_keys=dict(generate="g", source="s", cold="c"),
        expires_at=time.time() + 300, path="P-B", extraction_request_key="x", extraction_recipe=recipe("ordered"))
    binding = ProductionTrialBinding(contract, "synthetic-approval", "synthetic-account")
    # No Worker constructor/validate/claim/send. This is a pin fixture, not a permit.
    worker = object.__new__(Worker)
    worker.store, worker.s, worker.pa_trial = store, settings, binding
    worker.id, worker.stop, worker.goal_planner_transport = "synthetic-worker", threading.Event(), None
    worker._journal_trial_store, worker._journal_trial_binding = store, binding
    worker._journal_trial_drift = False
    trace = []
    monkeypatch.setattr(text_continuations, "draft_gate", lambda *a: trace.append("draft_gate"))
    monkeypatch.setattr(store, "own_project", lambda *a: trace.append("own_project"))
    monkeypatch.setattr(apps, "validate_source_family", lambda *a: trace.append("source_family"))
    monkeypatch.setattr(apps, "compile_preview", lambda *a: (trace.append("compile") or (manifest, action, report)))
    origin = (manifest, report, source, goal.model_dump())
    monkeypatch.setattr(spec, "verify_origin", lambda *a: (trace.append("verify_origin") or origin))
    roles = dict(source=full_limits(max_requests=2), generate=None, platform=limits,
        trial=full_limits(max_requests=3), per_use=full_limits(max_requests=2, max_repairs=0))
    inputs = dict(run=dict(id="synthetic-cold", runtime_id=draft["runtime_id"]),
        history=[{"id": "one", "body": b"full original bytes"}, {"id": "one", "body": b"duplicate retained"}])
    return SimpleNamespace(store=store, worker=worker, user=user, draft=draft, limits=limits,
        origin=origin, roles=roles, inputs=inputs, trace=trace)


def handoff(f, c):
    return apps._cold_graph_origin_facts(f.worker, c, f.inputs, "cold", f.roles,
        f.user, f.draft, f.limits, f.origin)


def validate(f, c, facts=None, out=None):
    return apps.validate_frozen_candidate(f.store, c, f.user, f.draft, f.limits,
        _reuse_origin=facts, _origin_out=out)


@pytest.mark.parametrize("mode", ["default", "dict_match", "dict_fallback", "strict"])
def test_origin_handoff_legacy_order_and_strict_without_public_fallback(local_origin, mode):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        if mode == "strict":
            with handoff(f, c) as facts:
                out = {}
                result = validate(f, c, facts, out)
                assert out["origin"] == f.origin
                assert facts.active
            assert not facts.active
            before = list(f.trace)
            denied(lambda: validate(f, c, facts))
            assert f.trace == before
        else:
            reuse = None if mode == "default" else dict(_call_connection=c,
                _call_transaction=c.get_transaction(), principal_id=f.user, draft=copy.deepcopy(f.draft),
                platform_limits=f.limits.model_dump(), origin=f.origin)
            if mode == "dict_fallback":
                reuse["platform_limits"]["max_requests"] = 3
            result = validate(f, c, reuse)
        assert result == (f.draft, *apps.compile_preview(f.draft["candidate"], f.limits))
        expected = ["draft_gate", "own_project", "source_family", "compile"]
        if mode in {"default", "dict_fallback"}:
            expected.append("verify_origin")
        assert f.trace[:-1] == expected


@pytest.mark.parametrize("callee", ["draft_gate", "own_project", "source_family", "compile"])
def test_strict_callback_drift_is_sticky_before_later_calls(local_origin, monkeypatch, callee):
    f = local_origin
    def mutate(*args):
        f.trace.append(callee)
        if callee == "draft_gate":
            f.draft["candidate"]["namespace"] = "changed-family"
        elif callee == "own_project":
            f.roles["generate"] = f.roles["trial"]  # None is a distinct full role value.
        elif callee == "source_family":
            f.worker.s = copy.copy(f.worker.s)  # Equal values, different exact Settings.
        else:
            f.limits.max_tools -= 1
            return (*f.origin[:1], None, f.origin[1])
    module, name = {"draft_gate": (text_continuations, "draft_gate"),
        "own_project": (f.store, "own_project"), "source_family": (apps, "validate_source_family"),
        "compile": (apps, "compile_preview")}[callee]
    monkeypatch.setattr(module, name, mutate)
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with handoff(f, c) as facts:
                validate(f, c, facts)
        assert not facts.active and "verify_origin" not in f.trace
        assert f.trace[-1] == callee


@pytest.mark.parametrize("write", ["noop", "failed", "driver"])
def test_strict_real_sqlite_write_boundaries(local_origin, write):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with handoff(f, c) as facts:
                if write == "noop":
                    c.execute(text("UPDATE principals SET name=name WHERE id='absent'"))
                elif write == "failed":
                    with pytest.raises(OperationalError):
                        c.execute(text("UPDATE synthetic_missing_table SET value=1"))
                else:
                    before_epoch = c.info.get("source_proof_write_epoch", 0)
                    before = facts.driver.total_changes
                    facts.driver.execute("UPDATE principals SET name=name WHERE id=?", (f.user,))
                    assert facts.driver.total_changes > before
                    assert c.info.get("source_proof_write_epoch", 0) == before_epoch
                validate(f, c, facts)
        assert not facts.active and not f.trace


def test_strict_complete_input_origin_nonce_and_exception_cleanup(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        for mutate, restore in [
            (lambda: f.inputs["history"].reverse(), lambda: f.inputs["history"].reverse()),
            (lambda: f.origin[2].update(content="changed bytes"), lambda: f.origin[2].update(content=material(2).content)),
        ]:
            with pytest.raises(DomainError):
                with handoff(f, c) as facts:
                    mutate()
                    validate(f, c, facts)
            restore()
            denied(lambda: facts.check(f.store, c, f.user, f.draft, f.limits))
        with pytest.raises(DomainError):
            with handoff(f, c) as facts:
                facts.scope[0] = object()
                validate(f, c, facts)
        original = DomainError("PERMISSION_DENIED", "synthetic original callback error")
        def original_error(*args):
            raise original
        monkeypatch.setattr(text_continuations, "draft_gate", original_error)
        with pytest.raises(DomainError) as error:
            with handoff(f, c) as facts:
                validate(f, c, facts)
        assert error.value is original and not facts.active
        assert "verify_origin" not in f.trace


def test_queue_facts_permission_identity_full_input_and_resource():
    user = "owner"
    request = dict(instance_id="i", expected_revision=1, expected_release_fp="release-fp", input={"all": [1, 2]})
    s = dict(**request, namespace=app_jobs.KIND, model_requests=0, run_id="r", app_run_id="a",
        release_id="release", principal_id=user, project_id="p", runtime_id="cold-runtime",
        request_fingerprint=fingerprint(request))
    b = dict(snapshot=s, fingerprint=fingerprint(s))
    job = dict(id="r", principal_id=user, project_id="p", runtime_id="cold-runtime",
        fingerprint=b["fingerprint"], context=dict(kind=app_jobs.KIND), resource_refs=["per-use-source"])
    a = dict(id="a", principal_id=user, instance_id="i", release_id="release", input=s["input"],
        fingerprint=s["request_fingerprint"])
    release = dict(fingerprint="release-fp", project_id="p", snapshot=dict(draft=dict(runtime_id="cold-runtime")))
    assert app_jobs._binding_queue_from_facts(job, user, b) is s
    app_jobs._binding_app_run_from_facts(job, b, s, a)
    app_jobs._binding_request_from_facts(job, user, s, a, request)
    app_jobs._binding_release_from_facts(job, s, release, "per-use-source")
    denied(lambda: app_jobs._binding_queue_from_facts(job, "other", None), "PERMISSION_DENIED")
    denied(lambda: app_jobs._binding_queue_from_facts({**job, "runtime_id": "trial-runtime"}, user, b))
    denied(lambda: app_jobs._binding_app_run_from_facts(job, b, s, None))
    denied(lambda: app_jobs._binding_request_from_facts(job, user, s, {**a, "input": {"all": [2, 1]}}, request))
    denied(lambda: app_jobs._binding_release_from_facts(job, s, release, "saved-base-source"))


@pytest.mark.parametrize("family", [use.PA, use.PB])
def test_per_use_full_frozen_candidate_and_distinct_compile_limits(local_origin, monkeypatch, family):
    f = local_origin
    base = f.draft
    base["candidate"]["spec_task"] = dict(kind=pb.KIND) if family == use.PB else {}
    if family == use.PA:
        base["candidate"].pop("spec_task")
        base["candidate"]["goal_application"] = dict(run_id="gen")
    base["fingerprint"] = fingerprint(base["candidate"])
    release = dict(fingerprint="release-fp", snapshot=dict(draft=base))
    instance = dict(source_app_id=base["id"], runtime_id=base["runtime_id"], revision=2)
    body = SimpleNamespace(expected_revision=2, expected_release_fingerprint="release-fp",
        expected_app_fingerprint=base["fingerprint"], expected_recipe_fingerprint=fingerprint(base["candidate"]["spec_recipe"]))
    use._review_identity_from_facts(instance, release, body, base, base["candidate"], family)
    denied(lambda: use._review_identity_from_facts({**instance, "revision": 3}, release, body, base, base["candidate"], family))
    checked = dict(review_fingerprint="reviewed", effective_fingerprint="effective",
        effective_candidate=copy.deepcopy(base["candidate"]), approved_grant_state=[dict(id="grant", revoked=False)])
    body = SimpleNamespace(expected_review_fingerprint="reviewed", model_dump=lambda: {"complete": "request"})
    frozen = dict(reviewed=copy.deepcopy(checked), request_fingerprint=fingerprint(body.model_dump()))
    snapshot = {"pb_effective_fingerprint" if family == use.PB else "pa_effective_fingerprint": "effective"}
    trace = []
    def compile_full(candidate, limits):
        trace.append((copy.deepcopy(candidate), limits.model_dump()))
        return "manifest", None, {"report": "complete"}
    monkeypatch.setattr(natural, "compile_candidate", compile_full)
    platform = full_limits(max_requests=4)
    value = use._bound_review_from_facts(dict(id="cold"), snapshot, release, platform, family, body, frozen, checked)
    assert value[0][family.field + "_run_id"] == "cold"
    assert trace == [(checked["effective_candidate"], platform.model_dump())]
    broken = copy.deepcopy(frozen)
    broken["reviewed"]["approved_grant_state"].append(dict(id="extra"))
    denied(lambda: use._bound_review_from_facts(dict(id="cold"), snapshot, release, platform, family, body, broken, checked))
    assert len(trace) == 1
    meta = SimpleNamespace(model_dump=lambda: {"complete": "meta"})
    first = use._audit_from_facts("base-full", meta, {"seal": "all"}, body, frozen)
    assert first != use._audit_from_facts("base-full", meta, {"seal": "all"}, body, broken)


def test_stage_partial_fields_do_not_form_authority_and_clock_roles(local_origin):
    f = local_origin
    contract = f.worker.pa_trial.contract
    target = contract.bindings[1]
    bound = dict(source=f.origin[2], goal=f.origin[3], app_run=dict(id="a"))
    gate._stage_target_from_facts(bound, target)
    denied(lambda: gate._stage_target_from_facts({**bound, "source": {**bound["source"], "content": "same hash is insufficient"}}, target))
    first = contract.bindings[0]
    frozen = SimpleNamespace(source_goal_card=SimpleNamespace(model_dump=lambda: dict(card_id=first.card_id,
        version=first.goal_version, fingerprint=first.goal_fingerprint, snapshot=first.goal_snapshot.model_dump())),
        application_generation=SimpleNamespace(version="goal-natural-spec-application.v1"), request_model=contract.model)
    gate._stage_generate_from_facts(contract, SimpleNamespace(approved_at=1.0), {"created_at": 2.0}, frozen)
    denied(lambda: gate._stage_generate_from_facts(contract, SimpleNamespace(approved_at=3.0), {"created_at": 2.0}, frozen))
    job = dict(id="cold", fingerprint="accepted", runtime_id="actual-cold-runtime", created_at=10.0)
    fields = gate._stage_authority_fields_from_facts(contract, "cold", {}, job, bound,
        dict(id="i", revision=2), f.draft, dict(id="release", fingerprint="rfp"), "gen", {"all": [1, 2]}, target)
    assert fields["runtime_id"] == "actual-cold-runtime" != contract.runtime_id
    assert "authorization_fingerprint" not in fields
    with pytest.raises(ValueError):
        gate.StageAuthority(**fields)
    clock_contract = SimpleNamespace(limits=full_limits(run_seconds=40))
    manifest = SimpleNamespace(runtime_limits=full_limits(run_seconds=20))
    spec._bound_clock_from_facts(dict(created_at=10.0, deadline=30.0), job, clock_contract, manifest)
    denied(lambda: spec._bound_clock_from_facts(dict(created_at=10.0, deadline=50.0), job, clock_contract, manifest))
    snapshot = {"input": {"all": [1, 2]}}
    plan = spec._bound_plan_from_facts(f.draft, snapshot, f.origin[2])
    assert plan == dict(definition=f.draft["candidate"], input=snapshot["input"],
        plan_fingerprint=fingerprint(f.draft["candidate"]), source_hash=f.origin[2]["hash"])


def test_strict_missing_facts_and_same_handoff_reentry(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with apps._cold_graph_origin_facts(f.worker, c, f.inputs, "cold", {},
                    f.user, f.draft, f.limits, f.origin):
                pytest.fail("Missing roles cannot publish facts")
        with pytest.raises(DomainError):
            with apps._cold_graph_origin_facts(f.worker, c, f.inputs, "cold", f.roles,
                    f.user, f.draft, f.limits, (None, {}, {}, {})):
                pytest.fail("Missing origin cannot publish facts")
        with pytest.raises(DomainError):
            with handoff(f, c) as facts:
                def reenter(*args):
                    denied(lambda: validate(f, c, facts))
                monkeypatch.setattr(text_continuations, "draft_gate", reenter)
                validate(f, c, facts)
        assert not facts.active and "verify_origin" not in f.trace


@pytest.mark.parametrize("change", ["limits_dict", "origin_list", "engine"])
def test_strict_equal_values_cannot_change_fact_shapes_or_original_engine(local_origin, monkeypatch, change):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with handoff(f, c) as facts:
                with monkeypatch.context() as patch:
                    if change == "limits_dict":
                        f.roles["source"] = f.roles["source"].model_dump()
                    elif change == "origin_list":
                        facts.origin = list(facts.origin)
                    else:
                        replacement = object()
                        patch.setattr(c, "engine", replacement)
                        patch.setattr(f.store, "engine", replacement)
                    validate(f, c, facts)
        assert not facts.active and not f.trace

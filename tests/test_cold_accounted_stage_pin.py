"""Local native parent boundaries; no Worker/model/transport or full G0."""

import ast
from pathlib import Path

import pytest
from accounted_sqlite_fixture import seed_cold
from sqlalchemy import update
from sqlalchemy.exc import ResourceClosedError
from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import resolve
from test_cold_accounted_sqlite import sql_facts as sql_facts

from sim2act import cold_accounted as owned
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act.db import grants
from sim2act.errors import DomainError


def old_pin(s, facts):
    gate._graph_trial_pin(s.graph, s.f.store, s.c)
    gate._graph_trial_stage_raw(s.graph, facts, _owned=s.mode)


def pin(s, facts):
    gate._graph_trial_stage_parent_pin(s.graph, s.f.store, s.c, facts, _owned=s.mode)


def test_same_call_one_codec_all_pure_associations_and_public_self_pins(sql_facts, monkeypatch):
    f = sql_facts
    seed_cold(f)
    with f.store.tx() as c, native_segment(f, c) as s:
        codec, families, records = [], [], []
        original = runtime._cold_graph_bytes
        family = owned._OwnedPrewriteMode._OwnedPrewriteMode__family_current
        record = owned._OwnedPrewriteMode._OwnedPrewriteMode__run_current

        def encode(value):
            codec.append(1)
            return original(value)

        def family_join(self, graph, value, role):
            families.append(role)
            return family(self, graph, value, role)

        def run_join(self, value, item):
            records.append(value.role)
            return record(self, value, item)

        monkeypatch.setattr(runtime, "_cold_graph_bytes", encode)
        monkeypatch.setattr(
            owned._OwnedPrewriteMode, "_OwnedPrewriteMode__family_current", family_join
        )
        monkeypatch.setattr(owned._OwnedPrewriteMode, "_OwnedPrewriteMode__run_current", run_join)
        for facts, runs in ((s.stage, ["generate", "source"]), (s.cold_stage, ["generate"])):
            codec.clear()
            families.clear()
            records.clear()
            old_pin(s, facts)
            old_counts = len(codec), list(families), list(records)
            codec.clear()
            families.clear()
            records.clear()
            pin(s, facts)
            assert old_counts[0] == 7 and len(codec) == 1
            assert families == old_counts[1] == ["generate", "generate", "source"]
            assert records == old_counts[2] == runs
        for call in (
            lambda: s.mode.assert_family(s.graph, s.source, "source"),
            lambda: s.mode.assert_run("source", s.source.run),
            lambda: s.mode.assert_stage(s.stage),
            lambda: gate._graph_trial_stage_raw(s.graph, s.stage, _owned=s.mode),
        ):
            codec.clear()
            call()
            assert codec


@pytest.mark.parametrize(
    "damage",
    [
        "generate_family",
        "generate_run",
        "raw",
        "metadata",
        "source_run",
        "cold_job",
        "bound",
        "source_family",
        "draft",
        "target",
        "goal",
    ],
)
def test_original_relation_rejections_and_new_scope_close(sql_facts, damage):
    f = sql_facts
    seed_cold(f)
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        cold = damage in ("cold_job", "source_family", "draft", "target", "goal")
        facts = list(s.cold_stage if cold else s.stage)
        if damage == "generate_family":
            facts[6] = s.source
        elif damage == "generate_run":
            facts[4] = s.source.run
        elif damage == "raw":
            facts[2] = dict(facts[2])
        elif damage == "metadata":
            facts[3] = dict(facts[3])
        elif damage == "source_run":
            facts[0] = s.generated.run
        elif damage == "cold_job":
            facts[0] = dict(facts[0])
        elif damage == "bound":
            facts[1] = {}
        elif damage == "source_family":
            facts[7] = s.generated
        else:
            extraction = list(facts[8])
            index = {"draft": 0, "target": 2, "goal": 3}[damage]
            extraction[index] = dict(extraction[index])
            facts[8] = tuple(extraction)
        with pytest.raises(DomainError) as original:
            old_pin(s, facts)
        with pytest.raises(DomainError) as changed:
            pin(s, facts)
        assert original.value.code == changed.value.code
        assert not s.mode.active and not s.mode.scope._issued
        raise changed.value


@pytest.mark.parametrize("damage", ["frontier", "revoke", "write", "rollback", "stop"])
def test_each_call_rechecks_mutation_authority_transaction_stop(sql_facts, damage):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        pin(s, s.stage)
        if damage == "frontier":
            s.graph.inputs["cold-trial:complete"]["source_proof"]["changed"] = True
        elif damage == "revoke":
            c.execute(update(grants).values(revoked=True))
        elif damage == "write":
            c.execute(update(grants).values(revision=grants.c.revision + 1))
        elif damage == "rollback":
            c.rollback()
        else:
            f.worker.stop.set()
        pin(s, s.stage)
    assert not s.mode.active and not s.mode.scope._issued


def test_closed_connection_pin_refuses_before_existing_fixture_cleanup(sql_facts):
    f = sql_facts
    # The existing source-read/Store.tx finalizers access c.info after a forced
    # close. Separate that existing fixture exit from the pin's exact refusal.
    with pytest.raises(ResourceClosedError), f.store.tx() as c, native_segment(f, c) as s:
        pin(s, s.stage)
        c.close()
        with pytest.raises(DomainError) as refusal:
            pin(s, s.stage)
        assert refusal.value.code == "VERSION_CONFLICT"
        assert not s.mode.active and not s.mode.scope._issued
        raise refusal.value


def test_ready_dispatch_never_calls_bool_before_original_first_pin(sql_facts, monkeypatch):
    calls = []

    class ForeignBool:
        def __bool__(self):
            calls.append("bool")
            raise AssertionError("ready callback before first pin")

    marker = DomainError("VERSION_CONFLICT", "original first pin")

    def first_pin(*args):
        raise marker

    f = sql_facts
    with pytest.raises(DomainError) as refusal, f.store.tx() as c, native_segment(f, c) as s:
        s.candidate.owned_ready = ForeignBool()
        with monkeypatch.context() as m:
            m.setattr(gate, "_graph_trial_pin", first_pin)
            pin(s, s.stage)
    assert refusal.value is marker and calls == []


def test_foreign_native_and_extraction_never_execute_callbacks(sql_facts):
    f = sql_facts
    seed_cold(f)
    calls = []

    class Foreign:
        def __getattr__(self, name):
            calls.append(name)
            raise AssertionError("foreign native getter")

        def __iter__(self):
            calls.append("iter")
            raise AssertionError("foreign extraction iterator")

    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        facts = list(s.cold_stage)
        facts[8] = Foreign()
        pin(s, facts)
    assert calls == []
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        s.mode._native = Foreign()
        pin(s, s.stage)
    assert calls == []


def test_default_parent_order_and_exact_two_callsites(monkeypatch):
    calls = []
    monkeypatch.setattr(gate, "_graph_trial_pin", lambda *args: calls.append("pin"))
    monkeypatch.setattr(
        gate, "_graph_trial_stage_raw", lambda *args, **kwargs: calls.append(("stage", kwargs))
    )
    gate._graph_trial_stage_parent_pin(None, None, None, None)
    assert calls == ["pin", ("stage", {})]
    root = Path(__file__).resolve().parents[1] / "src/sim2act"
    for filename, expected in [
        ("natural_live_admission.py", ["_graph_run_context"]),
        ("natural_source_archives.py", ["_graph_resolve_trial_source"]),
    ]:
        tree = ast.parse((root / filename).read_text())
        routed = []
        for function in tree.body:
            if (
                isinstance(function, ast.FunctionDef)
                and function.name != "_graph_trial_stage_parent_pin"
            ):
                if any(
                    isinstance(n, ast.Call)
                    and (
                        getattr(n.func, "id", None) == "_graph_trial_stage_parent_pin"
                        or getattr(n.func, "attr", None) == "_graph_trial_stage_parent_pin"
                    )
                    for n in ast.walk(function)
                ):
                    routed.append(function.name)
        assert routed == expected


def test_real_source_receipt_and_complete_slot_gate_remain(sql_facts):
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c) as s:
        resolved = resolve(s, _owned=s.mode)
        assert resolved.public_receipt["source_run_id"] == f.source_id
        index, slot = next(
            (i, slot) for i, slot in enumerate(s.state.slots) if slot.identity.stage == "source"
        )
        # Same aid but changed non-aid Slot data must still fail the original
        # full domain equality when source consumers cross the ledger boundary.
        changed = slot.model_copy(update={"accepted": not slot.accepted})
        slots = list(s.state.slots)
        slots[index] = changed
        altered = s.state.model_copy(update={"slots": tuple(slots)})
        with pytest.raises(DomainError):
            owned._archive_chain(s.source, altered, resolved)


def test_typed_cohort_still_rechecks_after_composite(sql_facts):
    f = sql_facts
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        models = []
        gate._graph_trial_stage_models(s.graph, f.store, c, models, s.stage, _owned=s.mode)
        guard = gate._trial_typed_guard(lambda: pin(s, s.stage), models)
        guard()
        object.__setattr__(f.frozen.limits, "run_seconds", f.frozen.limits.run_seconds - 1)
        guard()
    assert not s.mode.active


def test_query_return_revocation_cannot_cross_new_parent(sql_facts, monkeypatch):
    f = sql_facts
    calls = []
    with pytest.raises(DomainError), f.store.tx() as c, native_segment(f, c) as s:
        original = gate._approved

        def revoke_after_query(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append("approved-return")
            c.execute(update(grants).values(revoked=True))
            return result

        monkeypatch.setattr(gate, "_approved", revoke_after_query)
        resolve(s, _owned=s.mode)
    assert calls == ["approved-return"] and not s.mode.active

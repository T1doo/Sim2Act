"""Post-epoch existing raw reads fuse only fixed presence/get arithmetic."""

import pytest
from test_cold_extract_parse import local_origin as local_origin
from test_cold_extract_parse import no_external_transport as no_external_transport

from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act.errors import DomainError


def scope(f, c):
    return runtime._cold_graph_read(f.worker, c, f.inputs, f.roles, "post")


def reader(f, c, guard, key, value):
    facts = runtime._ColdRunFacts(f.store, c, f.inputs["run"], guard)
    facts._put(key, value)
    return facts


def test_hit_has_one_complete_pin_and_same_original_value(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        value = [{"complete": ["same"]}]
        facts = reader(f, c, guard, "model-reserved", value)
        start = guard._diagnostic_counts[1]
        assert facts.model_reserved() is value
        assert guard._diagnostic_counts[1] - start == 1
        with monkeypatch.context() as patch:
            patch.setattr(runtime, "_raw_read_eligible", lambda *args: False)
            start = guard._diagnostic_counts[1]
            assert facts.model_reserved() is value
            assert guard._diagnostic_counts[1] - start == 2


@pytest.mark.parametrize("value", [None, False, []])
def test_none_false_empty_are_hits_not_missing(local_origin, value):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts = reader(f, c, guard, "effect:synthetic", value)
        assert facts.effect("synthetic") is value
        assert facts._read_loaded("absent") is runtime._RAW_READ_MISS


def test_input_mutation_is_still_sticky(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with scope(f, c) as guard:
                value = [{"complete": [1]}]
                facts = reader(f, c, guard, "model-reserved", value)
                value[0]["complete"].append(2)
                facts.model_reserved()
        assert not guard.active


def test_unknown_get_shadow_keeps_old_callback_and_error(local_origin):
    f = local_origin
    error = ValueError("synthetic unknown getter")
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with scope(f, c) as guard:
                facts = reader(f, c, guard, "model-reserved", [])

                def unknown(name):
                    calls.append(name)
                    raise error

                facts._get = unknown
                facts.model_reserved()
        assert caught.value is error and calls == ["model-reserved"]
        assert not guard.active


def test_unknown_source_current_keeps_original_detection(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with scope(f, c) as guard:
                value = []
                facts = reader(f, c, guard, "model-reserved", value)
                current = pb._source_reads_current

                def changed(*args):
                    facts._raw["model-reserved"] = ["unproved"]
                    return current(*args)

                with monkeypatch.context() as patch:
                    patch.setattr(pb, "_source_reads_current", changed)
                    facts.model_reserved()
        assert not guard.active


@pytest.mark.parametrize("method", ["input_key", "input_bytes"])
def test_unknown_graph_method_shadow_is_not_fused(local_origin, method):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts = reader(f, c, guard, "model-reserved", [])
        setattr(guard, method, lambda **kwargs: calls.append("unknown"))
        assert not runtime._raw_read_eligible(facts, "model-reserved")
        assert calls == []
        delattr(guard, method)


def test_unknown_graph_codec_is_not_fused(local_origin, monkeypatch):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts = reader(f, c, guard, "model-reserved", [])
        with monkeypatch.context() as patch:
            patch.setattr(runtime, "_cold_graph_bytes", lambda *args: calls.append("unknown"))
            assert not runtime._raw_read_eligible(facts, "model-reserved")
        assert calls == []


def test_unknown_pickler_persistent_hook_is_not_fused(local_origin, monkeypatch):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts = reader(f, c, guard, "model-reserved", [])
        with monkeypatch.context() as patch:
            patch.setattr(
                runtime._ColdGraphPickler,
                "persistent_id",
                lambda *args: calls.append("unknown"),
                raising=False,
            )
            assert not runtime._raw_read_eligible(facts, "model-reserved")
        assert calls == []


@pytest.mark.parametrize(
    "dependency", ["transaction", "checkpoint", "in_transaction", "get_transaction"]
)
def test_unknown_dynamic_dependency_is_not_fused(local_origin, monkeypatch, dependency):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts = reader(f, c, guard, "model-reserved", [])
        owner, name = {
            "transaction": (pb, "_source_transaction"),
            "checkpoint": (runtime._raw_read_settlement, "checkpoint"),
            "in_transaction": (c, "in_transaction"),
            "get_transaction": (c, "get_transaction"),
        }[dependency]
        with monkeypatch.context() as patch:
            patch.setattr(owner, name, lambda *args: calls.append("unknown"))
            assert not runtime._raw_read_eligible(facts, "model-reserved")
        assert calls == []


@pytest.mark.parametrize(
    "dependency", ["driver", "worker", "clock", "ident", "info", "settings", "proofs", "stop"]
)
def test_dynamic_access_and_scalar_boundaries_fall_back(local_origin, monkeypatch, dependency):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts = reader(f, c, guard, "model-reserved", [])
        with monkeypatch.context() as patch:
            if dependency == "driver":
                patch.setattr(c.engine.dialect, "get_driver_connection", lambda *a: calls.append(1))
            elif dependency == "worker":
                patch.setattr(type(f.worker), "store", property(lambda *a: calls.append(1)))
            elif dependency == "clock":
                patch.setattr(
                    runtime._raw_read_settlement.time, "monotonic", lambda *a: calls.append(1)
                )
            elif dependency == "ident":
                patch.setattr(pb, "get_ident", lambda *a: calls.append(1))
            elif dependency == "info":
                patch.setitem(c.info, "source_proof_write_epoch", object())
            elif dependency == "settings":
                patch.setitem(guard.settings_values, "data_dir", object())
            elif dependency == "proofs":
                patch.setattr(facts, "_receipt_proofs", [object()])
            elif dependency == "stop":
                patch.setattr(f.worker, "stop", object())
            assert not runtime._raw_read_eligible(facts, "model-reserved")
        assert calls == []


@pytest.mark.parametrize("dependency", ["event_flag", "diagnostic_container", "diagnostic_item"])
def test_internal_bookkeeping_cannot_run_foreign_callbacks(local_origin, monkeypatch, dependency):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts = reader(f, c, guard, "model-reserved", [])
        with monkeypatch.context() as patch:
            if dependency == "event_flag":
                patch.setattr(guard.stop, "_flag", object())
            elif dependency == "diagnostic_container":
                patch.setattr(guard, "_diagnostic_counts", (0, 0))
            else:
                patch.setattr(guard, "_diagnostic_counts", [object(), 0])
            assert not runtime._raw_read_eligible(facts, "model-reserved")


def seeded_reader(f, c, guard):
    from sim2act.db import runs
    from sim2act.text_workflows import RunScopeInput

    user, pid, rid = f.user, f.worker.pa_trial.contract.project_id, "synthetic-seeded-run"
    scope_input = RunScopeInput(**{key: "synthetic" for key in RunScopeInput.model_fields})
    prefix = pb._ColdSourceAuditPrefix(
        guard, f"pb-source-audit:{user}:{pid}:{rid}", user, pid, rid, scope_input, {}, {}, {}
    )
    guard.add(prefix.key, prefix.fields())
    native = {}
    guard.add(prefix.key + ":native", native)
    job = {str(key): None for key in runs.c.keys()}
    job.update(id=rid, principal_id=user, project_id=pid)
    rows = {
        key: None
        for key in (
            "scope",
            "seal",
            "original_audit",
            "original",
            "run",
            "contract",
            "binding",
            "app_run",
            "typed",
            "release",
            "attempts",
            "operations",
            "intents",
            "effects",
            "events",
            "reservations",
            "origin_marker",
            "origin_seals",
            "current_goal",
            "current_goal_versions",
        )
    }
    rows.update(run=[job], attempts=[], operations=[])
    audit = pb._ColdSourceAuditFacts(
        prefix, prefix.key + ":complete", native, rows, "synthetic-digest"
    )
    guard.add(audit.key, audit.fields())
    seed = runtime._cold_run_raw_seed(f.store, c, guard, audit)
    facts = runtime._ColdRunFacts(f.store, c, seed.job, guard, raw_seed=seed)
    facts._put("model-reserved", [])
    return facts, seed


def test_actual_seed_shape_reduces_internal_pins_and_loaded_read(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, seed = seeded_reader(f, c, guard)
        assert runtime._raw_read_eligible(facts, "attempts")
        start = guard._diagnostic_counts[1]
        facts.check(f.store, c, facts.job)
        assert guard._diagnostic_counts[1] - start == 2
        start = guard._diagnostic_counts[1]
        assert facts.model_reserved() is facts._raw["model-reserved"]
        assert guard._diagnostic_counts[1] - start == 2
        with monkeypatch.context() as patch:
            patch.setattr(runtime, "_raw_read_eligible", lambda *args: False)
            start = guard._diagnostic_counts[1]
            facts.check(f.store, c, facts.job)
            assert guard._diagnostic_counts[1] - start == 4
            start = guard._diagnostic_counts[1]
            facts.model_reserved()
            assert guard._diagnostic_counts[1] - start == 8


@pytest.mark.parametrize("part", ["job", "attempts", "audit", "alias"])
def test_seed_changes_still_fail_sticky(local_origin, part):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with scope(f, c) as guard:
                facts, seed = seeded_reader(f, c, guard)
                if part == "job":
                    seed.job["cancel_intent"] = True
                elif part == "attempts":
                    seed.attempt_rows.append({"unproved": True})
                elif part == "audit":
                    seed.audit.rows["unused"] = ["changed"]
                else:
                    facts._raw["attempts"] = []
                facts.model_reserved()
        assert not guard.active


def test_unknown_seed_fields_retains_original_error(local_origin, monkeypatch):
    f = local_origin
    original, calls = ValueError("synthetic seed field hook"), []
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with scope(f, c) as guard:
                facts, seed = seeded_reader(f, c, guard)

                def changed(self):
                    calls.append(1)
                    raise original

                with monkeypatch.context() as patch:
                    patch.setattr(runtime._ColdRunRawSeed, "fields", changed)
                    assert not runtime._raw_read_eligible(facts, "attempts")
                    facts.model_reserved()
        assert caught.value is original and calls == [1]
        assert not guard.active


def test_seed_qualification_never_compares_foreign_metaclass():
    calls = []

    class ForeignMeta(type):
        def __eq__(self, other):
            calls.append("foreign equality")
            return False

    class Foreign(metaclass=ForeignMeta):
        pass

    assert not runtime._raw_seed_plain([Foreign()])
    assert not runtime._raw_seed_plain({Foreign(): 1})
    assert calls == []


@pytest.mark.parametrize(
    "change", ["dump_code", "metadata", "row_keys", "view_iter", "prefix_shadow"]
)
def test_unknown_seed_code_is_not_selected(local_origin, monkeypatch, change):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, seed = seeded_reader(f, c, guard)
        with monkeypatch.context() as patch:
            if change == "dump_code":

                def unknown_dump(self, *args, **kwargs):
                    return {"unknown": True}

                patch.setattr(runtime._RAW_SEED_SCOPE_DUMP, "__code__", unknown_dump.__code__)
            elif change == "metadata":
                patch.setattr(runtime._raw_seed_db, "runs", object())
            elif change == "row_keys":
                patch.setattr(runtime._ColdGraphRowMapping, "keys", lambda *a: calls.append(1))
            elif change == "view_iter":
                patch.setattr(runtime._RawKeyView, "__iter__", lambda *a: calls.append(1))
            else:
                object.__setattr__(seed.audit.prefix, "fields", lambda *a: calls.append(1))
            assert not runtime._raw_read_eligible(facts, "attempts")
            if change == "prefix_shadow":
                object.__delattr__(seed.audit.prefix, "fields")
        assert calls == []


def test_seed_real_sql_row_and_foreign_index_lookup(local_origin):
    from sqlalchemy import select

    from sim2act.db import principals

    f = local_origin
    calls = []
    with f.store.tx() as c:
        row = c.execute(select(principals)).mappings().first()
        assert row is not None and runtime._raw_seed_plain([row])
        parent = object.__getattribute__(row, "_parent")
        data = object.__getattribute__(row, "_data")

        class Trap:
            def __hash__(self):
                return hash("id")

            def __eq__(self, other):
                calls.append("foreign index equality")
                return False

        index = dict(object.__getattribute__(row, "_key_to_index"))
        index[Trap()] = 0
        forged = runtime._ColdGraphRowMapping(parent, None, index, data)
        calls.clear()
        assert not runtime._raw_seed_plain([forged])
        assert calls == []


def test_seed_view_setter_is_not_selected(local_origin, monkeypatch):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, seed = seeded_reader(f, c, guard)
        with monkeypatch.context() as patch:
            patch.setattr(runtime._RawKeyView, "__setattr__", lambda *a: calls.append(1))
            assert not runtime._raw_read_eligible(facts, "attempts")
        assert calls == []

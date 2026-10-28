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

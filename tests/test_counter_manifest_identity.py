"""Equal typed values share identity; every original counter path still runs."""

import pytest
from test_cold_extract_parse import local_origin as local_origin
from test_cold_extract_parse import no_external_transport as no_external_transport
from test_cold_release_stages import read_scope

from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act.contracts import AppManifest
from sim2act.errors import DomainError


def reader(f, c, guard):
    facts = runtime._ColdRunFacts(f.store, c, f.inputs["run"], guard)
    facts.pin_manifest(f.origin[0])
    return facts


def test_equivalent_parses_do_not_grow_manifest_registry(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
        facts = reader(f, c, guard)
        original = f.origin[0]
        before = guard.key
        for _ in range(10):
            fresh = AppManifest.model_validate(original.model_dump())
            runtime._counter_checkpoint(c, facts.job, facts)
            selected = facts.canonical_counter_manifest(fresh)
            assert selected is original
            assert facts.pin_manifest(selected) == "counter-manifest:0"
        assert len(facts._manifests) == 1 and guard.key == before


def test_distinct_complete_limits_retains_original_new_instance(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
        facts = reader(f, c, guard)
        raw = f.origin[0].model_dump()
        raw["runtime_limits"]["max_output_tokens"] -= 1
        fresh = AppManifest.model_validate(raw)
        runtime._counter_checkpoint(c, facts.job, facts)
        assert facts.canonical_counter_manifest(fresh) is fresh
        assert facts.pin_manifest(fresh) == "counter-manifest:1"


def test_current_pin_still_rejects_model_change(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with read_scope(f, c) as guard:
                facts = reader(f, c, guard)
                f.origin[0].runtime_limits.max_output_tokens -= 1
                runtime._counter_checkpoint(c, facts.job, facts)
        assert not guard.active


def test_unknown_manifest_getter_selects_original_without_callback(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
        facts = reader(f, c, guard)
        fresh = AppManifest.model_validate(f.origin[0].model_dump())
        calls = []
        with monkeypatch.context() as patch:
            patch.setattr(
                AppManifest, "runtime_limits", property(lambda self: calls.append(1)), raising=False
            )
            assert facts.canonical_counter_manifest(fresh) is fresh
        assert calls == []


def test_unknown_equality_helper_falls_back_without_callback(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), read_scope(f, c) as guard:
        facts = reader(f, c, guard)
        fresh = AppManifest.model_validate(f.origin[0].model_dump())
        calls = []
        with monkeypatch.context() as patch:
            patch.setattr(
                runtime._row_native_code, "_trial_typed_equal", lambda *args: calls.append(1)
            )
            assert facts.canonical_counter_manifest(fresh) is fresh
        assert calls == []

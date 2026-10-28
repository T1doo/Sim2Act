"""Content accelerator only; these units confer no settlement authority."""

import json
from contextlib import contextmanager

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from test_cold_extract_parse import local_origin as local_origin
from test_cold_extract_parse import no_external_transport as no_external_transport
from test_loaded_raw_segment import scope

from sim2act import _model_input_structure as selected
from sim2act import natural_spec_runtime as r
from sim2act import pb_natural_specs as pb
from sim2act.contracts import Limits


def limit():
    return Limits(max_requests=2, max_tools=4, max_repairs=0,
        max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)


@contextmanager
def content(f, inputs=None):
    """Real graph/SQL lifetime, unvalidated identity shell for pure data units."""
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as graph:
        p = object.__new__(r._ModelSettlementRead)
        p.inputs = inputs if inputs is not None else dict(nested=[dict(version=1)], limits=limit())
        p.connection, p.transaction = c, c.get_transaction()
        p.driver = c.connection.driver_connection
        p.changes, p.thread = p.driver.total_changes, r.get_ident()
        p.scope_nonce = object()
        c.info["_model_settlement_scope"] = p.scope_nonce
        p.active, p.state, p.authorities = True, "READY", set()
        p._input_structure, p._byte_digests = None, {}
        p._input_key_calls = p._input_structure_hits = 0
        p.input_fingerprint = p._inputs_key()
        # No graph/check/permission result is supplied by this carrier.
        p.post_graph = object.__new__(r._ColdTrialGraph)
        p.post_graph.guard = graph
        assert selected._qualified(p)
        try:
            yield p
        finally:
            p.invalidate()
            c.info.pop("_model_settlement_scope", None)


def test_current_full_walk_replaces_repeated_canonical_encoding(local_origin):
    with content(local_origin) as p:
        assert p._inputs_current()
        assert p._input_structure is not None
        initial = p._input_key_calls
        for _ in range(4):
            assert p._inputs_current()
        assert p._input_key_calls == initial
        assert p._input_structure_hits == 5
    assert p._input_structure is None


@pytest.mark.parametrize("change", ["nested", "limit", "signed_zero", "bytes"])
def test_complete_current_content_change_uses_original_rejection(local_origin, change):
    inputs = dict(nested=[dict(version=1)], limits=limit(), signed=0.0, wire=b"old")
    with content(local_origin, inputs) as p:
        assert p._inputs_current()
        if change == "nested":
            inputs["nested"][0]["version"] = 2
        elif change == "limit":
            inputs["limits"].max_requests += 1
        elif change == "signed_zero":
            inputs["signed"] = -0.0
        else:
            inputs["wire"] = b"new"
        assert not p._inputs_current()
        assert p._input_structure is None


@pytest.mark.parametrize("change", ["order", "tuple", "alias", "hidden_row"])
def test_stricter_structure_miss_preserves_original_canonical_acceptance(local_origin, change):
    shared = [1]
    row = RowMapping(SimpleResultMetaData(["visible"]), None, {"visible": 0}, ("kept", [1]))
    inputs = dict(ordered=dict(a=1, b=2), values=[shared, shared], row=row)
    with content(local_origin, inputs) as p:
        assert p._inputs_current()
        start = p._input_key_calls
        if change == "order":
            inputs["ordered"] = dict(b=2, a=1)
        elif change == "tuple":
            inputs["values"] = tuple(inputs["values"])
        elif change == "alias":
            inputs["values"] = [[1], [1]]
        else:
            row._data[1].append(2)
        assert p._inputs_current()
        assert p._input_key_calls > start
        assert p._input_structure is None


@pytest.mark.parametrize("warm", [False, True])
def test_pure_reducer_representation_error_falls_back_to_canonical(local_origin, warm):
    limits = limit()
    with content(local_origin, dict(limits=limits)) as p:
        if warm:
            assert p._inputs_current()
        object.__setattr__(limits, "__pydantic_private__", {"synthetic": 1})
        assert p._inputs_current()
        assert p._input_structure is None


def test_json_configuration_change_never_reuses_old_interpretation(local_origin, monkeypatch):
    with content(local_origin) as p:
        assert p._inputs_current()
        original = json.dumps
        def different(*args, **kwargs):
            return original(*args, **kwargs) + " "
        with monkeypatch.context() as patch:
            patch.setattr(json, "dumps", different)
            assert not p._inputs_current()
            assert p._input_structure is None


def test_serializer_configuration_change_uses_original_current_output(local_origin, monkeypatch):
    with content(local_origin) as p:
        assert p._inputs_current()
        original = Limits.model_dump
        def different(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            out["max_requests"] += 1
            return out
        with monkeypatch.context() as patch:
            patch.setattr(Limits, "model_dump", different)
            assert not p._inputs_current()
            assert p._input_structure is None


def test_scope_nonce_change_declines_content_acceleration(local_origin):
    with content(local_origin) as p:
        assert p._inputs_current()
        p.scope_nonce = object()
        assert selected.same(p) is None
        assert p._input_structure is None


@pytest.mark.parametrize("target", ["instance", "class"])
def test_unknown_proof_method_is_not_used_to_calibrate(local_origin, monkeypatch, target):
    with content(local_origin) as p:
        def unknown(*args):
            pytest.fail("Unknown proof method calibrated a content capsule")
        with monkeypatch.context() as patch:
            patch.setattr(p if target == "instance" else type(p), "_inputs_key", unknown)
            assert selected.same(p) is None
            assert p._input_structure is None


def test_unknown_exception_origin_is_not_a_representation_miss():
    from sim2act.errors import DomainError
    try:
        raise DomainError("VERSION_CONFLICT", "synthetic unknown callback")
    except DomainError as error:
        assert not selected._representation_miss(error)

"""Proposed pure encoder units. Not run by the independent reviewer.

No model/claim/authority, graph producer or semantic P-B acceptance.
Exact local CGR scope checks use synthetic SQLite/Worker identity pins.
One isolated in-memory SQLite metadata copy checks actual full RowMapping keys.
The private helper must first be applied by the repository's sole writer.
"""

import copy
import hashlib
import pickle
import pickletools
import threading
import time
from collections.abc import Mapping

import httpx
import pytest
from sqlalchemy import Column, MetaData, Table, create_engine, insert, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from test_natural_spec_apps import recipe
from test_pb_live_source_contract import material

from sim2act import natural_live_admission as admission
from sim2act import natural_spec_runtime as runtime
from sim2act import pb_natural_specs as pb
from sim2act.contracts import Limits
from sim2act.db import new_id, runs
from sim2act.errors import DomainError
from sim2act.production_trial_admission import canonical_quota_subject
from sim2act.spec_production import ProductionTrialBinding
from sim2act.worker import Worker


@pytest.fixture(autouse=True)
def no_transports(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("CGR encoder units forbid every HTTP/Mock transport")

    for cls, name in ((httpx.HTTPTransport, "handle_request"),
            (httpx.AsyncHTTPTransport, "handle_async_request"),
            (httpx.MockTransport, "handle_request"),
            (httpx.MockTransport, "handle_async_request")):
        monkeypatch.setattr(cls, name, forbidden)


def limits():
    return Limits(max_requests=4, max_tools=4, max_repairs=1,
        max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)


def inputs():
    first = dict(id="synthetic-attempt-A", usage=dict(input_tokens=100,
        output_tokens=20, total_tokens=120), wire=b"complete-request-A",
        response=b"complete-response-A")
    second = {**copy.deepcopy(first), "id": "synthetic-attempt-B"}
    shared = dict(goal=dict(version=1, fingerprint="synthetic-goal-fp",
        snapshot=dict(content="full current Goal", clauses=["one", "two"])),
        attempts=[first, second], anchors=[dict(kind="NS_RECEIVED",
        attempt_id=first["id"], data=dict(owner="owner-A", values=[1, 2]))])
    return dict(source=shared, cold=dict(ancestor=shared), roles={
        role: limits() for role in ("source", "generate", "platform", "trial", "per_use")})


@pytest.mark.parametrize("change", ["shared_deep", "goal", "usage", "wire",
    "response", "duplicate_anchor", "remove_anchor", "anchor_field", "attempt_order"])
def test_complete_current_fields_remain_detectable(change):
    value = inputs()
    before = copy.deepcopy(value)
    key, oracle = runtime._cold_graph_inputs(value), runtime._model_inputs(value)
    assert value == before and runtime._cold_graph_inputs(value) == key
    shared = value["source"]
    assert value["cold"]["ancestor"] is shared
    if change == "shared_deep":
        shared["goal"]["snapshot"]["clauses"][1] = "changed"
    elif change == "goal":
        shared["goal"]["snapshot"]["content"] += " changed"
    elif change == "usage":
        shared["attempts"][0]["usage"]["total_tokens"] += 1
    elif change == "wire":
        shared["attempts"][0]["wire"] += b" changed"
    elif change == "response":
        shared["attempts"][0]["response"] += b" changed"
    elif change == "duplicate_anchor":
        shared["anchors"].append(shared["anchors"][0])
    elif change == "remove_anchor":
        shared["anchors"].clear()
    elif change == "anchor_field":
        shared["anchors"][0]["data"]["owner"] = "owner-B"
    else:
        shared["attempts"].reverse()
    assert runtime._model_inputs(value) != oracle
    assert runtime._cold_graph_inputs(value) != key


@pytest.mark.parametrize("role", ["source", "generate", "platform", "trial", "per_use"])
@pytest.mark.parametrize("field", list(Limits.model_fields))
def test_each_full_role_limits_field_is_read_on_every_call(role, field):
    value = inputs()
    key, oracle = runtime._cold_graph_inputs(value), runtime._model_inputs(value)
    old = value["roles"][role]
    changed = old.model_dump()
    changed[field] -= 1
    value["roles"][role] = Limits(**changed)
    assert runtime._model_inputs(value) != oracle
    assert runtime._cold_graph_inputs(value) != key


def test_native_memo_per_call_reads_exact_limits_without_instance_serializer(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("model_dump")
        raise AssertionError("Native codec must read exact Limits fields directly")

    full = limits()
    monkeypatch.setattr(Limits, "model_dump", forbidden)
    value = dict(first=full, second=[full, dict(third=full)])
    first = runtime._cold_graph_inputs(value)
    encoded = runtime._cold_graph_bytes(value)
    assert hashlib.sha256(encoded).hexdigest() == first
    assert runtime._cold_graph_inputs(value) == first
    assert runtime._cold_graph_bytes(value) == encoded
    full.max_output_tokens -= 1
    assert runtime._cold_graph_inputs(value) != first
    assert calls == []


@pytest.mark.parametrize("size", [0, 255, 65535, 65536, 65537, 579257])
def test_envelope_matches_independent_chunk_stream_across_frames_and_aliases(size):
    full = limits()
    shared = dict(wire=b"x" * size, limits=full)
    data = (shared, dict(hidden=[full, shared]))
    row = RowMapping(SimpleResultMetaData([quoted_name("visible", True)]), None,
        {"visible": 0, "unused": 1}, data)
    value = dict(first=row, again=row, shared=shared, complete_data=data)
    chunks = []

    class ChunkSink:
        def write(self, chunk):
            chunks.append(chunk)

    # The oracle has no BytesIO position or prefix. Only parse pickle opcodes;
    # the fingerprint-only marker must never be loaded or executed.
    runtime._ColdGraphPickler(ChunkSink(), protocol=5).dump(value)
    payload = b"".join(chunks)
    operations = list(pickletools.genops(payload))
    assert operations[0][0].name == "PROTO" and operations[0][1] == 5
    assert operations[-1][0].name == "STOP"
    encoded = runtime._cold_graph_bytes(value)
    assert type(encoded) is bytes
    assert encoded == b"SIM2ACT_COLD_GRAPH_PICKLE_V2\x00" + payload
    digest = hashlib.sha256(encoded).hexdigest()
    full.max_output_tokens -= 1
    assert runtime._cold_graph_bytes(value) != encoded
    assert hashlib.sha256(encoded).hexdigest() == digest


def test_envelope_preserves_pickle_import_failure_translation(monkeypatch):
    import builtins

    original_import = builtins.__import__
    error = ValueError("synthetic marker import failure")
    calls = []

    def importing(name, *args, **kwargs):
        if name == runtime.__name__:
            calls.append(name)
            raise error
        return original_import(name, *args, **kwargs)

    value = limits()
    output = runtime._ColdGraphBytesIO()
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", importing)
        with pytest.raises(pickle.PicklingError) as reference:
            runtime._ColdGraphPickler(output, protocol=5).dump(value)
        with pytest.raises(pickle.PicklingError) as caught:
            runtime._cold_graph_bytes(value)
    assert str(caught.value) == str(reference.value)
    assert calls == [runtime.__name__, runtime.__name__]


def test_envelope_keeps_original_reducer_exception_identity(monkeypatch):
    error = DomainError("VERSION_CONFLICT", "synthetic Limits reducer failure")
    calls = []

    def refusing(value):
        calls.append(value)
        raise error

    value = limits()
    monkeypatch.setattr(runtime, "_cold_graph_limit_values", refusing)
    with pytest.raises(DomainError) as caught:
        runtime._cold_graph_bytes(value)
    assert caught.value is error and len(calls) == 1 and calls[0] is value


def test_key_order_is_a_stricter_local_pin_with_complete_alias_graph():
    shared = dict(z=[1, 2], a=dict(full=b"bytes"))
    left = dict(z=shared, a=dict(z=shared, a=limits()))
    right = dict(a=dict(a=left["a"]["a"], z=shared), z=shared)
    assert runtime._model_inputs(left) == runtime._model_inputs(right)
    assert runtime._cold_graph_inputs(left) != runtime._cold_graph_inputs(right)


def test_alias_topology_keeps_all_edges_and_list_tuple_kind():
    shared = dict(goal=dict(content="same"))
    aliased = dict(a=shared, b=shared)
    independent = dict(a=copy.deepcopy(shared), b=copy.deepcopy(shared))
    assert runtime._model_inputs(aliased) == runtime._model_inputs(independent)
    assert runtime._cold_graph_inputs(aliased) != runtime._cold_graph_inputs(independent)
    assert runtime._cold_graph_inputs([shared]) != runtime._cold_graph_inputs((shared,))


@pytest.mark.parametrize("kind", ["dict", "list", "mixed"])
def test_cycles_fail_instead_of_emitting_completed_refs(kind):
    if kind == "dict":
        value = {}
        value["self"] = value
    elif kind == "list":
        value = []
        value.append(value)
    else:
        value = []
        value.append((value,))
    with pytest.raises(DomainError):
        runtime._cold_graph_validate_inputs(value)


def test_custom_mapping_and_string_key_methods_never_run():
    calls = []

    class Foreign(Mapping):
        def __iter__(self):
            calls.append("iter")
            raise AssertionError("Custom Mapping must be rejected before callback")

        def __getitem__(self, key):
            calls.append("get")
            raise AssertionError("Custom Mapping must be rejected before callback")

        def __len__(self):
            calls.append("len")
            raise AssertionError("Custom Mapping must be rejected before callback")

    class ForeignKey(str):
        def __lt__(self, other):
            calls.append("sort")
            raise AssertionError("Custom key must be rejected before sort")

    class ForeignDict(dict):
        def keys(self):
            calls.append("keys")
            raise AssertionError("dict subclass must be rejected before callback")

    for value in (Foreign(), ForeignDict(a=1), {ForeignKey("z"): 1, "a": 2}):
        with pytest.raises(DomainError):
            runtime._cold_graph_inputs(value)
    assert calls == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_values_remain_rejected_by_original_json_fingerprint(value):
    with pytest.raises(ValueError):
        runtime._cold_graph_validate_inputs(dict(value=value))


def test_unknown_reducers_and_shadowed_limits_never_dispatch():
    calls = []

    class Foreign:
        def __reduce__(self):
            calls.append("reduce")
            raise AssertionError("Unknown reducer must never execute")

        def __reduce_ex__(self, protocol):
            calls.append("reduce_ex")
            raise AssertionError("Unknown reducer must never execute")

    class ForeignDict(dict):
        def __reduce_ex__(self, protocol):
            calls.append("dict-reduce")
            raise AssertionError("Unknown dict reducer must never execute")

    class ForeignStr(str):
        def __reduce_ex__(self, protocol):
            calls.append("str-reduce")
            raise AssertionError("Unknown str reducer must never execute")

    class HostileMeta(type):
        def __eq__(cls, other):
            calls.append("metaclass-equality")
            raise AssertionError("Type gates must use identity")

    class ForeignType(metaclass=HostileMeta):
        pass

    def callback(*args, **kwargs):
        calls.append("callable")
        raise AssertionError("Foreign callable must never execute")

    shadowed = limits().model_copy(update={"model_dump": callback})
    for value in (Foreign(), ForeignDict(x=1), ForeignStr("x"), callback, shadowed, ForeignType()):
        with pytest.raises(DomainError):
            runtime._cold_graph_bytes(dict(value=value))
        with pytest.raises(DomainError):
            runtime._cold_graph_validate_inputs(dict(value=value))
    assert calls == []


def test_actual_full_sqlalchemy_row_mapping_and_trusted_quoted_keys():
    """Full column set, synthetic metadata copy only; no Store or actual Run."""
    synthetic = Table("synthetic_cgr_row", MetaData(),
        *(Column(column.name, column.type) for column in runs.c))
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as c:
            synthetic.create(c)
            values = {column.name: None for column in synthetic.c}
            values.update(id="synthetic-row", goal="full Goal",
                context=dict(messages=[dict(content="complete body")],
                    usage=dict(input_tokens=1, output_tokens=2, total_tokens=3)),
                resource_refs=["synthetic-resource-A", "synthetic-resource-A"])
            c.execute(insert(synthetic).values(values))
            row = c.execute(select(synthetic)).mappings().one()
            assert type(row) is RowMapping and set(row) == set(runs.c.keys())
            assert any(type(key) is quoted_name for key in row)
            complete = dict(row)
            plain = {str(key): value for key, value in row.items()}
            expected = runtime._cold_graph_inputs(row)
            assert runtime._cold_graph_inputs(row) == expected
            runtime._cold_graph_validate_inputs(row)
            complete_key = runtime._cold_graph_inputs(complete)
            assert complete_key != expected  # Exact SQL row marker is a stricter pin.
            assert runtime._cold_graph_inputs(plain) != expected
            assert runtime._model_inputs(complete) == runtime._model_inputs(plain)
            changed = copy.deepcopy(complete)
            changed["context"]["usage"]["input_tokens"] = 4
            assert runtime._cold_graph_inputs(changed) != complete_key
            assert row["context"]["usage"]["input_tokens"] == 1
    finally:
        engine.dispose()


def test_literal_values_cannot_collide_with_ref_or_bytes_node_shapes():
    assert runtime._cold_graph_inputs("ref") != runtime._cold_graph_inputs(["ref", 0])
    raw = b"complete bytes"
    projected = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    assert runtime._model_inputs(raw) == runtime._model_inputs(projected)
    assert runtime._cold_graph_inputs(raw) != runtime._cold_graph_inputs(projected)


def test_forged_native_row_metadata_cannot_run_key_callback():
    calls = []

    class ForeignMeta:
        @property
        def _keys(self):
            calls.append("keys")
            raise AssertionError("Forged native row metadata getter must not execute")

    forged = RowMapping(ForeignMeta(), None, {}, ())
    with pytest.raises(DomainError):
        runtime._cold_graph_bytes(forged)
    with pytest.raises(DomainError):
        runtime._cold_graph_validate_inputs(forged)
    assert calls == []


def test_actual_row_index_collision_never_dispatches_foreign_hash_or_equality():
    from sqlalchemy.engine.result import SimpleResultMetaData

    calls = []

    class CollidingKey:
        def __hash__(self):
            calls.append("hash")
            return hash("id")

        def __eq__(self, other):
            calls.append("eq")
            raise AssertionError("Native row index must not compare a foreign key")

    # Native metadata and RowMapping, but a deliberately forged index key. Its
    # construction hashes once; neither codec may hash or compare it again.
    index = {CollidingKey(): 0}
    forged = RowMapping(SimpleResultMetaData(["id"]), None, index, ("complete-id",))
    assert calls == ["hash"]
    calls.clear()
    with pytest.raises(DomainError):
        runtime._cold_graph_bytes(forged)
    with pytest.raises(DomainError):
        runtime._cold_graph_validate_inputs(forged)
    assert calls == []


@pytest.mark.parametrize("path", ["direct", "dict", "list", "tuple", "row"])
def test_incoming_validator_forbids_actual_root_by_identity_on_every_value_path(path):
    from sqlalchemy.engine.result import SimpleResultMetaData

    root = dict(existing=dict(full=b"complete", limits=limits()))
    if path == "direct":
        incoming = root
    elif path == "dict":
        incoming = dict(edge=root)
    elif path == "list":
        incoming = [root]
    elif path == "tuple":
        incoming = (root,)
    else:
        incoming = RowMapping(SimpleResultMetaData(["edge"]), None, {"edge": 0}, (root,))
    # Before insertion each input is an ordinary acyclic graph.
    runtime._cold_graph_validate_inputs(incoming)
    with pytest.raises(DomainError):
        runtime._cold_graph_validate_inputs(incoming, _forbid_root=root)
    # Equal content in another object does not create a root back-edge.
    runtime._cold_graph_validate_inputs(dict(edge=copy.deepcopy(root)), _forbid_root=root)


@pytest.mark.parametrize("mutation", ["cycle", "unsupported_builtin",
    "add_direct_backedge", "add_nested_backedge", "add_row_backedge", "add_unused_row_backedge", "add_shared_dag"])
def test_exact_cgr_check_poison_on_new_cycle_or_builtin(env, mutation, monkeypatch):
    store, settings, _, user, _, pid, _ = env
    assert store.sqlite
    trial = admission.PBTrialContract(trial_key="synthetic-codec-pin", project_id=pid,
        principal_id=user, runtime_id=new_id("runtime"),
        quota_subject=canonical_quota_subject("synthetic-codec-account"),
        software_fingerprint="b" * 64, authorization_fingerprint="c" * 64,
        bindings=[material(1), material(2)], stage_keys=dict(generate="g", source="s", cold="c"),
        expires_at=time.time() + 300, path="P-B", extraction_request_key="x",
        extraction_recipe=recipe("ordered"))
    binding = ProductionTrialBinding(trial, "synthetic-unapproved-pin", "synthetic-codec-account")
    worker = object.__new__(Worker)
    worker.store, worker.s, worker.pa_trial = store, settings, binding
    worker.id, worker.stop, worker.goal_planner_transport = "synthetic-codec-reader", threading.Event(), None
    worker._journal_trial_store, worker._journal_trial_binding = store, binding
    worker._journal_trial_drift = False
    full = limits()
    payload = dict(original=[1, 2])
    with store.tx() as c, pb._source_reads(store, c):
        with pytest.raises(DomainError):
            with runtime._cold_graph_read(worker, c, dict(payload=payload),
                    dict(source=full, generate=None, platform=full, trial=full, per_use=None), "pre") as guard:
                original_bytes = guard.input_bytes()
                assert hashlib.sha256(original_bytes).hexdigest() == guard.key
                assert guard.input_bytes() == original_bytes
                if mutation in ("add_direct_backedge", "add_nested_backedge", "add_row_backedge", "add_unused_row_backedge"):
                    from sqlalchemy.engine.result import SimpleResultMetaData

                    if mutation == "add_direct_backedge":
                        incoming = guard.inputs
                    elif mutation == "add_nested_backedge":
                        incoming = dict(edge=guard.inputs)
                    elif mutation == "add_row_backedge":
                        incoming = RowMapping(SimpleResultMetaData(["edge"]), None,
                            {"edge": 0}, (guard.inputs,))
                    else:
                        # Complete raw storage includes this unused position;
                        # installing root -> row would close the hidden cycle.
                        incoming = RowMapping(SimpleResultMetaData(["visible"]), None,
                            {"visible": 0}, ("ordinary", guard.inputs))
                    # Acyclic alone, but the new root -> incoming edge would
                    # create a cycle. Reject it before mutating the inputs.
                    runtime._cold_graph_validate_inputs(incoming)
                    with pytest.raises(DomainError):
                        guard.add("backedge", incoming)
                    assert not guard.active and "backedge" not in guard.inputs
                elif mutation == "add_shared_dag":
                    fresh = limits()
                    shared = dict(original=payload["original"], full=fresh, absent=None)
                    incoming = dict(left=shared, right=shared)
                    calls = []
                    original_validate = runtime._cold_graph_validate_inputs

                    def observe(value, *, _forbid_root=None):
                        calls.append((value, _forbid_root))
                        return original_validate(value, _forbid_root=_forbid_root)

                    with monkeypatch.context() as patch:
                        patch.setattr(runtime, "_cold_graph_validate_inputs", observe)
                        guard.add("shared", incoming)
                    assert len(calls) == 1
                    assert calls[0][0] is incoming and calls[0][1] is guard.inputs
                    assert guard.active and guard.input_key() == guard.key
                    assert guard.inputs["shared"]["left"] is guard.inputs["shared"]["right"]
                    assert shared["original"] is payload["original"]
                    # Complete bytes still cover newly accepted full Limits.
                    fresh.max_output_tokens -= 1
                    with pytest.raises(DomainError):
                        guard.check(store, c)
                    assert not guard.active
                    fresh.max_output_tokens += 1
                else:
                    if mutation == "cycle":
                        payload["changed"] = payload
                    else:
                        payload["changed"] = {1, 2}
                    with pytest.raises(DomainError):
                        guard.check(store, c)
                    assert not guard.active
                    del payload["changed"]
                # Even after removing the bad value, this scope stays poisoned.
                with pytest.raises(DomainError):
                    guard.check(store, c)


def test_foreign_limits_storage_key_is_rejected_without_hash_or_equality():
    calls = []

    class ForeignKey:
        def __hash__(self):
            calls.append("hash")
            return 0

        def __eq__(self, other):
            calls.append("equality")
            raise AssertionError("Foreign Limits key must not be compared")

    value = limits()
    # Hashing during deliberate fixture construction is outside the encoder.
    object.__getattribute__(value, "__dict__")[ForeignKey()] = 1
    calls.clear()
    for encode in (runtime._cold_graph_bytes, runtime._cold_graph_validate_inputs):
        with pytest.raises(DomainError):
            encode(dict(limits=value))
    assert calls == []

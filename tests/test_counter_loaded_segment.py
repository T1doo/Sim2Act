"""Complete already-loaded counter inputs; synthetic facts, no model execution."""

import copy
import sys
from contextlib import contextmanager

import pytest
from sqlalchemy import event
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_loaded_raw_segment import scope, seeded_reader

from sim2act import natural_spec_runtime as r
from sim2act import pb_natural_specs as pb
from sim2act.errors import DomainError


def prepared(f, c, guard, omit=None, *, count=0, marker=False, job_extra=None, change=None,
             mapping_job=False, use_seed=True):
    from sim2act.db import attempts, reservations

    context = dict(
        kind="INTERNAL_APPRUN",
        messages=[] if not count else [{"role": "user", "content": "synthetic only"}],
        requests=count,
        repairs=0,
        reserved_tokens=10 * count,
        tools=0,
        spec_family=r.codec.VERSION,
    )
    if marker:
        context[r._COUNTER_PACKET_MARKER] = "synthetic-scope"
    rows = []
    slots = {}
    for ordinal in range(count):
        aid = f"synthetic-attempt-{ordinal}"
        row = {str(key): None for key in attempts.c.keys()}
        meta = dict(
            ordinal=ordinal,
            operation_id=f"synthetic-op-{ordinal}",
            step_id=f"synthetic-step-{ordinal}",
            fence=1,
        )
        row.update(
            id=aid,
            run_id="synthetic-seeded-run",
            created_at=float(count - ordinal),
            mode="LIVE",
            request_model="intern-s2",
            status="VERIFIED",
            reserved_tokens=10,
            parameters=dict(
                natural_spec=meta,
                request_fingerprint=r.fingerprint(
                    dict(messages=context["messages"], tools=[], model="intern-s2")
                ),
            ),
        )
        rows.append(row)
        slot = {str(key): None for key in reservations.c.keys()}
        slot.update(id=aid, run_id=row["run_id"], created_at=row["created_at"])
        slots[aid] = [slot]
    raw = {
        "mode": "LIVE",
        "association": {"stage": "cold"},
        "model-operations": [row["parameters"]["natural_spec"]["operation_id"] for row in rows],
    }
    for kind in ("NS_RESERVED", "NS_RECEIVED", "NS_SETTLED", "NS_REJECTED"):
        raw["anchor-ids:" + kind] = [] if kind == "NS_REJECTED" else [row["id"] for row in rows]
    for row in rows:
        aid, meta = row["id"], row["parameters"]["natural_spec"]
        raw["reservation:" + aid] = slots[aid]
        raw["anchor:NS_RESERVED:" + aid] = [
            dict(
                attempt_id=aid,
                parameters_fingerprint=r.fingerprint(row["parameters"]),
                reserved_tokens=row["reserved_tokens"],
                request_model=row["request_model"],
                mode=row["mode"],
                created_at=row["created_at"],
                operation_id=meta["operation_id"],
                step_id=meta["step_id"],
                fence=meta["fence"],
                reservation_fingerprint=r.fingerprint(slots[aid][0]),
            )
        ]
    reserved = [dict(attempt_id=row["id"], mode="live") for row in rows]
    if change:
        change(context, rows, raw, reserved)
    facts, seed = seeded_reader(
        f,
        c,
        guard,
        job_values=dict(context=context, **(job_extra or {})),
        attempt_values=list(reversed(rows)),
        reserved_values=reserved,
        mapping_job=mapping_job,
        use_seed=use_seed,
    )
    needed = [
        "model-operations",
        *[
            "anchor-ids:" + kind
            for kind in ("NS_RESERVED", "NS_RECEIVED", "NS_SETTLED", "NS_REJECTED")
        ],
    ]
    if count:
        needed.extend(
            ["mode", *[key for key in raw if key.startswith(("reservation:", "anchor:"))]]
        )
    if marker:
        needed.append("association")
    for key in needed:
        if key != omit:
            facts._put(key, raw[key])
    return facts, seed


@contextmanager
def observe_core(callback=None):
    monitoring = sys.monitoring
    slot = next(i for i in (4, 3, 5) if monitoring.get_tool(i) is None)
    monitoring.use_tool_id(slot, "synthetic counter packet witness")
    calls = []

    def called(code, offset):
        calls.append(1)
        if callback:
            callback()

    monitoring.register_callback(slot, monitoring.events.PY_START, called)
    monitoring.set_local_events(slot, r._counter_packet_core.__code__, monitoring.events.PY_START)
    try:
        yield calls
    finally:
        monitoring.set_events(slot, 0)
        monitoring.set_local_events(slot, r._counter_packet_core.__code__, 0)
        monitoring.free_tool_id(slot)


def test_first_manifest_registration_hits_and_reduces_complete_pins(local_origin, monkeypatch):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, _ = prepared(f, c, guard)
        assert facts._manifests == []
        with observe_core() as calls:
            assert r._counters(c, facts.job, f.origin[0], _facts=facts) == []
        assert calls == [1] and len(facts._manifests) == 1
        start = guard._diagnostic_counts[1]
        assert r._counters(c, facts.job, f.origin[0], _facts=facts) == []
        fast = guard._diagnostic_counts[1] - start
        with monkeypatch.context() as patch:
            patch.setattr(r, "_cold_counter_loaded", lambda *a: r._RAW_READ_MISS)
            start = guard._diagnostic_counts[1]
            assert r._counters(c, facts.job, f.origin[0], _facts=facts) == []
            slow = guard._diagnostic_counts[1] - start
        assert fast < slow, (fast, slow)


@pytest.mark.parametrize("use_seed", [False, True])
@pytest.mark.parametrize("marker", [False, True])
@pytest.mark.parametrize("mapping_job", [True, "cursor"])
def test_actual_mapping_job_hits_without_sql_and_keeps_original_rows(
    local_origin, monkeypatch, use_seed, marker, mapping_job
):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, _ = prepared(f, c, guard, count=2, marker=marker,
            mapping_job=mapping_job, use_seed=use_seed)
        queries = []
        def sql(*args):
            queries.append(1)
        event.listen(f.store.engine, "before_cursor_execute", sql)
        try:
            start = guard._diagnostic_counts[1]
            with observe_core() as calls:
                actual = r._counters(c, facts.job, f.origin[0], _facts=facts)
            fast = guard._diagnostic_counts[1] - start
            assert calls == [1] and queries == []
            with monkeypatch.context() as patch:
                patch.setattr(r, "_cold_counter_loaded", lambda *args: r._RAW_READ_MISS)
                start = guard._diagnostic_counts[1]
                expected = r._counters(c, facts.job, f.origin[0], _facts=facts)
                slow = guard._diagnostic_counts[1] - start
            assert fast < slow
            assert len(actual) == len(expected) == 2
            assert all(a is b for a, b in zip(actual, expected, strict=True))
        finally:
            event.remove(f.store.engine, "before_cursor_execute", sql)


def test_missing_raw_key_uses_original_query_without_packet(local_origin):
    f = local_origin
    queries = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, _ = prepared(f, c, guard, omit="model-operations")

        def sql(connection, cursor, statement, *args):
            queries.append(statement)

        event.listen(f.store.engine, "before_cursor_execute", sql)
        try:
            with observe_core() as calls:
                assert r._counters(c, facts.job, f.origin[0], _facts=facts) == []
            assert calls == [] and any("FROM operations" in text for text in queries)
        finally:
            event.remove(f.store.engine, "before_cursor_execute", sql)


def test_original_data_mutation_inside_core_fails_late_pin(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with scope(f, c) as guard:
                facts, _ = prepared(f, c, guard)
                with observe_core(
                    lambda: facts.job["context"]["messages"].append("synthetic drift")
                ) as calls:
                    r._counters(c, facts.job, f.origin[0], _facts=facts)
        assert calls == [1] and not guard.active


@pytest.mark.parametrize("marker", [False, True])
def test_two_attempts_match_original_and_retain_rows(local_origin, monkeypatch, marker, tmp_path):
    import json

    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, seed = prepared(f, c, guard, count=2, marker=marker)
        with observe_core() as calls:
            fast_rows = r._counters(c, facts.job, f.origin[0], _facts=facts)
        assert calls == [1]
        start = guard._diagnostic_counts[1]
        fast_rows = r._counters(c, facts.job, f.origin[0], _facts=facts)
        fast_pins = guard._diagnostic_counts[1] - start
        with monkeypatch.context() as patch:
            patch.setattr(r, "_cold_counter_loaded", lambda *a: r._RAW_READ_MISS)
            start = guard._diagnostic_counts[1]
            old_rows = r._counters(c, facts.job, f.origin[0], _facts=facts)
            old_pins = guard._diagnostic_counts[1] - start
        assert [x["parameters"]["natural_spec"]["ordinal"] for x in fast_rows] == [0, 1]
        assert fast_rows == old_rows
        assert all(a is b for a, b in zip(fast_rows, old_rows, strict=True))
        assert all(any(row is original for original in seed.attempt_rows) for row in fast_rows)
        assert fast_pins < old_pins
        (tmp_path / "pins.json").write_text(
            json.dumps(dict(rows=2, marker=marker, fast_pins=fast_pins, old_pins=old_pins))
        )


@pytest.mark.parametrize(
    "change",
    ["extra_slot", "duplicate_anchor", "wrong_anchor", "wrong_mode", "context", "repeated_ordinal"],
)
def test_bad_loaded_values_keep_original_rejection(local_origin, monkeypatch, change):
    f = local_origin

    def altered(context, rows, raw, reserved):
        aid = rows[0]["id"]
        if change == "extra_slot":
            raw["reservation:" + aid].append(dict(raw["reservation:" + aid][0]))
        elif change == "duplicate_anchor":
            raw["anchor:NS_RESERVED:" + aid].append(dict(raw["anchor:NS_RESERVED:" + aid][0]))
        elif change == "wrong_anchor":
            raw["anchor:NS_RESERVED:" + aid][0]["reserved_tokens"] += 1
        elif change == "wrong_mode":
            raw["mode"] = "MOCK"
        elif change == "context":
            context["repairs"] = 1
        else:
            rows[1]["parameters"]["natural_spec"]["ordinal"] = 0

    # Each rejection has its own graph, since failure invalidates the scope.
    results = []
    original_inputs = copy.deepcopy(f.inputs)
    for legacy in (False, True):
        f.inputs = copy.deepcopy(original_inputs)
        with f.store.tx() as c, pb._source_reads(f.store, c):
            with pytest.raises(DomainError) as caught:
                with scope(f, c) as guard:
                    facts, _ = prepared(f, c, guard, count=2, change=altered)
                    with monkeypatch.context() as patch:
                        if legacy:
                            patch.setattr(r, "_cold_counter_loaded", lambda *a: r._RAW_READ_MISS)
                        r._counters(c, facts.job, f.origin[0], _facts=facts)
            results.append(caught.value.public())
        assert not guard.active
    assert results[0] == results[1]


def test_unsuitable_snapshot_falls_back_before_core(local_origin):
    from sqlalchemy.sql.elements import quoted_name

    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, _ = prepared(f, c, guard, job_extra=dict(result=quoted_name("synthetic", None)))
        with observe_core() as calls:
            assert r._counters(c, facts.job, f.origin[0], _facts=facts) == []
        assert calls == []


@pytest.mark.parametrize("name", ["_Comparison", "standard_serializers", "json_defaults"])
def test_unknown_copy_or_json_dependencies_use_old_path(local_origin, monkeypatch, name):
    f = local_origin
    calls = []
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as guard:
        facts, _ = prepared(f, c, guard)
        with monkeypatch.context() as patch:
            if name == "_Comparison":
                patch.setattr(r._policy_segments, "_Comparison", lambda *a: calls.append(1))
            elif name == "standard_serializers":
                patch.setattr(
                    r._RAW_READ_COMPARISON, "standard_serializers", lambda *a: calls.append(1)
                )
            else:
                patch.setattr(r.json.encoder._make_iterencode, "__defaults__", ())
            with observe_core() as packet_calls:
                assert r._counters(c, facts.job, f.origin[0], _facts=facts) == []
            assert packet_calls == [] and calls == []


def test_original_core_exception_is_not_rechecked_or_replaced(local_origin):
    f = local_origin
    original = ValueError("synthetic original counter execution failure")

    def raised():
        raise original

    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(ValueError) as caught:
            with scope(f, c) as guard:
                facts, _ = prepared(f, c, guard)
                with observe_core(raised):
                    r._counters(c, facts.job, f.origin[0], _facts=facts)
        assert caught.value is original and not guard.active


def test_foreign_native_keys_are_refused_without_equality():
    calls = []

    class Trap:
        def __hash__(self):
            return hash("context")

        def __eq__(self, other):
            calls.append(1)
            return False

    value = {Trap(): "synthetic"}
    calls.clear()
    assert not r._counter_native_keys(value) and calls == []

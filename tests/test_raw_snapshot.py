"""Owned captures preserve independent observations; no provider or Worker."""

import math

import pytest

from sim2act import _raw_snapshot as native
from sim2act import natural_live_admission as gate
from sim2act.errors import DomainError


def original():
    from raw_snapshot_reference import _trial_pure_data

    return _trial_pure_data


def test_complete_builtin_capture_preserves_types_and_duplicates_dag():
    shared = [{"bool": True, "int": 1, "float": 1.0, "bytes": b"abc", "none": None}]
    raw = {"left": shared, "right": shared, "tuple": (shared, []), "nan": float("nan")}
    value = native.copy_snapshot(raw)
    assert type(value) is dict and value["left"] is not value["right"]
    assert value["left"] is not value["tuple"][0]
    assert type(value["tuple"]) is tuple and type(value["tuple"][1]) is list
    assert math.isnan(value.pop("nan"))
    old = original()(raw)
    old.pop("nan")
    assert gate._trial_typed_equal(value, old)
    shared[0]["int"] = 2
    assert value["left"][0]["int"] == 1
    assert native.copy_snapshot(raw)["left"][0]["int"] == 2


def test_unfamiliar_cycle_and_deep_values_select_original_before_capture():
    class Trap:
        def __reduce__(self):
            raise AssertionError("must not invoke reducers")

        def __iter__(self):
            raise AssertionError("must not invoke foreign iteration")

    for value in ({"foreign": Trap()}, {1: "invalid key"}):
        assert native.copy_snapshot(value) is native.UNSUPPORTED
        with pytest.raises(DomainError):
            gate._trial_pure_data(value)
    cyclic = []
    cyclic.append(cyclic)
    assert native.copy_snapshot(cyclic) is native.UNSUPPORTED
    with pytest.raises(DomainError, match="Cyclic"):
        gate._trial_pure_data(cyclic)
    deep = []
    for _ in range(100):
        deep = [deep]
    assert native.copy_snapshot(deep) is native.UNSUPPORTED
    assert original()(deep) == gate._trial_pure_data(deep)


def test_native_execution_failure_is_not_retried(monkeypatch):
    calls = []

    def failed(value):
        calls.append(1)
        raise MemoryError("synthetic allocation failure")

    monkeypatch.setattr(gate, "_RAW_COPY", failed)
    with pytest.raises(MemoryError):
        gate._trial_pure_data({"value": 1})
    assert calls == [1]


def test_left_capture_precedes_right_and_neither_borrows():
    left, right = {"value": 1}, {"value": 1}
    actual = gate._trial_pure_data(left)
    left["value"] = right["value"] = 2
    saved = gate._trial_pure_data(right)
    left["value"] = right["value"] = 1
    assert not gate._trial_typed_equal(actual, saved)
    assert gate._trial_typed_equal(left, right)


def test_unknown_mapping_helper_uses_original_once(monkeypatch):
    calls = []

    def changed(value):
        calls.append(value)
        raise ValueError("synthetic unknown mapping helper")

    monkeypatch.setattr(gate, "_trial_pure_mapping", changed)
    with pytest.raises(ValueError, match="unknown mapping"):
        gate._trial_pure_data({"value": 1})
    assert len(calls) == 1


def test_native_equality_keeps_exact_types_and_nan_semantics():
    nan = float("nan")
    assert native.equal_values(nan, nan) is False
    for left, right, expected in (
        (True, 1, False),
        (1, 1.0, False),
        ([1], (1,), False),
        (-0.0, 0.0, True),
        ({"v": [1, None]}, {"v": [1, None]}, True),
    ):
        assert native.equal_values(left, right) is expected

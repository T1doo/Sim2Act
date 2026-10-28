"""Raw mapping boundary: fresh keys, exact values and original hook fallback."""

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name

from sim2act import natural_live_admission as gate
from sim2act.errors import DomainError


def test_exact_dictionary_is_not_copied_or_value_inspected_and_keys_are_fresh():
    class Foreign:
        def __eq__(self, other):
            pytest.fail("Projection must not compare values")

    value = {"visible": Foreign(), "shared": []}
    assert gate._trial_pure_mapping(value) is value
    value[1] = "invalid current key"
    with pytest.raises(DomainError, match="trusted trial raw keys"):
        gate._trial_pure_mapping(value)


def test_quoted_dictionary_and_row_retain_visible_projection():
    leaf = []
    raw = {quoted_name("visible", True): leaf}
    projected = gate._trial_pure_mapping(raw)
    assert projected is not raw and type(next(iter(projected))) is str
    assert projected["visible"] is leaf
    row = RowMapping(SimpleResultMetaData(["visible"]), None,
        {quoted_name("visible", False): 0}, (leaf, object()))
    projected = gate._trial_pure_mapping(row)
    assert list(projected) == ["visible"] and projected["visible"] is leaf


def test_foreign_key_is_rejected_without_dispatch():
    class Key:
        armed = False

        def __hash__(self):
            if self.armed:
                pytest.fail("Projection must not hash a foreign key")
            return 1

        def __eq__(self, other):
            pytest.fail("Projection must not compare a foreign key")

    key = Key()
    value = {"ordinary": 1, key: 2}
    key.armed = True
    with pytest.raises(DomainError, match="trusted trial raw keys"):
        gate._trial_pure_mapping(value)


def test_changed_require_keeps_original_hook_order(monkeypatch):
    original, calls = gate.require, []
    value = {"visible": []}

    def observe(condition, message):
        calls.append(message)
        original(condition, message)

    monkeypatch.setattr(gate, "require", observe)
    assert gate._trial_pure_mapping(value) is value
    assert calls == ["Exact complete trial raw mapping required",
        "Exact trusted trial raw keys required"]

"""Packaged native row projection retains original bytes, errors and hooks."""

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name

from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act.errors import DomainError


def make(position=2):
    return RowMapping(
        SimpleResultMetaData(["first", "second"]),
        None,
        {"first": 0, "second": 1, "hidden": position},
        ({"x": [1, True]}, "visible", "unused"),
    )


def test_packaged_projection_matches_old_complete_pin(monkeypatch):
    value = make()
    native = gate._RAW_ROW_LOOKUP
    assert native is not None
    fast = runtime._cold_graph_bytes({"row": value, "raw": object.__getattribute__(value, "_data")})
    monkeypatch.setattr(gate, "_RAW_ROW_LOOKUP", None)
    slow = runtime._cold_graph_bytes({"row": value, "raw": object.__getattribute__(value, "_data")})
    assert fast == slow


@pytest.mark.parametrize("position", [True, -1, 3, 1 << 200])
def test_rejection_matches_legacy_including_huge_integer(monkeypatch, position):
    native = gate._RAW_ROW_LOOKUP
    errors = []
    for backend in (native, None):
        monkeypatch.setattr(gate, "_RAW_ROW_LOOKUP", backend)
        with pytest.raises(DomainError) as caught:
            runtime._cold_graph_row_storage(make(position))
        errors.append(caught.value.public())
    assert errors[0] == errors[1]


def test_quoted_conversion_index_mutation_has_same_iterator_error(monkeypatch):
    native = gate._RAW_ROW_LOOKUP
    observations = []
    for backend in (native, None):
        monkeypatch.setattr(gate, "_RAW_ROW_LOOKUP", backend)
        key = quoted_name("visible", True)
        index = {key: 0}
        value = RowMapping(SimpleResultMetaData(["visible"]), None, index, ("data",))
        calls = []

        def convert(self, calls=calls, index=index):
            calls.append(1)
            index["new"] = 0
            return "visible"

        with monkeypatch.context() as patch:
            patch.setattr(quoted_name, "__str__", convert)
            with pytest.raises(RuntimeError) as caught:
                runtime._cold_graph_row_storage(value)
        observations.append((str(caught.value), len(calls)))
    assert observations[0] == observations[1]


def test_quoted_finalizer_cannot_hide_missing_key(monkeypatch):
    metadata = SimpleResultMetaData(["visible", "missing"])
    keys = metadata._keys
    index = {"visible": 0, quoted_name("extra", True): 1}
    row = RowMapping(metadata, None, index, ("a", "b"))
    events = []

    def stringify(self):
        name = str.__str__(self)
        if name == "extra":
            index.clear()
            index.update({"visible": 0, "extra": 1})
        return name

    def finalize(self):
        events.append("finalized")
        if "missing" in keys:
            keys.remove("missing")

    monkeypatch.setattr(quoted_name, "__str__", stringify)
    monkeypatch.setattr(quoted_name, "__del__", finalize, raising=False)
    assert (
        gate._RAW_ROW_LOOKUP(keys, ("a", "b"), index, quoted_name, runtime.require)
        is gate._RAW_UNSUPPORTED
    )
    assert events == []
    with pytest.raises(DomainError, match="Complete Cold graph SQL row keys required"):
        runtime._cold_graph_row_storage(row)

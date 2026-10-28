"""Owned plans retain exact data; no Worker, network or permission is installed."""

import gc
import struct
import weakref

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name

from sim2act._immutable_settlement import OwnedValue, UnsupportedPlan
from sim2act.contracts import Limits


def test_complete_large_shared_graph_owns_all_mutable_data():
    shared = [{"payload": "synthetic source " * 200, "bits": -0.0} for _ in range(200)]
    source = {
        "left": shared,
        "right": shared,
        "binary": b"raw" * 5000,
        "typed": (True, 1, 1.0, None),
    }
    owned = OwnedValue.capture(source)
    private = owned.materialize()
    assert private == source and private is not source
    assert private["left"] is private["right"] and private["left"] is not shared
    shared[0]["payload"] = "changed"
    assert not owned.matches(source) and private["left"][0]["payload"] != "changed"
    private["left"].append("private edit")
    assert len(owned.materialize()["left"]) == 200
    assert type(owned._data) is bytes


def test_alias_split_merge_key_order_and_float_bits_are_distinct():
    a, b = [bytes(bytearray(b"equal contents " * 5)) for _ in range(2)]
    assert a is not b
    owned = OwnedValue.capture([a, b])
    assert not owned.matches([b, b]) and not owned.matches([a, a])
    assert owned.matches([b, a])
    assert not OwnedValue.capture(dict(a=1, b=2)).matches(dict(b=2, a=1))
    assert not OwnedValue.capture([0.0]).matches([-0.0])
    nan1 = struct.unpack("!d", bytes.fromhex("7ff8000000000001"))[0]
    nan2 = struct.unpack("!d", bytes.fromhex("7ff8000000000002"))[0]
    assert not OwnedValue.capture([nan1]).matches([nan2])


def test_limits_and_actual_sql_row_are_private_and_complete():
    limit = Limits(
        max_requests=2,
        max_tools=4,
        max_repairs=0,
        max_total_tokens=64000,
        max_output_tokens=1024,
        run_seconds=300,
    )
    keys = [quoted_name("id", True), "body"]
    parent = SimpleResultMetaData(keys)
    row = RowMapping(parent, None, {keys[0]: 0, "body": 1}, ("synthetic", {"items": [1]}))
    owned = OwnedValue.capture({"row": row, "limits": limit, "same": limit})
    result = owned.materialize()
    assert type(result["row"]) is RowMapping and dict(result["row"]) == dict(row)
    assert result["row"] is not row and result["row"]["body"] is not row["body"]
    assert result["limits"] is result["same"] and result["limits"] is not limit
    assert result["limits"].model_dump() == limit.model_dump()
    row["body"]["items"].append(2)
    assert not owned.matches({"row": row, "limits": limit, "same": limit})


def test_unknown_callbacks_cycles_and_hidden_row_storage_not_silently_normalized():
    class Foreign(dict):
        def items(self):
            pytest.fail("Foreign callback invoked")

    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture(Foreign())
    cyclic = []
    cyclic.append(cyclic)
    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture(cyclic)
    parent = SimpleResultMetaData(["visible"])
    hidden = RowMapping(parent, None, {"visible": 0}, ("visible", "hidden"))
    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture(hidden)


def test_owned_packet_retains_no_mutable_source():
    class ReferenceableList(list):
        pass

    source = ReferenceableList([1])
    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture(source)
    ref = weakref.ref(source)
    del source
    gc.collect()
    assert ref() is None


def test_foreign_row_lookup_is_rejected_without_losing_lookup_semantics():
    from sqlalchemy import column

    key = column("x")
    row = RowMapping(SimpleResultMetaData(["x"]), None, {"x": 0, key: 0}, (7,))
    assert row[key] == 7
    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture(row)


def test_limits_storage_and_fields_set_external_aliases_survive():
    limits = Limits(
        max_requests=2,
        max_tools=4,
        max_repairs=0,
        max_total_tokens=64000,
        max_output_tokens=1024,
        run_seconds=300,
    )
    original = {
        "limits": limits,
        "storage": limits.__dict__,
        "fields": limits.__pydantic_fields_set__,
    }
    owned = OwnedValue.capture(original)
    private = owned.materialize()
    assert private["storage"] is private["limits"].__dict__
    assert private["fields"] is private["limits"].__pydantic_fields_set__
    assert owned.matches(private)
    private["storage"]["max_requests"] += 1
    assert not owned.matches(private)


def test_unknown_metaclass_equality_is_never_called():
    class Meta(type):
        def __eq__(self, other):
            pytest.fail("Foreign metaclass callback invoked")

    class Foreign(metaclass=Meta):
        pass

    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture(Foreign())
    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture({Foreign(): 1})


def test_row_index_storage_alias_is_owned_not_rebuilt():
    index = {"x": 0}
    row = RowMapping(SimpleResultMetaData(["x"]), None, index, (7,))
    private = OwnedValue.capture({"row": row, "index": index}).materialize()
    assert private["row"]._key_to_index is private["index"]


def test_unknown_quoted_name_conversion_rejected_before_callback(monkeypatch):
    def foreign(self):
        pytest.fail("Unknown quote conversion invoked")

    monkeypatch.setattr(quoted_name, "__str__", foreign)
    with pytest.raises(UnsupportedPlan):
        OwnedValue.capture(quoted_name("x", True))

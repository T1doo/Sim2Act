"""Fresh complete metadata encoding; mismatches keep original key/cycle gate."""

import pytest

from sim2act import _cold_policy_segment as schema
from sim2act.errors import DomainError


def test_live_nested_metadata_change_and_restore_is_observed():
    kind, live, *_ = schema._SCHEMAS[0]
    assert schema._fixed_schema(kind)
    prior = live.get("metadata")
    existed = "metadata" in live
    try:
        live["metadata"] = {"new complete field": [1, True]}
        assert not schema._fixed_schema(kind)
    finally:
        if existed:
            live["metadata"] = prior
        else:
            live.pop("metadata")
    assert schema._fixed_schema(kind)


def test_unknown_leaf_has_no_reduce_or_equality_hook():
    class Trap:
        def __reduce__(self):
            raise AssertionError("reducer")

        def __eq__(self, other):
            raise AssertionError("equality")

    value = Trap()
    assert schema._schema_bytes({"leaf": value}) == schema._schema_bytes({"leaf": value})
    assert schema._schema_bytes({"leaf": value}) != schema._schema_bytes({"leaf": Trap()})


def test_pin_miss_still_visits_illegal_key_and_cycle():
    entry = schema._SCHEMAS[0]
    live = entry[1]
    prior = live.get("metadata")
    existed = "metadata" in live
    try:
        cycle = []
        cycle.append(cycle)
        for value in ({object(): 1}, cycle):
            live["metadata"] = value
            with pytest.raises(DomainError):
                schema._schema_current(entry)
    finally:
        if existed:
            live["metadata"] = prior
        else:
            live.pop("metadata")
    assert schema._fixed_schema(entry[0])

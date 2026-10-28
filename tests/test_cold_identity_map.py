"""Original pointer shortcut preserves full alias partition and mutable checks."""

import pytest
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import quoted_name

from sim2act import _cold_graph_structure as native
from sim2act import natural_spec_runtime as r
from sim2act.contracts import Limits


def equal_pair(kind):
    if kind == "bytes":
        return [bytes(bytearray(b"synthetic alias content" * 5)) for _ in range(2)]
    if kind == "str":
        return [bytes(bytearray(b"synthetic alias content" * 5)).decode() for _ in range(2)]
    if kind == "list":
        return [[1], [1]]
    return [dict(a=1), dict(a=1)]


@pytest.mark.parametrize("kind", ["bytes", "str", "list", "dict"])
def test_merge_after_reassigning_other_original_still_conflicts(kind):
    a, b = equal_pair(kind)
    assert a == b and a is not b
    original = [a, b]
    identity = (object(), object(), "synthetic", 0, "post")
    saved = native.snapshot(
        original,
        RowMapping,
        Limits,
        quoted_name,
        r._cold_graph_row_storage,
        r._cold_graph_limit_values,
        identity,
    )
    assert saved is not native.UNSUPPORTED
    for current in ([b, b], [a, a]):
        assert native.matches_fast(saved, current, identity) is False
        assert r._cold_graph_bytes(original) != r._cold_graph_bytes(current)
    assert native.matches_fast(saved, [b, a], identity) is True
    assert native.matches_fast(saved, original, identity) is True
    if kind in {"list", "dict"}:
        if kind == "list":
            a.append(2)
        else:
            a["new"] = 2
        # SAME original pointer must still traverse fresh changed contents.
        assert native.matches_fast(saved, original, identity) is False

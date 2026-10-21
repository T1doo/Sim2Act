"""Private immutable values for the uninstalled accounted-family component.

No callers in the current runtime. Explicit bounds are caller obligations, not
product defaults or authorization. There is deliberately no thaw/materializer.
"""

import base64
import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, NamedTuple

from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import quoted_name

from sim2act.errors import DomainError
from sim2act.natural_spec_runtime import _cold_graph_row_storage


class _Rejected(DomainError):
    def __init__(self, message):
        super().__init__("VERSION_CONFLICT", "Owned accounted fact: " + message)


class _Bounds(NamedTuple):
    nodes: int
    edges: int
    depth: int
    leaf_bytes: int
    encoded_bytes: int


class _Packet(NamedTuple):
    root: int
    nodes: tuple
    encoded: bytes
    digest: str
    edges: int


def _freeze(value, bounds):
    """One invocation, no cross-call cache; no source reference in the result."""
    if type(bounds) is not _Bounds or not all(type(v) is int and v > 0 for v in bounds):
        raise _Rejected("explicit positive proof bounds required")
    nodes: list[Any] = []
    done: dict[int, tuple[Any, int]] = {}
    active: set[int] = set()
    heights: dict[int, int] = {}
    edge_count = leaf_bytes = 0

    def visit(item, depth):
        nonlocal edge_count, leaf_bytes
        if depth > bounds.depth:
            raise _Rejected("depth")
        kind = type(item)
        if not (
            kind is dict
            or kind is list
            or kind is tuple
            or kind is bytes
            or kind is str
            or kind is int
            or kind is bool
            or kind is float
            or item is None
            or kind is RowMapping
            or kind is quoted_name
        ):
            raise _Rejected("unknown type")
        identity = id(item)
        if identity in active:
            raise _Rejected("cycle")
        if identity in done:
            original, index = done[identity]
            assert original is item
            if depth + heights[index] > bounds.depth:
                raise _Rejected("depth")
            return index
        if len(nodes) >= bounds.nodes:
            raise _Rejected("nodes")
        index = len(nodes)
        nodes.append(None)
        active.add(identity)
        node: tuple[str, Any]

        child_refs = []

        def child(value):
            nonlocal edge_count
            edge_count += 1
            if edge_count > bounds.edges:
                raise _Rejected("edges")
            ref = visit(value, depth + 1)
            child_refs.append(ref)
            return ref

        if kind is dict:
            keys = tuple(dict.keys(item))
            if not all(type(k) is str or type(k) is quoted_name for k in keys):
                raise _Rejected("mapping keys")
            if len({str(k) for k in keys}) != len(keys):
                raise _Rejected("duplicate mapping keys")
            node = ("dict", tuple((child(k), child(item[k])) for k in keys))
        elif kind is list or kind is tuple:
            node = ("list" if kind is list else "tuple", tuple(child(v) for v in item))
        elif kind is RowMapping:
            # Full keys/data/safe-index payload, including hidden positions.
            storage = _cold_graph_row_storage(item)
            names = tuple(str(key) for key in storage[0])
            if len(set(names)) != len(names):
                raise _Rejected("duplicate row keys")
            node = ("row", child(storage))
        elif kind is bytes:
            leaf_bytes += len(item)
            node = ("bytes", item)
        elif kind is str or kind is quoted_name:
            text = item if kind is str else str(item)
            # strict_json and the legacy C Pickler accept escaped lone Unicode
            # surrogates. Count them without narrowing the native str domain;
            # wire encoding below is ASCII JSON with escapes, never raw UTF-8.
            leaf_bytes += len(text.encode("utf-8", errors="surrogatepass"))
            node = ("str" if kind is str else "quoted", text)
        elif kind is float:
            if not math.isfinite(item):
                raise _Rejected("nonfinite")
            leaf_bytes += 8
            node = ("float", item.hex())
        elif kind is int:
            leaf_bytes += max(1, (item.bit_length() + 7) // 8)
            node = ("int", item)
        elif kind is bool:
            leaf_bytes += 1
            node = ("bool", item)
        else:
            node = ("none", None)
        if leaf_bytes > bounds.leaf_bytes:
            raise _Rejected("leaf bytes")
        nodes[index] = node
        heights[index] = max((heights[ref] + 1 for ref in child_refs), default=0)
        active.remove(identity)
        # Reuse only completed immutable subvalues; retain source until done.
        done[identity] = item, index
        return index

    root = visit(value, 0)
    frozen = tuple(nodes)
    flat = tuple(
        (tag, base64.b64encode(body).decode("ascii")) if tag == "bytes" else (tag, body)
        for tag, body in frozen
    )
    chunks = [b"SIM2ACT_ACCOUNTED_COMPONENT_VALUES_V1\x00"]
    total = len(chunks[0])
    for chunk in json.JSONEncoder(
        ensure_ascii=True, allow_nan=False, separators=(",", ":")
    ).iterencode((root, flat)):
        encoded = chunk.encode("ascii")
        total += len(encoded)
        if total > bounds.encoded_bytes:
            raise _Rejected("encoded bytes")
        chunks.append(encoded)
    encoded = b"".join(chunks)
    return _Packet(root, frozen, encoded, hashlib.sha256(encoded).hexdigest(), edge_count)


@dataclass(frozen=True, slots=True, eq=False)
class _Node:
    packet: _Packet
    ref: int

    def __post_init__(self):
        if not (
            type(self.packet) is _Packet
            and type(self.packet.nodes) is tuple
            and type(self.ref) is int
            and 0 <= self.ref < len(self.packet.nodes)
        ):
            raise _Rejected("admitted packet and exact node reference required")

    def __eq__(self, other):
        raise TypeError("Use explicit domain comparison, not node equality")

    def __ne__(self, other):
        raise TypeError("Use explicit domain comparison, not node inequality")

    @property
    def tag(self):
        return self.packet.nodes[self.ref][0]

    def scalar(self):
        tag, value = self.packet.nodes[self.ref]
        if tag in ("dict", "list", "tuple", "row"):
            raise _Rejected("scalar required")
        return float.fromhex(value) if tag == "float" else value

    def items(self):
        if self.tag != "dict":
            raise _Rejected("mapping required")
        return tuple(
            (_Node(self.packet, k).scalar(), _Node(self.packet, v))
            for k, v in self.packet.nodes[self.ref][1]
        )

    def get(self, name):
        if type(name) is not str:
            raise _Rejected("exact field name required")
        for key, value in self.items():
            if key == name:
                return value
        raise _Rejected("missing complete field: " + name)

    def sequence(self):
        if self.tag not in ("list", "tuple"):
            raise _Rejected("sequence required")
        return tuple(_Node(self.packet, ref) for ref in self.packet.nodes[self.ref][1])


def _node(packet):
    return _Node(packet, packet.root)


def _equal(left, right):
    """Type-exact domain values, independent of node ids/sharing/dict order.

    All inputs are immutable admitted nodes. A per-comparison pair memo prevents
    unfolding common DAG paths; it is never reused across validations.
    """
    if type(left) is not _Node or type(right) is not _Node:
        raise _Rejected("owned nodes required")
    pending, done = [(left, right)], set()
    while pending:
        a, b = pending.pop()
        key = (id(a.packet), a.ref, id(b.packet), b.ref)
        if key in done:
            continue
        done.add(key)
        if a.tag != b.tag:
            return False
        if a.tag == "dict":
            aa, bb = dict(a.items()), dict(b.items())
            if aa.keys() != bb.keys():
                return False
            pending.extend((v, bb[k]) for k, v in aa.items())
        elif a.tag in ("list", "tuple"):
            aa, bb = a.sequence(), b.sequence()
            if len(aa) != len(bb):
                return False
            pending.extend(zip(aa, bb, strict=True))
        elif a.tag == "row":
            # Raw sidecar equality is not used for business row membership.
            pending.append(
                (
                    _Node(a.packet, a.packet.nodes[a.ref][1]),
                    _Node(b.packet, b.packet.nodes[b.ref][1]),
                )
            )
        elif a.scalar() != b.scalar():
            return False
    return True

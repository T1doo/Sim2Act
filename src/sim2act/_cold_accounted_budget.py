"""Explicit, uninstalled allocation accounting for the SQLite cohort experiment.

Units are conservative logical allocation costs, not RSS/GC or a Python heap
quota. Original SQL decoding/full guards/oracles are deliberately outside this
ledger. No implicit limits, process globals, authority, or cross-call cache.
"""

import math
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, NamedTuple

from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import quoted_name

from ._cold_accounted_values import _Bounds, _freeze, _Node, _Rejected
from .errors import DomainError


class _Capacity(DomainError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__("BUDGET_EXHAUSTED", "Uninstalled owned capacity: " + reason)


class _Unsupported(_Capacity):
    pass


class _Limits(NamedTuple):
    resident: int
    peak: int
    work: int
    integer_bits: int


@dataclass(eq=False)
class _Reservation:
    ledger: Any
    kind: str
    units: int = 0
    active: bool = True

    def grow(self, units):
        b = self.ledger
        if not self.active or not b.active or type(units) is not int or units < 0:
            raise _Rejected("inactive allocation reservation")
        if b.live + units > b.limits.peak:
            b.fail("peak")
        if self.kind == "resident" and b.resident + units > b.limits.resident:
            b.fail("resident")
        b.live += units
        if self.kind == "resident":
            b.resident += units
        self.units += units
        b.peak = max(b.peak, b.live)

    def close(self):
        if self.active:
            self.active = False
            self.ledger.live -= self.units
            if self.kind == "resident":
                self.ledger.resident -= self.units
            assert self.ledger.live >= 0 and self.ledger.resident >= 0
            self.ledger._tickets.remove(self)


class _Ledger:
    def __init__(self, bounds, limits):
        if (type(bounds) is not _Bounds or type(limits) is not _Limits
                or not all(type(v) is int and v > 0 for v in (*bounds, *limits))):
            raise ValueError("explicit positive experiment bounds required")
        self.bounds, self.limits = bounds, limits
        self.active = True
        self.live = self.resident = self.peak = self.work = 0
        self._tickets: set[_Reservation] = set()
        self._views = None
        self.on_failure = None

    def fail(self, reason):
        if self.on_failure is not None:
            self.on_failure()
        raise _Capacity(reason)

    def view(self, units):
        # Views may escape their helper's call stack. Conservatively retain ALL
        # their logical allocation charges until scope close, never falsely
        # release a still-held tuple/Node as temporary scratch.
        self.spend()
        if self._views is None:
            self._views = self.reserve('resident')
        self._views.grow(units)

    def spend(self, units=1):
        if not self.active:
            raise _Rejected("closed allocation ledger")
        if type(units) is not int or units < 0:
            raise _Rejected("exact nonnegative allocation work required")
        if self.work + units > self.limits.work:
            self.fail("work")
        self.work += units

    def reserve(self, kind="temporary", units=0):
        if type(kind) is not str or kind not in ("temporary", "resident"):
            raise ValueError("reservation kind")
        self.spend()
        result = _Reservation(self, kind)
        result.grow(units)
        self._tickets.add(result)
        return result

    def close(self):
        self.on_failure = None
        for ticket in tuple(self._tickets):
            ticket.close()
        self.active = False

    @contextmanager
    def projection(self):
        ticket = self.reserve()
        try:
            yield _Projection(self, ticket)
        finally:
            ticket.close()

    def encode(self, prepared, projection, *, resident=False):
        """Reserve full overlapping encoder temporaries BEFORE _freeze allocates.

        Prepared is a private native-only copy. Its original mutable input is
        never revisited by the encoder. No RowMapping/reducer/model_dump here.
        Conservative upper bounds may reject an otherwise encodable old value.
        """
        upper = projection.encoded_upper()
        if upper > self.bounds.encoded_bytes:
            raise _Capacity("encoded")
        # Nodes/ref tuples/memo, UTF8 leaf count, base64 flat, JSON chunk strings
        # plus bytes, join overlap. Deliberate logical overaccounting, not RSS.
        retained = projection.units + upper + 256 * (projection.nodes + projection.edges + 1)
        temporary = self.reserve(units=retained + 8 * upper)
        output = None
        try:
            from ._cold_accounted_measure import Limits, measure_prepared

            self.spend(8 * upper + 4 * projection.hash_work + 65536)
            measured = measure_prepared(prepared, Limits(*self.bounds, self.limits.integer_bits))
            if not measured.complete:
                if measured.reason in ("cycle", "nonfinite", "concurrent_mutation"):
                    raise _Rejected("private prepared graph changed")
                raise _Capacity("prepared_" + str(measured.reason))
            output = self.reserve("resident" if resident else "temporary", retained)
            packet = _freeze(prepared, self.bounds)
            return packet, output
        except BaseException:
            if output is not None:
                output.close()
            raise
        finally:
            temporary.close()

    @contextmanager
    def snapshot(self, value, *, visible=False, typed=False):
        lease = None
        try:
            with self.projection() as p:
                prepared = (p.row(value, None) if visible and type(value) is RowMapping
                            else p.copy(value, typed=typed))
                packet, lease = self.encode(prepared, p)
            yield packet
        finally:
            if lease is not None:
                lease.close()

    @contextmanager
    def source_json(self, size):
        # Existing wire/body gates bound these bytes. Covers the additional
        # owned leaf's strict_json trees, canonical/UTF8/ASCII strings, SHA and
        # usage envelope, including overlapping live parse results.
        self.spend(64 * size + 65536)
        ticket = self.reserve(units=1024 * size + 65536)
        try:
            yield
        finally:
            ticket.close()

    def equal(self, left, right):
        """The old domain comparison, with per-pair and pending-table budget."""
        if type(left) is not _Node or type(right) is not _Node:
            raise _Rejected("exact owned nodes required")
        ticket = self.reserve(units=256)
        try:
            pending, done = [(left, right)], set()
            while pending:
                self.spend()
                a, b = pending.pop()
                key = (id(a.packet), a.ref, id(b.packet), b.ref)
                if key in done:
                    continue
                ticket.grow(256)
                done.add(key)
                if a.tag != b.tag:
                    return False
                if a.tag == "dict":
                    size = len(a.packet.nodes[a.ref][1]) + len(b.packet.nodes[b.ref][1])
                    self.spend(8 * size)
                    key_units = 0
                    for node in (a, b):
                        for key_ref, _ in node.packet.nodes[node.ref][1]:
                            key_units += 8 * len(node.packet.nodes[key_ref][1])
                    # First hash, key equality and lookups, conservatively even
                    # for collisions. No items table/hash before this prepayment.
                    self.spend(key_units * (size + 1))
                    ticket.grow(512 * size)
                    aa, bb = dict(a.items()), dict(b.items())
                    if aa.keys() != bb.keys():
                        return False
                    pending.extend((v, bb[k]) for k, v in aa.items())
                elif a.tag in ("list", "tuple"):
                    size = len(a.packet.nodes[a.ref][1]) + len(b.packet.nodes[b.ref][1])
                    self.spend(4 * size)
                    ticket.grow(256 * size)
                    aa, bb = a.sequence(), b.sequence()
                    if len(aa) != len(bb):
                        return False
                    pending.extend(zip(aa, bb, strict=True))
                elif a.tag == "row":
                    ticket.grow(256)
                    pending.append((_Node(a.packet, a.packet.nodes[a.ref][1]),
                                    _Node(b.packet, b.packet.nodes[b.ref][1])))
                else:
                    # Values are immutable admitted leaves, never user callbacks.
                    aa, bb = a.packet.nodes[a.ref][1], b.packet.nodes[b.ref][1]
                    kind = type(aa)
                    if kind is str or kind is bytes:
                        self.spend(4 * (len(aa) + len(bb)))
                    elif kind is int:
                        self.spend(1 + (aa.bit_length() + bb.bit_length()) // 8)
                    if a.scalar() != b.scalar():
                        return False
            return True
        finally:
            ticket.close()


class _Projection:
    def __init__(self, ledger, ticket):
        self.b, self.ticket = ledger, ticket
        self.nodes = self.edges = self.leaf = self.ascii = self.units = 0
        self.hash_work = 0
        self.active: set[int] = set()
        self.done: dict[tuple[int, bool], tuple[Any, Any, int]] = {}
        self.sidecars: list = []
        from . import natural_live_admission as gate
        self.alloc(8192)  # trusted fixed registry construction before the tuple copies
        self.allowed = gate._trial_typed_nested_classes()

    def alloc(self, units):
        self.b.spend()
        self.ticket.grow(units)
        self.units += units

    def edge(self, n=1):
        if self.edges + n > self.b.bounds.edges:
            raise _Capacity("edges")
        self.edges += n
        self.alloc(64 * n)

    def leaf_size(self, n):
        if self.leaf + n > self.b.bounds.leaf_bytes:
            raise _Capacity("leaf")
        self.leaf += n

    def hash_keys(self, raw, width):
        # Prepay iteration before reading even the first native key; len(str)
        # does not hash/compare/scan its contents. Foreign keys get no callback.
        self.b.spend(len(raw))
        lengths = 0
        for key in raw:
            if type(key) is not str and type(key) is not quoted_name:
                raise _Rejected("bounded mapping key")
            lengths += len(key)
        amount = 8 * lengths * (width + 1)
        self.b.spend(amount)
        self.hash_work += amount

    def text(self, value):
        # reserve normalization and possible UTF8 counting scratch before str().
        self.b.spend(2 * len(value))
        self.alloc(128 + 8 * len(value))
        self.leaf_size(sum(1 if ord(c) < 128 else 2 if ord(c) < 2048
                           else 3 if ord(c) < 65536 else 4 for c in value))
        self.ascii += sum(2 if c in ('"', "\\", "\b", "\t", "\n", "\f", "\r") else
                          6 if ord(c) < 32 or 127 <= ord(c) < 65536 else
                          12 if ord(c) >= 65536 else 1 for c in value)
        return value if type(value) is str else str(value)

    def copy(self, value, depth=0, *, typed=False):
        """Single-pass bounded copy; aliases reuse only completed owned values."""
        from .contracts import BranchCondition, WorkflowStep

        self.b.spend()
        depth_limit = min(self.b.bounds.depth - 16, (sys.getrecursionlimit() - 200) // 5)
        if depth > depth_limit:
            raise _Capacity("depth")
        kind, ident = type(value), id(value)
        memo_key = ident, typed
        if ident in self.active:
            raise _Rejected("cyclic bounded input")
        if memo_key in self.done:
            original, copied, height = self.done[memo_key]
            assert original is value
            if depth + height > depth_limit:
                raise _Capacity("depth")
            return copied
        model = typed and any(kind is t for t in self.allowed)
        if not (any(kind is t for t in (dict, list, tuple, str, quoted_name, bytes, int, bool, float, type(None))) or model):
            raise _Unsupported("representation")
        if self.nodes >= self.b.bounds.nodes:
            raise _Capacity("nodes")
        self.nodes += 1
        self.alloc(384)  # node + strong memo + active/height bookkeeping
        self.active.add(ident)
        height = 0

        def child(item):
            nonlocal height
            self.edge()
            result = self.copy(item, depth + 1, typed=typed)
            height = max(height, self.done[id(item), typed][2] + 1)
            return result

        result: Any
        if kind is dict or model:
            if model:
                raw = object.__getattribute__(value, "__dict__")
                fields = type.__getattribute__(kind, "__pydantic_fields__")
                selected = object.__getattribute__(value, "__pydantic_fields_set__")
                if type(raw) is not dict or type(fields) is not dict or type(selected) is not set:
                    raise _Rejected("fixed model storage")
                self.b.spend(len(raw) + len(fields) + len(selected))
                if (not all(type(k) is str for k in raw)
                        or not all(type(k) is str for k in fields)
                        or not all(type(k) is str for k in selected)
                        or raw.keys() != fields.keys() or not selected <= fields.keys()
                        or object.__getattribute__(value, "__pydantic_extra__") is not None
                        or object.__getattribute__(value, "__pydantic_private__") is not None):
                    raise _Rejected("fixed model fields/extra/private")
            else:
                raw = value
            if self.edges + len(raw) * 2 > self.b.bounds.edges:
                raise _Capacity("edges")
            self.hash_keys(raw, len(raw))
            result = {}
            for k, v in dict.items(raw):
                if type(k) is not str and type(k) is not quoted_name:
                    raise _Rejected("bounded mapping key")
                if v is None and ((kind is BranchCondition and k == "value") or (kind is WorkflowStep and k == "when")):
                    continue
                key, item = child(k), child(v)
                result[key] = item
        elif kind is list or kind is tuple:
            if self.edges + len(value) > self.b.bounds.edges:
                raise _Capacity("edges")
            self.alloc(64 * len(value))  # list/tuple overlap before construction
            items = [child(item) for item in value]
            result = items if kind is list else tuple(items)
        elif kind is str or kind is quoted_name:
            self.text(value)
            result = value  # immutable text; preserve the quoted_name type tag
        elif kind is bytes:
            self.b.spend(len(value))
            self.leaf_size(len(value))
            self.alloc(128 + len(value))
            self.ascii += 4 * ((len(value) + 2) // 3)
            result = value
        elif kind is int:
            bits = value.bit_length()
            if bits > self.b.limits.integer_bits:
                raise _Capacity("integer_bits")
            self.leaf_size(max(1, (bits + 7) // 8))
            self.ascii += 2 + bits * 30103 // 100000
            result = value
        elif kind is float:
            if not math.isfinite(value):
                raise _Rejected("nonfinite bounded input")
            self.leaf_size(8)
            result = value
        else:
            self.leaf_size(1)
            result = value
        self.active.remove(ident)
        self.done[memo_key] = value, result, height
        return result

    def row(self, value, label, schema=None):
        """No _cold_graph_row_storage/model_dump/foreign-key lookup before budget."""
        from .natural_spec_runtime import _ColdGraphCursorMeta, _ColdGraphSimpleMeta

        if type(value) is dict:
            result = self.copy(value)
        elif type(value) is RowMapping:
            parent = object.__getattribute__(value, "_parent")
            data = object.__getattribute__(value, "_data")
            index = object.__getattribute__(value, "_key_to_index")
            if (not (type(parent) is _ColdGraphCursorMeta or type(parent) is _ColdGraphSimpleMeta)
                    or type(data) is not tuple or type(index) is not dict):
                raise _Rejected("exact bounded row storage")
            keys = object.__getattribute__(parent, "_keys")
            if type(keys) is not list:
                raise _Rejected("exact bounded row keys")
            self.b.spend(len(index) + len(keys))  # ignored foreign entries count too
            lengths = 0
            for key in dict.keys(index):
                if type(key) is str or type(key) is quoted_name:
                    lengths += len(key)
            amount = 8 * lengths * (len(index) + len(keys) + 1)
            self.b.spend(amount)
            self.hash_work += amount
            self.alloc(256)
            lookup = {}
            for key, position in dict.items(index):
                if type(key) is str or type(key) is quoted_name:
                    if type(position) is not int or not 0 <= position < len(data):
                        raise _Rejected("bounded row position")
                    self.edge(2)
                    self.copy(key)
                    name = self.text(key)
                    copied_position = self.copy(position)
                    lookup[name] = copied_position
            copied_keys = self.copy(keys)
            copied_data = self.copy(data)  # ALL hidden values, not just visible keys
            self.alloc(256)
            result = {}
            for key in copied_keys:
                if type(key) is not str and type(key) is not quoted_name:
                    raise _Rejected("bounded row keys")
                name = self.text(key)
                if name not in lookup or name in result:
                    raise _Rejected("bounded row keys")
                self.edge(2)
                result[name] = copied_data[lookup[name]]
            if label is not None:
                self.alloc(256)
                self.sidecars.append((label, (copied_keys, copied_data, lookup)))
        else:
            raise _Rejected("exact bounded row")
        if schema is not None and (len(result) != len(schema) or not all(k in result for k in schema)):
            raise _Rejected("complete bounded row columns")
        return result

    def encoded_upper(self):
        # Covers generated wrapper keys/containers too: each charged allocation
        # unit supplies at least one byte of encoding headroom. Ref digit size is
        # bounded by the explicit node limit. This is deliberately conservative.
        return 256 + self.units + self.ascii + 64 * (self.nodes + self.edges + 1)

"""Optional, bounded fresh continuity projection; no permissions or PASS cache.

The old whole-envelope SHA remains the fallback verifier and the baseline's
binding. Selection constructs an invocation-owned immutable event stream. It
does not run a verifier and then retry one: once selected, comparison failure
propagates. Bounds apply only to this extra optimization, never to business
inputs or the existing owned allocation ledger.

This private domain preserves source type/order/alias relations, not pickle's
injected global marker objects. It is never a business/origin fingerprint.
"""

import struct
from dataclasses import dataclass
from typing import NamedTuple

from .errors import DomainError


class _Limits(NamedTuple):
    """Logical bounds for ONE selection construction, not total scope memory.

    At most one baseline plus one selection scratch coexist: <= 2*units for
    this component (also during initial publication's fresh self-comparison).
    Two selections and exact stream comparison cost conservatively no more
    than 2*work + 4*edges + 2*leaf_bytes logical walk/leaf units per check.
    Original PB projections, SQL, codec and business data remain outside these
    additional-work bounds. No CPU/RSS/whole-process guarantee is implied.
    """
    nodes: int
    edges: int
    depth: int
    leaf_bytes: int
    units: int
    work: int
    integer_bits: int


@dataclass(frozen=True)
class _Snapshot:
    events: tuple
    nodes: int
    edges: int
    leaf_bytes: int
    units: int
    work: int


class _Unsuited(Exception):
    """Selection stopped before choosing this optional verifier."""


def _require(ok, message):
    if not ok:
        raise DomainError('VERSION_CONFLICT', message)


def _children(mapping):
    for key, value in dict.items(mapping):
        yield key
        yield value


def _select(values, limits, *, row_type, quoted_type, limits_type,
            row_storage, limit_values, cursor_meta, simple_meta):
    """Fresh nonrecursive full graph, with no caller/container equality hooks.

    Only exact builtin containers and the original two trusted adapters qualify.
    Strong memo entries keep both source and adapter temporaries alive until
    selection finishes. The returned snapshot owns no mutable source objects.
    Completed aliases avoid duplicate traversal *within this invocation* only;
    active-before-completed rejects cycles. Scalars pickle does not memoize do
    not acquire artificial identity requirements (including the empty tuple).
    """
    if type(limits) is not _Limits or not all(type(v) is int and v > 0 for v in limits):
        raise ValueError('explicit positive fresh continuity bounds required')
    memo, active, records = {}, set(), []
    nodes = edges = leaf = units = work = 0

    def charge(n=0, e=0, b=0, u=0, w=1):
        nonlocal nodes, edges, leaf, units, work
        nodes += n
        edges += e
        leaf += b
        units += u
        work += w
        if (nodes > limits.nodes or edges > limits.edges or leaf > limits.leaf_bytes
                or units > limits.units or work > limits.work):
            raise _Unsuited

    # One construction's scratch and records: the prior immutable baseline is
    # separately bounded by the same limit, hence a two-construction peak.
    # Units include records, memo/active/stack slots and leaf retention; they
    # are logical costs, not RSS or a whole-process heap quota.
    stack = [(iter((values,)), 0, None)]
    try:
        while stack:
            iterator, depth, leaving = stack[-1]
            try:
                value = next(iterator)
            except StopIteration:
                stack.pop()
                if leaving is not None:
                    active.remove(leaving)
                continue
            if depth > limits.depth:
                raise _Unsuited
            kind = type(value)
            charge(e=1, u=64)
            if kind is type(None):
                records.append((0,))
                continue
            if kind is bool:
                records.append((1, value))
                continue
            if kind is int:
                bits = int.bit_length(value)
                if bits > limits.integer_bits:
                    raise _Unsuited
                charge(b=(bits + 7) // 8, u=64 + (bits + 7) // 8, w=bits + 1)
                records.append((2, value))
                continue
            if kind is float:
                charge(b=8, u=64)
                # Includes signed zero, NaN payload and infinities. The old
                # pickle domain accepts all float bits; finite-only narrowing
                # belongs to business validators, not this local pin.
                records.append((3, struct.pack('>d', value)))
                continue
            if kind is tuple and not value:
                records.append((4,))
                continue
            if not (kind is str or kind is bytes or kind is dict or kind is list
                    or kind is tuple or kind is row_type or kind is quoted_type
                    or kind is limits_type):
                raise _Unsuited
            identity = id(value)
            _require(identity not in active, 'Cyclic Cold graph input')
            prior = memo.get(identity)
            if prior is not None:
                _require(prior[0] is value, 'Cold continuity identity reused')
                records.append((5, prior[1]))
                continue
            charge(n=1, u=768)
            ordinal = len(memo)
            memo[identity] = value, ordinal
            if kind is str or kind is bytes:
                size = len(value) * (4 if kind is str else 1)
                charge(b=size, u=size + 128, w=size + 1)
                records.append((6 if kind is str else 7, ordinal, value))
                continue
            if kind is dict:
                charge(w=len(value))
                # Iterate rather than hash foreign keys, even for selection.
                if not all(type(k) is str or type(k) is quoted_type for k in value):
                    raise _Unsuited
                records.append((8, ordinal, len(value)))
                children = _children(value)
            elif kind is list or kind is tuple:
                records.append((9 if kind is list else 10, ordinal, len(value)))
                children = iter(value)
            elif kind is row_type:
                # Bound the adapter's lookup allocation BEFORE invoking it.
                # Every foreign index entry costs traversal but is never hashed
                # or compared. Original helper retains all keys/data/index gates.
                parent = object.__getattribute__(value, '_parent')
                data = object.__getattribute__(value, '_data')
                index = object.__getattribute__(value, '_key_to_index')
                if not ((type(parent) is cursor_meta or type(parent) is simple_meta)
                        and type(data) is tuple and type(index) is dict):
                    raise _Unsuited
                keys = object.__getattribute__(parent, '_keys')
                if type(keys) is not list:
                    raise _Unsuited
                charge(u=1024 + 256 * (len(index) + len(keys)),
                       w=len(index) + len(keys) + 1)
                for key in index:
                    if type(key) is quoted_type:
                        charge(u=4 * len(key), w=len(key) + 1)
                records.append((11, ordinal))
                children = iter((row_storage(value),))
            elif kind is limits_type:
                charge(u=4096, w=64)
                records.append((12, ordinal))
                children = iter((limit_values(value),))
            else:
                charge(u=128 + 4 * len(value), w=len(value) + 1)
                records.append((13, ordinal))
                children = iter((str(value),))
            active.add(identity)
            stack.append((children, depth + 1, identity))
        # Tuple construction overlaps the list; charged before allocating it.
        charge(u=64 + 8 * len(records), w=len(records))
        return _Snapshot(tuple(records), nodes, edges, leaf, units, work)
    except _Unsuited:
        return None


def _same(snapshot, baseline):
    """Both operands are owned immutable streams; no callbacks or live aliases."""
    _require(type(snapshot) is _Snapshot and type(baseline) is _Snapshot,
             'Exact Cold continuity snapshots required')
    return snapshot.events == baseline.events

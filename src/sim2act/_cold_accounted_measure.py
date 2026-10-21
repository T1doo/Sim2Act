"""Offline size meter for an already prepared native component value.

This is not a raw-fact preflight, validator, capability or product admission
route. RowMapping/Pydantic adapters are outside its domain. The explicit SQLite
budget experiment may meter a private native copy only after reserving scratch.
No source values or encoded body escape a call; no production limits exist here.
"""

import math
import sys
from dataclasses import dataclass
from typing import Any

from sqlalchemy.sql.elements import quoted_name

HEADER = b"SIM2ACT_ACCOUNTED_COMPONENT_VALUES_V1\x00"


@dataclass(frozen=True)
class Limits:
    nodes: int
    edges: int
    depth: int
    leaf_bytes: int
    encoded_bytes: int
    integer_bits: int  # Also bounds temporary integer arithmetic, not a product limit.


@dataclass(frozen=True)
class Measurement:
    complete: bool
    reason: str | None
    nodes: int
    edges: int
    depth: int
    leaf_bytes: int
    string_utf8_bytes: int
    string_ascii_bytes: int
    base64_ascii_bytes: int
    encoded_bytes: int


class _Stop(Exception):
    pass


def _digits(value):
    """Decimal digits without making a decimal string; caller bounds bit_length."""
    bits = value.bit_length()
    if not bits:
        return 1
    # 30103/100000 > log10(2). Temporary powers are bounded by a small
    # constant multiple of the admitted integer_bits, without decimal strings.
    low, high = 1, bits * 30103 // 100000 + 1
    while low < high:
        mid = (low + high) // 2
        if value < 10**mid:
            high = mid
        else:
            low = mid + 1
    return low


def measure_prepared(value, limits):
    """Exact _freeze encoding size on success, prefix observations on failure.

    Traverses the same object identities, in insertion/sequence order. The input
    must stay unchanged during this synchronous call. O(nodes+depth) auxiliary
    references, no recursive Python calls or full string/base64/node-table copy.
    All work ceilings are explicit; callers are responsible for sensible caps.
    A complete result confers neither immutability nor permission to issue.
    """
    if type(limits) is not Limits or not all(
        type(v) is int and v > 0 for v in vars(limits).values()
    ):
        raise ValueError("explicit positive diagnostic limits required")
    nodes = edges = depth_seen = leaf = utf8 = escaped = b64 = 0
    # JSON [root,[nodes...]]; the first allocated node is always root index 0.
    encoded = len(HEADER) + len("[0,[]]")
    active = set()
    done: dict[int, tuple[Any, int, int]] = {}  # strong source, index, descendant height
    stack: list[list[Any]] = []

    def charge(amount):
        nonlocal encoded
        encoded += amount
        if encoded > limits.encoded_bytes:
            raise _Stop("encoded_bytes")

    def charge_leaf(amount):
        nonlocal leaf
        leaf += amount
        if leaf > limits.leaf_bytes:
            raise _Stop("leaf_bytes")

    def children(item, kind):
        if kind is dict:
            for key, child in dict.items(item):
                if type(key) is not str and type(key) is not quoted_name:
                    raise _Stop("unsupported_mapping_key")
                # These exact key types share str equality/hash. An ordinary
                # dict cannot contain two keys with the same normalized text.
                yield key
                yield child
        else:
            yield from item

    def delivered(ref, height):
        if not stack:
            return
        frame = stack[-1]
        frame[4] = max(frame[4], height + 1)
        position = frame[5]
        frame[5] += 1
        # Bodies are [refs...] or [[key_ref,value_ref],...]. Count punctuation
        # incrementally, never build the refs table or its encoding.
        if frame[6] is dict:
            punctuation = (2 + (position > 0)) if position % 2 == 0 else 1
        else:
            punctuation = int(position > 0)
        charge(_digits(ref) + punctuation)

    def enter(item, depth):
        nonlocal nodes, depth_seen, utf8, escaped, b64
        depth_seen = max(depth_seen, depth)
        if depth > limits.depth:
            raise _Stop("depth")
        kind = type(item)
        if not any(kind is allowed for allowed in
                   (dict, list, tuple, bytes, str, quoted_name, int, bool, float, type(None))):
            raise _Stop("unsupported_type")
        identity = id(item)
        if identity in active:
            raise _Stop("cycle")
        if identity in done:
            original, ref, height = done[identity]
            assert original is item
            depth_seen = max(depth_seen, depth + height)
            if depth + height > limits.depth:
                raise _Stop("depth")
            delivered(ref, height)
            return
        if nodes >= limits.nodes:
            raise _Stop("nodes")
        ref = nodes
        nodes += 1
        # Node ['tag',body], with a JSON-quoted tag and comma/brackets.
        tag = "quoted" if kind is quoted_name else "none" if item is None else kind.__name__
        charge(5 + len(tag) + int(ref > 0))
        if kind is dict or kind is list or kind is tuple:
            size = len(item) * (2 if kind is dict else 1)
            # Refuse a huge shallow container before even creating an iterator.
            if edges + size > limits.edges:
                raise _Stop("edges")
            charge(2)  # empty body []; each child adds refs/punctuation later
            active.add(identity)
            stack.append([item, ref, depth, iter(children(item, kind)), 0, 0, kind])
            return
        if kind is str or kind is quoted_name:
            if len(item) > limits.leaf_bytes - leaf:
                raise _Stop("leaf_bytes")
            charge(2)  # JSON string quotes
            for char in item:
                cp = ord(char)
                width = 1 if cp < 128 else 2 if cp < 2048 else 3 if cp < 65536 else 4
                charge_leaf(width)  # UTF-8 surrogatepass; no whole encode()
                utf8 += width
                if char in ('"', "\\", "\b", "\t", "\n", "\f", "\r"):
                    ascii_width = 2
                else:
                    ascii_width = 6 if cp < 32 or 127 <= cp < 65536 else 12 if cp >= 65536 else 1
                escaped += ascii_width
                charge(ascii_width)
        elif kind is bytes:
            charge_leaf(len(item))
            size = 4 * ((len(item) + 2) // 3)
            b64 += size
            charge(2 + size)  # base64 JSON string; no b64encode()
        elif kind is int:
            bits = item.bit_length()
            if bits > limits.integer_bits:
                raise _Stop("integer_bits")
            charge_leaf(max(1, (bits + 7) // 8))
            digits = _digits(item if item >= 0 else -item)
            digit_limit = sys.get_int_max_str_digits()
            if digit_limit and digits > digit_limit:
                raise _Stop("runtime_integer_digits")
            charge(digits + int(item < 0))
        elif kind is bool:
            charge_leaf(1)
            charge(4 if item else 5)
        elif kind is float:
            if not math.isfinite(item):
                raise _Stop("nonfinite")
            charge_leaf(8)
            charge(2 + len(item.hex()))
        else:
            charge(4)  # null
        done[identity] = (item, ref, 0)
        delivered(ref, 0)

    reason = None
    try:
        charge(0)
        enter(value, 0)
        while stack:
            frame = stack[-1]
            try:
                child = next(frame[3])
            except StopIteration:
                stack.pop()
                item, ref, _, _, height, _, _ = frame
                active.remove(id(item))
                done[id(item)] = (item, ref, height)
                delivered(ref, height)
                continue
            edges += 1
            if edges > limits.edges:
                raise _Stop("edges")
            enter(child, frame[2] + 1)
    except _Stop as stop:
        reason = str(stop)
    except RuntimeError:
        # Native container mutation during iteration: never an eligibility proof.
        reason = "concurrent_mutation"
    return Measurement(
        reason is None, reason, nodes, edges, depth_seen, leaf, utf8, escaped, b64, encoded
    )

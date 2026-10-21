"""Offline accounted-family representation proof; no runtime integration/permit.

All limits below are explicit proof-input limits, NOT new product defaults.
Flat node references prevent repeated DAG paths from expanding during encoding.
"""
import base64
import hashlib
import json
import math
from typing import NamedTuple

from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import quoted_name
from sim2act.natural_spec_runtime import _cold_graph_row_storage


class Rejected(ValueError):
    pass


class Bounds(NamedTuple):
    nodes: int
    edges: int
    depth: int
    leaf_bytes: int
    encoded_bytes: int


class Packet(NamedTuple):
    root: int
    nodes: tuple
    encoded: bytes
    digest: str
    edges: int


def freeze(value, bounds):
    """One invocation, no cross-call cache; no source reference in the result."""
    if type(bounds) is not Bounds or not all(type(v) is int and v > 0 for v in bounds):
        raise Rejected('explicit positive proof bounds required')
    nodes, done, active, heights = [], {}, set(), {}
    edge_count = leaf_bytes = 0

    def visit(item, depth):
        nonlocal edge_count, leaf_bytes
        if depth > bounds.depth:
            raise Rejected('depth')
        kind = type(item)
        if not (kind is dict or kind is list or kind is tuple or kind is bytes
                or kind is str or kind is int or kind is bool or kind is float
                or item is None or kind is RowMapping or kind is quoted_name):
            raise Rejected('unknown type')
        identity = id(item)
        if identity in active:
            raise Rejected('cycle')
        if identity in done:
            original, index = done[identity]
            assert original is item
            if depth + heights[index] > bounds.depth:
                raise Rejected('depth')
            return index
        if len(nodes) >= bounds.nodes:
            raise Rejected('nodes')
        index = len(nodes)
        nodes.append(None)
        active.add(identity)

        child_refs = []
        def child(value):
            nonlocal edge_count
            edge_count += 1
            if edge_count > bounds.edges:
                raise Rejected('edges')
            ref = visit(value, depth + 1)
            child_refs.append(ref)
            return ref

        if kind is dict:
            keys = tuple(dict.keys(item))
            if not all(type(k) is str for k in keys):
                raise Rejected('mapping keys')
            node = ('dict', tuple((child(k), child(item[k])) for k in keys))
        elif kind is list or kind is tuple:
            node = ('list' if kind is list else 'tuple', tuple(child(v) for v in item))
        elif kind is RowMapping:
            # Full keys/data/safe-index payload, including hidden positions.
            storage = _cold_graph_row_storage(item)
            names = tuple(str(key) for key in storage[0])
            if len(set(names)) != len(names):
                raise Rejected('duplicate row keys')
            node = ('row', child(storage))
        elif kind is bytes:
            leaf_bytes += len(item)
            node = ('bytes', item)
        elif kind is str or kind is quoted_name:
            text = item if kind is str else str(item)
            leaf_bytes += len(text.encode('utf-8'))
            node = ('str' if kind is str else 'quoted', text)
        elif kind is float:
            if not math.isfinite(item):
                raise Rejected('nonfinite')
            leaf_bytes += 8
            node = ('float', item.hex())
        elif kind is int:
            leaf_bytes += max(1, (item.bit_length() + 7) // 8)
            node = ('int', item)
        elif kind is bool:
            leaf_bytes += 1
            node = ('bool', item)
        else:
            node = ('none', None)
        if leaf_bytes > bounds.leaf_bytes:
            raise Rejected('leaf bytes')
        nodes[index] = node
        heights[index] = max((heights[ref] + 1 for ref in child_refs), default=0)
        active.remove(identity)
        # Reuse only completed immutable subvalues; retain source until done.
        done[identity] = item, index
        return index

    root = visit(value, 0)
    frozen = tuple(nodes)
    flat = tuple((tag, base64.b64encode(body).decode('ascii')) if tag == 'bytes'
                 else (tag, body) for tag, body in frozen)
    chunks = [b'OFFLINE_ACCOUNTED_GRAPH_PROOF_V1\x00']
    total = len(chunks[0])
    for chunk in json.JSONEncoder(ensure_ascii=True, allow_nan=False,
            separators=(',', ':')).iterencode((root, flat)):
        encoded = chunk.encode('ascii')
        total += len(encoded)
        if total > bounds.encoded_bytes:
            raise Rejected('encoded bytes')
        chunks.append(encoded)
    encoded = b''.join(chunks)
    return Packet(root, frozen, encoded, hashlib.sha256(encoded).hexdigest(), edge_count)


class View(NamedTuple):
    """Immutable read interface; deliberately not a model, mapping or permit."""
    packet: Packet
    ref: int

    def __len__(self):
        tag, body = self.packet.nodes[self.ref]
        if tag in ('dict', 'list', 'tuple'):
            return len(body)
        if tag == 'row':
            return len(resolve(self.packet, body)[0])
        raise TypeError('not a container')

    def __getitem__(self, key):
        tag, body = self.packet.nodes[self.ref]
        if tag in ('tuple', 'list'):
            if type(key) is not int:
                raise TypeError('exact integer key required')
            return resolve(self.packet, body[key])
        if tag == 'dict':
            if type(key) is not str:
                raise TypeError('exact string key required')
            for name, child in body:
                if resolve(self.packet, name) == key:
                    return resolve(self.packet, child)
            raise KeyError(key)
        if tag == 'row':
            if type(key) is not str:
                raise TypeError('exact string key required')
            payload = resolve(self.packet, body)
            return payload[1][payload[2][key]]
        raise TypeError('not a container')

    def __iter__(self):
        tag, body = self.packet.nodes[self.ref]
        if tag == 'dict':
            return (resolve(self.packet, key) for key, _ in body)
        if tag in ('list', 'tuple'):
            return (resolve(self.packet, ref) for ref in body)
        if tag == 'row':
            return iter(resolve(self.packet, body)[0])
        raise TypeError('not a container')

    def items(self):
        return tuple((key, self[key]) for key in self)


def resolve(packet, ref=None):
    ref = packet.root if ref is None else ref
    tag, body = packet.nodes[ref]
    if tag in ('dict', 'list', 'tuple', 'row'):
        return View(packet, ref)
    if tag == 'float':
        return float.fromhex(body)
    return body


def materialize_oracle(packet):
    """TEST ORACLE ONLY: detached data for existing fingerprint comparisons.

    This is not the proposed consumer API. Uses completed-node memo too.
    """
    done = {}

    def copy(ref):
        if ref in done:
            return done[ref]
        tag, body = packet.nodes[ref]
        if tag == 'dict':
            result = {copy(k): copy(v) for k, v in body}
        elif tag in ('tuple', 'list'):
            items = [copy(v) for v in body]
            result = tuple(items) if tag == 'tuple' else items
        elif tag == 'row':
            keys, data, index = copy(body)
            result = {str(key): data[index[str(key)]] for key in keys}
        else:
            result = resolve(packet, ref)
        done[ref] = result
        return result
    return copy(packet.root)

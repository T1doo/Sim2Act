"""Uninstalled whole-content handoff experiment, never dispatch authority.

One complete capture preserves model storage / raw-dict / hidden-row aliases.
It intentionally does NOT claim producer timing, all-consumer migration or a
production capacity proof. Runtime imports are explicit isolated opt-in only. Dynamic SQL and
business authority remain the original caller's job; no PASS is cached here.
"""

import base64
import hashlib
import json
import math
import sys
from dataclasses import dataclass

from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import quoted_name

from . import _cold_base_segment as segments
from . import natural_live_admission as gate
from . import natural_spec_runtime as runtime
from ._cold_accounted_budget import _Capacity, _Ledger, _Limits, _Unsupported
from ._cold_accounted_values import _Bounds, _Rejected

# These are content inventories, not proof that the actual runtime used them.
# Repeated producers are named separately; no None placeholders or first->second
# substitution qualifies a runtime closure.
_FAMILIES = {
    'trial': ('base',),
    'binding': ('base',),
    'ledger': ('base',),
    'authorities': ('first', 'second'),
    'source': ('first', 'second'),
    'context': ('first', 'second'),
    'settlement': ('input', 'received', 'parsed'),
}
_ROOT = 'cold-settlement:isolated-owned-inputs'
_TAG = b'SIM2ACT_OWNED_SETTLEMENT_EXPERIMENT_V1\x00'

def _is(kind, choices):
    return any(kind is choice for choice in choices)


@dataclass(frozen=True, slots=True)
class _Image:
    nodes: tuple
    root: int
    encoded: bytes
    digest: str
    edges: int


class _Capture:
    def __init__(self, ledger):
        self.b = ledger
        self.ticket = ledger.reserve()
        self.nodes, self.done, self.active, self.heights = [], {}, set(), {}
        self.edges = self.leaf = self.model_payload = 0
        self.allowed = gate._trial_typed_nested_classes()

    def alloc(self, units):
        self.b.spend(units)
        self.ticket.grow(units)

    def visit(self, value, depth=0):
        self.b.spend()
        if depth > min(self.b.bounds.depth, (sys.getrecursionlimit() - 200) // 6):
            raise _Capacity('capture_depth')
        kind, identity = type(value), id(value)
        model = any(kind is cls for cls in self.allowed)
        if not (_is(kind, (dict, list, tuple, bytes, str, int, float, bool, type(None),
                         RowMapping, quoted_name)) or model):
            raise _Unsupported('capture_type')
        if identity in self.active:
            raise _Rejected('cycle in settlement capture')
        if identity in self.done:
            original, ref = self.done[identity]
            assert original is value
            if depth + self.heights[ref] > self.b.bounds.depth:
                raise _Capacity('capture_depth')
            return ref
        if len(self.nodes) >= self.b.bounds.nodes:
            raise _Capacity('capture_nodes')
        self.alloc(512)
        ref = len(self.nodes)
        self.nodes.append(None)
        self.active.add(identity)
        children = []

        def child(item):
            if self.edges >= self.b.bounds.edges:
                raise _Capacity('capture_edges')
            self.edges += 1
            self.alloc(128)
            result = self.visit(item, depth + 1)
            children.append(result)
            return result

        if model:
            raw = object.__getattribute__(value, '__dict__')
            fields = type.__getattribute__(kind, '__pydantic_fields__')
            selected = object.__getattribute__(value, '__pydantic_fields_set__')
            if (type(raw) is not dict or type(fields) is not dict or type(selected) is not set
                    or not all(type(k) is str for k in raw)
                    or not all(type(k) is str for k in fields)
                    or not all(type(k) is str for k in selected)
                    or raw.keys() != fields.keys() or not selected <= fields.keys()
                    or object.__getattribute__(value, '__pydantic_extra__') is not None
                    or object.__getattribute__(value, '__pydantic_private__') is not None):
                raise _Rejected('complete fixed settlement model required')
            self.alloc(256 + 128 * len(selected))
            # Visit the ORIGINAL __dict__ node: a raw root pointing to it must
            # share this reference, not a second typed-projection dictionary.
            schema = kind.__module__ + '.' + kind.__qualname__
            self.model_payload += 256 + 8 * len(schema) + 128 * len(selected)
            body = ('model', (schema, child(raw), tuple(sorted(selected))))
        elif kind is RowMapping:
            parent = object.__getattribute__(value, '_parent')
            data = object.__getattribute__(value, '_data')
            index = object.__getattribute__(value, '_key_to_index')
            if (not _is(type(parent), (runtime._ColdGraphCursorMeta, runtime._ColdGraphSimpleMeta))
                    or type(data) is not tuple or type(index) is not dict):
                raise _Rejected('complete settlement row storage required')
            keys = object.__getattribute__(parent, '_keys')
            if type(keys) is not list:
                raise _Rejected('complete settlement row keys required')
            # Pay before lookup allocation/hashing. Foreign key objects are
            # traversed, but their hash/equality/serializer are never invoked.
            self.alloc(256 + 512 * (len(index) + len(keys)))
            width = sum(len(k) for k in dict.keys(index)
                        if type(k) is str or type(k) is quoted_name)
            self.b.spend(8 * width * (len(index) + len(keys) + 1))
            lookup = {}
            for key, position in dict.items(index):
                if type(key) is str or type(key) is quoted_name:
                    if type(position) is not int or not 0 <= position < len(data):
                        raise _Rejected('complete settlement row position required')
                    lookup[str(key)] = position
            for key in keys:
                if not _is(type(key), (str, quoted_name)) or str(key) not in lookup:
                    raise _Rejected('complete settlement row keys required')
            body = ('row', (child(keys), child(data), child(lookup)))
        elif kind is dict:
            self.alloc(128 * len(value))
            if not all(_is(type(k), (str, quoted_name)) for k in dict.keys(value)):
                raise _Unsupported('capture_mapping_key')
            body = ('dict', tuple((child(k), child(v)) for k, v in dict.items(value)))
        elif _is(kind, (list, tuple)):
            self.alloc(128 * len(value))
            body = ('list' if kind is list else 'tuple', tuple(child(v) for v in value))
        elif _is(kind, (str, quoted_name, bytes)):
            upper = len(value) * (4 if kind is not bytes else 1)
            self.leaf += upper
            self.alloc(128 + 8 * upper)
            body = ('bytes', value) if kind is bytes else (
                'quoted' if kind is quoted_name else 'str', str(value))
        elif kind is float:
            if not math.isfinite(value):
                raise _Rejected('nonfinite settlement value')
            self.leaf += 8
            body = ('float', value.hex())
        elif kind is int:
            if value.bit_length() > self.b.limits.integer_bits:
                raise _Capacity('capture_integer_bits')
            self.leaf += max(1, (value.bit_length() + 7) // 8)
            body = ('int', value)
        else:
            self.leaf += 1
            body = ('bool', value) if kind is bool else ('none', None)
        if self.leaf > self.b.bounds.leaf_bytes:
            raise _Capacity('capture_leaf_bytes')
        self.nodes[ref] = body
        self.heights[ref] = max((self.heights[n] + 1 for n in children), default=0)
        self.active.remove(identity)
        self.done[identity] = value, ref
        return ref

    def finish(self, value):
        root = self.visit(value)
        # Conservative logical headroom before base64/flat/JSON/chunk/join
        # allocations. This is neither a heap quota nor a production bound.
        upper = 1024 + 64 * self.leaf + 1024 * (len(self.nodes) + self.edges)
        if upper > self.b.bounds.encoded_bytes:
            raise _Capacity('capture_encoding')
        self.alloc(10 * upper)
        frozen = tuple(self.nodes)
        flat = tuple((tag, base64.b64encode(body).decode('ascii')) if tag == 'bytes'
                     else (tag, body) for tag, body in frozen)
        encoded = _TAG + json.dumps((root, flat), ensure_ascii=True, allow_nan=False,
                                   separators=(',', ':')).encode('ascii')
        assert len(encoded) <= upper
        return _Image(frozen, root, encoded, hashlib.sha256(encoded).hexdigest(), self.edges)

    def close(self):
        self.nodes.clear()
        self.done.clear()  # no borrowed mutable source survives capture
        self.active.clear()
        self.ticket.close()


class _Handle:
    __slots__ = ()


class _View:
    __slots__ = ('_scope', '_ref')

    def __init__(self, scope, ref):
        object.__setattr__(self, '_scope', scope)
        object.__setattr__(self, '_ref', ref)

    def __setattr__(self, name, value):
        raise _Rejected('immutable settlement view')

    def _node(self):
        if type(self._scope) is not _Scope:
            raise _Rejected('unissued settlement scope')
        self._scope._current()
        if (type(self._ref) is not int or not 0 <= self._ref < len(self._scope._views)
                or self._scope._views[self._ref] is not self):
            raise _Rejected('unissued settlement view')
        return self._scope._image.nodes[self._ref]

    @property
    def tag(self):
        return self._node()[0]

    def field(self, name):
        if type(name) is not str:
            raise _Rejected('exact settlement field required')
        tag, body = self._node()
        if tag == 'model':
            return self._scope._view(body[1]).field(name)
        if tag == 'row':
            position = self._scope._view(body[2]).field(name).scalar()
            return self._scope._view(body[1]).at(position)
        if tag != 'dict':
            raise _Rejected('settlement mapping required')
        for key, value in body:
            if self._scope._image.nodes[key][1] == name:
                return self._scope._view(value)
        raise _Rejected('missing settlement field')

    def at(self, index):
        tag, body = self._node()
        if tag not in ('list', 'tuple') or type(index) is not int or not 0 <= index < len(body):
            raise _Rejected('exact settlement sequence index required')
        return self._scope._view(body[index])

    def scalar(self):
        tag, body = self._node()
        if tag not in ('str', 'quoted', 'bytes', 'int', 'bool', 'float', 'none'):
            raise _Rejected('settlement scalar required')
        return float.fromhex(body) if tag == 'float' else body

    def same_node(self, other):
        self._node()
        if type(other) is not _View:
            return False
        other._node()
        return self._scope is other._scope and self._ref == other._ref


class _Scope:
    def __init__(self, graph, image, ledger, retained):
        self._graph, self._image, self._ledger, self._retained = graph, image, ledger, retained
        self._handle, self._active = _Handle(), True
        self._nonce, self._epoch, self._phase = graph.nonce, graph.epoch, graph.phase
        self._binding = graph.binding
        self._contract = graph.binding.contract
        self._header = tuple(object.__getattribute__(graph.binding, name) for name in
                             ('approval_key', 'account_id', 'version', 'contract_fingerprint'))
        self._views = tuple(_View(self, ref) for ref in range(len(image.nodes)))

    def _view(self, ref):
        self._current()
        return self._views[ref]

    def _current(self):
        try:
            if not self._active or self._image is None:
                raise _Rejected('closed owned settlement')
            runtime._ColdGraphRead._check_dynamic(self._graph, self._graph.store,
                                                self._graph.connection)
            if self._binding is not self._graph.binding:
                raise _Rejected('owned settlement binding changed')
            header = tuple(object.__getattribute__(self._binding, name) for name in
                           ('approval_key', 'account_id', 'version', 'contract_fingerprint'))
            if (self._nonce is not self._graph.nonce or self._epoch != self._graph.epoch
                    or self._phase != self._graph.phase or self._binding is not self._graph.binding
                    or self._contract is not self._graph.binding.contract
                    or self._graph.worker.stop.is_set()
                    or not all(type(v) is str for v in header) or header != self._header):
                raise _Rejected('owned settlement generation changed')
        except BaseException:
            self.close()
            raise

    def family(self, handle, family, boundary):
        self._current()
        if (handle is not self._handle or type(family) is not str or type(boundary) is not str
                or family not in _FAMILIES or boundary not in _FAMILIES[family]):
            raise _Rejected('unissued settlement family or boundary')
        return self._view(self._image.root).field(family).field(boundary)

    def close(self):
        if self._active:
            self._active = False
            self._image = None
            self._views = ()
            self._retained.close()
            self._ledger.close()


@dataclass(frozen=True)
class _Selection:
    route: str
    reason: str
    scope: object = None
    handle: object = None


def _select_complete_inner(graph, families, models, bounds, limits):
    """Explicit SQLite experiment ONLY, after all named outputs actually exist.

    This is necessarily late in a settlement and does not optimize _prepare.
    No existing runtime consumer is switched; original full guards remain.
    """
    if (type(graph) is not runtime._ColdGraphRead or not graph.store.test_only
            or not graph.store.sqlite or type(bounds) is not _Bounds or type(limits) is not _Limits):
        raise _Rejected('explicit isolated settlement configuration required')
    if type(graph.inputs) is not dict or graph.inputs.get(_ROOT) is not families:
        raise _Rejected('complete handoff inventory must be in the original full graph read set')
    graph.check(graph.store, graph.connection)
    gate._trial_typed_values(models)
    if (type(families) is not dict or not all(type(k) is str for k in families)
            or set(families) != set(_FAMILIES)
            or any(type(families[k]) is not dict
                   or not all(type(v) is str for v in families[k])
                   or set(families[k]) != set(variants)
                   or any(v is None for v in families[k].values())
                   for k, variants in _FAMILIES.items())):
        raise _Rejected('complete actual settlement inventory required')
    if not segments.fixed_serializers(models) or not segments.serializers_current():
        return _Selection('LEGACY', 'unknown_serializer')
    ledger = _Ledger(bounds, limits)
    capture = scope = None
    try:
        capture = _Capture(ledger)
        try:
            image = capture.finish(families)
            retained = ledger.reserve('resident', len(image.encoded) + 1024 * len(image.nodes)
                                      + 512 * image.edges + 8 * capture.leaf
                                      + capture.model_payload)
        except _Capacity as error:
            # Complete original validation still runs before capacity fallback.
            graph.check(graph.store, graph.connection)
            gate._trial_typed_values(models)
            return _Selection('LEGACY', error.reason)
        graph.check(graph.store, graph.connection)
        gate._trial_typed_values(models)
        scope = _Scope(graph, image, ledger, retained)
        scope._current()
        return _Selection('OWNED', 'isolated_complete_capture_only', scope, scope._handle)
    finally:
        if capture is not None:
            capture.close()
        if scope is None:
            ledger.close()


def _select_complete(graph, families, models, bounds, limits):
    try:
        return _select_complete_inner(graph, families, models, bounds, limits)
    except BaseException:
        if type(graph) is runtime._ColdGraphRead:
            graph.invalidate()
        raise


class _NativeCopy:
    """Direct unique native graph, not _Image thaw; one handoff-version memo.

    No dynamic reader/connection is copied. Exact model/native types let fixed
    existing pure consumers use the transferred values. Read-only/no-escape
    qualification of the entire consumer closure is STILL required before any
    content guard exemption; this bridge itself exempts none.
    """

    def __init__(self, ledger):
        self.b = ledger
        self.ticket = ledger.reserve()
        self.done, self.active = {}, set()
        self.allowed = gate._trial_typed_nested_classes()
        self.nodes = self.edges = self.leaf = 0
        frame, level = sys._getframe(), 0
        while frame is not None:
            level += 1
            frame = frame.f_back
        self.depth = min(ledger.bounds.depth, max(0, (sys.getrecursionlimit() - level - 100) // 6))

    def allocate(self, units):
        self.b.spend(units)
        self.ticket.grow(units)

    def copy(self, value, depth=0):
        self.b.spend()
        kind, ident = type(value), id(value)
        if depth > self.depth:
            raise _Capacity('native_depth')
        if ident in self.active:
            raise _Rejected('cycle in native handoff')
        if ident in self.done:
            old, result, height = self.done[ident]
            assert old is value
            if depth + height > self.depth:
                raise _Capacity('native_depth')
            return result
        if self.nodes >= self.b.bounds.nodes:
            raise _Capacity('native_nodes')
        model = any(kind is t for t in self.allowed)
        if not (model or _is(kind, (dict, list, tuple, bytes, str, int, float, bool,
                                    type(None), RowMapping, quoted_name))):
            raise _Unsupported('native_type')
        self.nodes += 1
        self.allocate(512)
        self.active.add(ident)
        height = 0

        def child(item):
            nonlocal height
            if self.edges >= self.b.bounds.edges:
                raise _Capacity('native_edges')
            self.edges += 1
            self.allocate(128)
            result = self.copy(item, depth + 1)
            height = max(height, self.done[id(item)][2] + 1)
            return result

        if model:
            raw = object.__getattribute__(value, '__dict__')
            fields = type.__getattribute__(kind, '__pydantic_fields__')
            selected = object.__getattribute__(value, '__pydantic_fields_set__')
            if (type(raw) is not dict or type(fields) is not dict or type(selected) is not set
                    or not all(type(k) is str for k in raw)
                    or not all(type(k) is str for k in fields)
                    or not all(type(k) is str for k in selected)
                    or raw.keys() != fields.keys() or not selected <= fields.keys()
                    or object.__getattribute__(value, '__pydantic_extra__') is not None
                    or object.__getattribute__(value, '__pydantic_private__') is not None):
                raise _Rejected('exact native model storage required')
            self.allocate(256 + 128 * len(selected))
            result = object.__new__(kind)
            object.__setattr__(result, '__dict__', child(raw))
            object.__setattr__(result, '__pydantic_fields_set__', set(selected))
            object.__setattr__(result, '__pydantic_extra__', None)
            object.__setattr__(result, '__pydantic_private__', None)
        elif kind is RowMapping:
            parent = object.__getattribute__(value, '_parent')
            data = object.__getattribute__(value, '_data')
            index = object.__getattribute__(value, '_key_to_index')
            if (not _is(type(parent), (runtime._ColdGraphCursorMeta, runtime._ColdGraphSimpleMeta))
                    or type(data) is not tuple or type(index) is not dict):
                raise _Rejected('exact native row storage required')
            keys = object.__getattribute__(parent, '_keys')
            if type(keys) is not list:
                raise _Rejected('exact native row keys required')
            self.allocate(512 * (len(index) + len(keys) + 1))
            self.b.spend(8 * sum(len(k) for k in dict.keys(index)
                                if _is(type(k), (str, quoted_name)))
                         * (len(index) + len(keys) + 1))
            lookup = {}
            for key, position in dict.items(index):
                if _is(type(key), (str, quoted_name)):
                    if type(position) is not int or not 0 <= position < len(data):
                        raise _Rejected('exact native row position required')
                    lookup[str(key)] = position
            if any(not _is(type(k), (str, quoted_name)) or str(k) not in lookup for k in keys):
                raise _Rejected('complete native row keys required')
            copied_keys, copied_data = child(keys), child(data)
            from sqlalchemy.engine.result import SimpleResultMetaData
            meta = SimpleResultMetaData(copied_keys)
            # Keep the copied keys node itself, including an alias to another
            # root; the constructor's separate list is not the owned node.
            object.__setattr__(meta, '_keys', copied_keys)
            result = RowMapping(meta, None, lookup, copied_data)
        elif kind is dict:
            if not all(_is(type(k), (str, quoted_name)) for k in dict.keys(value)):
                raise _Unsupported('native_key')
            self.allocate(128 * len(value))
            result = {child(k): child(v) for k, v in dict.items(value)}
        elif kind is list or kind is tuple:
            self.allocate(128 * len(value))
            items = [child(v) for v in value]
            result = items if kind is list else tuple(items)
        elif kind is quoted_name:
            quote = object.__getattribute__(value, 'quote')
            if type(quote) is not bool and quote is not None:
                raise _Unsupported('native_quote_layout')
            self.leaf += 4 * len(value)
            self.allocate(128 + 32 * len(value))
            result = quoted_name(str(value), quote)
        elif kind is str or kind is bytes:
            self.leaf += 4 * len(value) if kind is str else len(value)
            result = value  # actually immutable native leaves may be shared
        elif kind is float:
            if not math.isfinite(value):
                raise _Rejected('nonfinite native handoff')
            self.leaf += 8
            result = value
        elif kind is int:
            if value.bit_length() > self.b.limits.integer_bits:
                raise _Capacity('native_integer_bits')
            self.leaf += max(1, (value.bit_length() + 7) // 8)
            result = value
        else:
            self.leaf += 1
            result = value
        if self.leaf > self.b.bounds.leaf_bytes:
            raise _Capacity('native_leaf_bytes')
        self.active.remove(ident)
        self.done[ident] = value, result, height
        return result

    def close(self):
        self.done.clear()
        self.active.clear()
        self.ticket.close()


class _NativeModels:
    """Explicit test-only paired handoff; NO guard or runtime eligibility waiver.

    The private native copies are the only copies retained by this bridge.
    Source inputs/memo are dropped per version. Old full typed and content guards
    remain installed until all seven-family consumer closure is proved.
    """

    def __init__(self, graph, bounds, limits):
        if (type(graph) is not runtime._ColdGraphRead or not graph.store.test_only
                or not graph.store.sqlite):
            raise _Rejected('isolated native model handoff only')
        graph.check(graph.store, graph.connection)
        if '_settlement_owned_models' in vars(graph):
            raise _Rejected('one native handoff owner per exact graph')
        self.graph, self.ledger = graph, _Ledger(bounds, limits)
        self.active, self.version, self._owned = True, 0, []
        self._frame = (graph.nonce, graph.epoch, graph.phase)
        graph._settlement_owned_models = self

    def current(self):
        if not self.active:
            raise _Rejected('closed native model handoff')
        try:
            runtime._ColdGraphRead._check_dynamic(self.graph, self.graph.store, self.graph.connection)
            if (not segments.serializers_current()
                    or not segments.fixed_serializers([
                        (type(pair[0]), pair[0], pair[1]) for _, pair, _ in self._owned])):
                raise _Unsupported('native_fixed_serializers')
            if (self.graph.nonce is not self._frame[0] or self.graph.epoch != self._frame[1]
                    or self.graph.phase != self._frame[2] or self.graph.worker.stop.is_set()):
                raise _Rejected('native model handoff scope changed')
        except BaseException:
            self.close()
            self.graph.invalidate()
            raise

    def issued_pair(self, expected, model):
        """Only explicit transferred objects; never lookup an old source id/PASS."""
        try:
            self.current()
            for _, pair, _ in self._owned:
                if pair[0] is model:
                    if type(model) is not expected:
                        raise _Rejected('native issued model kind changed')
                    gate._trial_typed_values([(expected, model, pair[1])])
                    return pair
            return None
        except BaseException:
            self.close()
            self.graph.invalidate()
            raise

    def produced(self, expected, model, raw):
        copy = None
        try:
            self.current()
            if type(model) is not expected or type(raw) is not dict:
                raise _Rejected('exact paired native producer required')
            if not segments.fixed_serializers([(expected, model, raw)]):
                raise _Unsupported('native_fixed_model_schema')
            gate._trial_typed_values([(expected, model, raw)])
            copy = _NativeCopy(self.ledger)
            pair = copy.copy((model, raw))
            # Retain private objects, including nodes with wide shared edges;
            # pay before adding them to the long-lived owner registry.
            lease = self.ledger.reserve('resident', copy.ticket.units + 8 * copy.leaf)
            self.current()
            if not segments.fixed_serializers([(expected, pair[0], pair[1])]):
                raise _Unsupported('native_fixed_model_schema')
            gate._trial_typed_values([(expected, pair[0], pair[1])])
            self.graph.check(self.graph.store, self.graph.connection)
            self.version += 1
            self._owned.append((self.version, pair, lease))
            return pair
        except BaseException:
            self.close()
            self.graph.invalidate()
            raise
        finally:
            if copy is not None:
                copy.close()

    def close(self):
        self.active = False
        self._owned.clear()
        self.ledger.close()
        if getattr(self.graph, '_settlement_owned_models', None) is self:
            self.graph._settlement_owned_models = None

"""A local content comparison; authority and dynamic gates stay in Graph.check.

A native MATCH means the complete fresh object/reducer structure has the same
values, order, types and alias partition as a full-SHA calibrated snapshot.
Unknown configuration/representation returns None to the original SHA caller.
Native execution errors are never caught or replayed here.
"""

import builtins
import copyreg
import hashlib
import sys
from pathlib import Path
from types import ModuleType

from . import _cold_accounted_native as accounted
from . import cold_accounted as owned
from . import natural_live_admission as typed
from . import natural_spec_runtime as r
from .spec_production import ProductionTrialBinding

try:
    from . import _cold_graph_structure as native
except ImportError:
    native = None

_NATIVE = native
_NATIVE_ENTRIES = (() if native is None else
    tuple((name, getattr(native, name, None)) for name in ('snapshot', 'matches_fast', 'UNSUPPORTED', 'same_classes')))
_NATIVE_SNAPSHOT = None if native is None else getattr(native, 'snapshot', None)
_NATIVE_MATCH = None if native is None else getattr(native, 'matches_fast', None)
_NATIVE_CLASSES = None if native is None else getattr(native, 'same_classes', None)
_UNSUPPORTED = None if native is None else native.UNSUPPORTED
_SOURCE_OK = (native is not None and native.SOURCE_SHA256 ==
    hashlib.sha256(Path(__file__).with_name('_cold_graph_structure.c').read_bytes()).hexdigest())
_BUILTINS = tuple((name, getattr(builtins, name)) for name in (
    'type', 'object', 'str', 'len', 'dict', 'tuple', 'all', 'any', 'set', 'id', '__import__'))
_FUNCTIONS = (
    r._ColdGraphRead.input_bytes, r._ColdGraphRead.input_key, r._ColdGraphRead._frontier_input_key,
    r._ColdGraphRead.invalidate,
    accounted._Frontier.check, accounted._Frontier.values, accounted._Frontier.key,
    accounted._Frontier._refresh, accounted._Frontier.added, accounted.gate.require,
    accounted._NativeCandidate.release, owned._OwnedPrewriteMode.close,
    accounted._NativeCandidate.qualify, accounted._SizingProjection.copy,
    typed._graph_source_upstream_run_equal,
    r._cold_graph_bytes, r._cold_graph_row_storage, r._cold_graph_limit_values,
    r._cold_graph_pickle_marker, r._ColdGraphPickler.reducer_override,
    r.require, r.codec.require, typed.require, typed._trial_typed_storage,
    typed._trial_typed_classes, typed._trial_typed_nested_classes,
)
_CODE = tuple((fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__,
    tuple((fn.__kwdefaults__ or {}).items())) for fn in _FUNCTIONS)
_ALIASES = tuple((owner, name, getattr(owner, name)) for owner, names in (
    (r, ('_cold_graph_bytes', '_cold_graph_row_storage', '_cold_graph_limit_values',
         '_cold_graph_pickle_marker', '_ColdGraphPickler', '_ColdGraphBytesIO',
         '_ColdGraphRowMapping', '_ColdGraphCursorMeta', '_ColdGraphSimpleMeta',
         '_ColdGraphQuotedName', 'Limits', 'require', '_COLD_ROW_LOOKUP',
         '_COLD_ROW_REQUIRE', '_COLD_ROW_LEAF', '_SOURCE_VIEW_TYPE', '_SOURCE_VIEW_PIN', '_SOURCE_OWNER_TYPE', '_SOURCE_OWNER_PIN')),
    (r.codec, ('require',)),
    (accounted, ('rt', 'gate', 'o', '_Frontier', '_NativeCandidate', '_SizingProjection')),
    (owned, ('_OwnedPrewriteMode',)),
    (r._row_native_code, ('_RAW_ROW_LOOKUP', '_RAW_UNSUPPORTED')),
    (typed, ('require', '_trial_typed_storage', '_trial_typed_classes', '_trial_typed_nested_classes')),
) for name in names)
# Resolve inheritance once as code configuration, then compare each current
# heap class's COMPLETE namespace and MRO every call. This is stricter than
# re-resolving 268 individual descriptors and never remembers data or PASS.
_roots = (r._ColdGraphRead, r._ColdGraphPickler, r._ColdGraphRowMapping,
    r._ColdGraphCursorMeta, r._ColdGraphSimpleMeta, r._ColdGraphQuotedName, r.Limits,
    ProductionTrialBinding, accounted._Frontier, accounted._NativeCandidate, accounted._SizingProjection, owned._OwnedPrewriteMode,
    *typed._trial_typed_nested_classes())
_classes = {}
_metas = {}
for _kind in _roots:
    _meta = type(_kind)
    for _ancestor in type.__getattribute__(_meta, '__mro__'):
        _metas[id(_ancestor)] = _ancestor
    for _base in type.__getattribute__(_kind, '__mro__'):
        if type.__getattribute__(_base, '__flags__') & (1 << 9):
            _classes[id(_base)] = _base
_META_CONFIG = tuple((kind, type.__getattribute__(kind, '__mro__'),
    tuple(type.__getattribute__(kind, '__dict__').items())) for kind in _metas.values())
_CLASS_CONFIG = tuple((kind, type(kind), type.__getattribute__(kind, '__mro__'),
    tuple(type.__getattribute__(kind, '__dict__').items())) for kind in _classes.values())
_META_OK = all(type(kind) is type for kind in _metas.values())
del _roots, _classes, _metas, _kind, _meta, _base, _ancestor
_DISPATCH = copyreg.dispatch_table
_DISPATCH_ITEMS = tuple(_DISPATCH.items())
_EXTENSIONS = copyreg._extension_registry
_EXTENSION_ITEMS = tuple(_EXTENSIONS.items())
_MARKER = r._cold_graph_pickle_marker
_MARKER_NAMES = tuple((name, getattr(_MARKER, name))
    for name in ('__module__', '__qualname__', '__name__'))
_SHA = r.hashlib.sha256
_ARGS = (r._ColdGraphRowMapping, r.Limits, r._ColdGraphQuotedName,
    r._cold_graph_row_storage, r._cold_graph_limit_values)


def _same_items(current, items):
    return len(current) == len(items) and all(
        key is old_key and value is old_value
        for (key, value), (old_key, old_value) in zip(current.items(), items, strict=True))


def _fixed_classes():
    # The native leaf reads every current tp_dict entry and MRO directly;
    # it stores no result and invokes no descriptor, hash, equality or getter.
    return _META_OK and _NATIVE_CLASSES(_META_CONFIG, _CLASS_CONFIG)


def _qualified(graph, *, _frontier=None):
    if (not _SOURCE_OK or native is not _NATIVE or type(native) is not ModuleType
            or _State is not _STATE_CLASS
            or type.__getattribute__(_State, '__mro__') is not _STATE_MRO
            or not _same_items(type.__getattribute__(_State, '__dict__'), _STATE_ITEMS)
            or _State.__init__.__code__ is not _STATE_INIT_CODE
            or any(vars(native).get(name) is not value for name, value in _NATIVE_ENTRIES)
            or any(vars(builtins).get(name) is not value for name, value in _BUILTINS)
            or type(graph) is not r._ColdGraphRead
            or not _fixed_classes()
            or any(vars(owner).get(name) is not value for owner, name, value in _ALIASES)
            or any(fn.__code__ is not code or fn.__defaults__ is not defaults
                or fn.__kwdefaults__ is not kwdefaults
                or (kwdefaults is not None and (type(kwdefaults) is not dict
                    or not _same_items(kwdefaults, items)))
                for fn, code, defaults, kwdefaults, items in _CODE)
            or copyreg.dispatch_table is not _DISPATCH
            or not _same_items(_DISPATCH, _DISPATCH_ITEMS)
            or copyreg._extension_registry is not _EXTENSIONS
            or not _same_items(_EXTENSIONS, _EXTENSION_ITEMS)
            or r.hashlib.sha256 is not _SHA
            or any(getattr(_MARKER, name) is not value for name, value in _MARKER_NAMES)
            or _MARKER.__name__ in ('__newobj__', '__newobj_ex__')
            or sys.modules.get(_MARKER.__module__) is not r
            or vars(r).get(_MARKER.__qualname__) is not _MARKER
            or type(r) is not ModuleType
            or r._row_native_code._trial_typed_storage is not typed._trial_typed_storage
):
        return False
    fields = object.__getattribute__(graph, '__dict__')
    return (not any(name in fields for name in ('input_bytes', 'input_key', '_frontier_input_key'))
        and type(fields.get('phase')) is str and fields['phase'] in ('pre', 'post')
        and type(fields.get('key')) is str and type(fields.get('epoch')) is int and fields.get('_accounted_frontier') is _frontier
        and fields.get('_typed_native_candidate') is None and fields.get('active') is True)


class _State:
    __slots__ = ('scope', 'count', 'capsule', 'declined')

    def __init__(self, scope):
        self.scope, self.count, self.capsule, self.declined = scope, 0, None, False


_STATE_CLASS = _State
_STATE_MRO = type.__getattribute__(_State, '__mro__')
_STATE_ITEMS = tuple(vars(_State).items())
_STATE_INIT_CODE = _State.__init__.__code__


def select(graph):
    """True/False from complete current content, or None for original-frame SHA."""
    fields = object.__getattribute__(graph, '__dict__')
    if not _qualified(graph):
        fields.pop('_structure_state', None)
        return None
    scope = (graph, graph.nonce, graph.key, graph.epoch, graph.phase)
    state = fields.get('_structure_state')
    if (type(state) is not _State or any(a is not b
            for a, b in zip(state.scope, scope, strict=True))):
        state = _State(scope)
        fields['_structure_state'] = state
    if state.declined:
        return None
    if state.capsule is not None:
        current = graph.input_bytes(_snapshot_values=True)
        result = _NATIVE_MATCH(state.capsule, current, scope)
        if result is True:
            return True
        fields.pop('_structure_state', None)
        return None
    # This is only a frequency hint. Every pending call executes its full SHA
    # in the original Graph.check frame; no prior content/PASS is remembered.
    state.count += 1
    # First-producer Source facts deliberately add roots at their original
    # output boundaries. Delaying calibration repeats the complete SHA for
    # the first three reads of every such root. Build the same fully checked
    # snapshot immediately for this path; every later read still walks all
    # current mutable content and Graph.check runs its dynamic gates afresh.
    source_facts = fields.get('_source_fact_bindings')
    if state.count < (1 if type(source_facts) is dict and source_facts else 4):
        return None
    if graph.input_key() != graph.key:
        return False
    values = graph.input_bytes(_snapshot_values=True)
    capsule = _NATIVE_SNAPSHOT(values, *_ARGS, scope, r._SOURCE_VIEW_TYPE, r._SOURCE_OWNER_TYPE)
    if graph.input_key() != graph.key:
        return False
    if capsule is _UNSUPPORTED:
        state.declined = True
        return None
    # Re-project the CURRENT contract as well as mutable graph inputs. This
    # immediate independent comparison closes calibration ABA, not merely two
    # identical before/after SHA values around capture.
    current = graph.input_bytes(_snapshot_values=True)
    if _NATIVE_MATCH(capsule, current, scope) is not True:
        fields.pop('_structure_state', None)
        return None
    state.capsule = capsule
    return True


_FRONTIER = accounted._Frontier


def _frontier_plain(frontier, graph):
    fields = object.__getattribute__(frontier, '__dict__')
    if (any(name in fields for name in ('values', 'key', '_refresh', 'check'))
            or fields.get('graph') is not graph or type(fields.get('expected')) is not str
            or graph.phase != 'pre'
            or type(object.__getattribute__(fields['mode'], '__dict__').get('active')) is not bool):
        return False
    for value in (graph.inputs, *(fields.get(name) for name in (
            'projected', 'replacement', 'gen_replacement', 'raw', 'tokens'))):
        if type(value) is not dict or not all(type(key) is str for key in value):
            return False
    for name in ('complete', 'generation'):
        value = fields.get(name)
        if value is not None and (type(value) is not dict
                or not all(type(key) is str for key in value)):
            return False
    return True


def _frontier_values(frontier, graph):
    # Run the ORIGINAL full current refresh before each independent walk.
    return graph.input_bytes(_frontier_inputs=frontier.values(), _snapshot_values=True)


def select_frontier(frontier):
    """Original projected-content comparison; no owned-family/authority verdict."""
    if type(frontier) is not _FRONTIER:
        return None
    fields = object.__getattribute__(frontier, '__dict__')
    graph = fields.get('graph')
    if not _qualified(graph, _frontier=frontier) or not _frontier_plain(frontier, graph):
        fields.pop('_structure_state', None)
        return None
    scope = (frontier, graph.nonce, frontier.expected, graph.epoch, graph.phase)
    state = fields.get('_structure_state')
    if (type(state) is not _State or any(a is not b
            for a, b in zip(state.scope, scope, strict=True))):
        state = _State(scope)
        fields['_structure_state'] = state
    if state.declined:
        return None
    if state.capsule is not None:
        current = _frontier_values(frontier, graph)
        if _NATIVE_MATCH(state.capsule, current, scope) is True:
            return True
        fields.pop('_structure_state', None)
        return None
    state.count += 1
    if state.count < 4:
        return None
    if frontier.key() != frontier.expected:
        return False
    values = _frontier_values(frontier, graph)
    capsule = _NATIVE_SNAPSHOT(values, *_ARGS, scope, r._SOURCE_VIEW_TYPE, r._SOURCE_OWNER_TYPE)
    if frontier.key() != frontier.expected:
        return False
    if capsule is _UNSUPPORTED:
        state.declined = True
        return None
    if _NATIVE_MATCH(capsule, _frontier_values(frontier, graph), scope) is not True:
        fields.pop('_structure_state', None)
        return None
    state.capsule = capsule
    return True

"""Complete immutable V2 expectations for one Graph or projected frontier.

Current projection remains current. A Version stores the actual original bytes
at publication; neither a selector miss nor an export can republish live data.
No authorization, Graph PASS or transaction is transferred between scopes.
"""
from builtins import object, type, tuple, vars, bool, getattr, bytes, all, hasattr, dict
import hashlib
import sys
from pathlib import Path
from .errors import DomainError
from . import _cold_source_packet as source
_SOURCE_CHECK=source.CHECK

try:
    from . import _cold_graph_structure as native
except ImportError:
    native = None

_MODULE = native
_NAMES = ('PinJournal','PinVersion','register_pin_code','pin_create','pin_publish',
    'pin_current','pin_matches','pin_close','pin_registered','pin_revoke','pin_read_scope','pin_owned_frontier','pin_resolve',
    'register_structure_config','qualify_metadata')
_ENTRIES = (() if native is None or not all(hasattr(native,n) for n in _NAMES)
    else tuple((n,getattr(native,n)) for n in _NAMES))
AVAILABLE = bool(_ENTRIES) and native.SOURCE_SHA256 == hashlib.sha256(
    Path(__file__).with_name('_cold_graph_structure.c').read_bytes()).hexdigest()
JOURNAL = None if not AVAILABLE else native.PinJournal
VERSION = None if not AVAILABLE else native.PinVersion
REVOKE = None if not AVAILABLE else native.pin_revoke
LOOKUP = None if not AVAILABLE else native.pin_registered
OWNED = None if not AVAILABLE else native.pin_owned_frontier
RESOLVE = None if not AVAILABLE else native.pin_resolve
_SHA = hashlib.sha256
_REGISTERED = False


def require(value):
    if not value:raise DomainError('VERSION_CONFLICT','Complete Graph publication changed')


def register(graph_type, frontier_type):
    global _REGISTERED
    if not AVAILABLE:return
    require(not _REGISTERED)
    native.register_pin_code(create,publish,
        (graph_type.__init__,frontier_type.__init__),
        (graph_type.__init__,graph_type.add,frontier_type.__init__,frontier_type.added),
        graph_type,frontier_type,source.native.verify_code if source.native is not None else None,
        (sys.modules[__name__],source,hashlib,native,source.native))
    _REGISTERED=True


def _scope(subject):
    try:return native.pin_read_scope(subject)
    except ValueError:raise DomainError('VERSION_CONFLICT','Exact Graph publication roots required') from None


def _code():
    fn,code,defaults=_SOURCE_CHECK
    require(source.current is fn and fn.__code__ is code and fn.__defaults__ is defaults)
    fn()
    require(AVAILABLE and _REGISTERED and native is _MODULE
        and all(vars(native).get(name) is value for name,value in _ENTRIES)
        and hashlib.sha256 is _SHA)


def create(subject):
    from .natural_spec_runtime import _SOURCE_VIEW_TYPE
    if not AVAILABLE or _SOURCE_VIEW_TYPE is None:return None
    _code()
    from ._cold_graph_structure_guard import _qualified
    scope=_scope(subject)
    graph=scope[1]
    if subject is graph:
        if not _qualified(graph):return None  # Original codec route, before issue.
    else:
        if native.pin_registered(graph) is None:return None
        require(_qualified(graph))
    fields=vars(subject);require(type(fields) is dict)
    require('_pin_journal' not in fields)
    return native.pin_create(scope)


def publish(subject, raw, *, predecessor, frontier=False):
    """Only original init/add entry frames may advance a publication."""
    _code()
    scope=_scope(subject)
    journal=native.pin_registered(subject)
    fields=vars(subject);require(type(fields) is dict)
    require(journal is not None and fields.get('_pin_journal') is journal)
    require(type(journal) is JOURNAL and type(raw) is bytes and type(frontier) is bool)
    key=(_SHA(b'SIM2ACT_NATIVE_ACCOUNTED_FRONTIER_V1\x00'+raw).hexdigest()
        if frontier else _SHA(raw).hexdigest())
    try:return native.pin_publish(journal,raw,key,scope,predecessor)
    except ValueError:raise DomainError('VERSION_CONFLICT','Graph publication scope changed') from None


def current(subject):
    _resolve = "sim2act:pin-resolve-const.v1"
    if _resolve is None:return None  # Capability fixed before Graph creation.
    try:return _resolve(subject)
    except ValueError:raise DomainError('VERSION_CONFLICT','Graph publication version changed') from None


def matches(subject, raw, version=None):
    actual=current(subject)
    require(actual is not None and (version is None or version is actual))
    result=native.pin_matches(actual,raw)
    require(current(subject) is actual)
    return result


def close(subject):
    _revoke = "sim2act:pin-revoke-const.v1"
    if _revoke is not None:_revoke(subject)


def seal_entries(function):
    """Bootstrap fixed native entries into immutable code constants.

    Cleanup/entry callables are not parameters, defaults or mutable module
    lookups during failure handling. Source code witnesses capture this code.
    """
    markers={'sim2act:pin-revoke-const.v1':REVOKE,
        'sim2act:pin-lookup-const.v1':LOOKUP,
        'sim2act:pin-owned-cleanup-const.v1':OWNED,
        'sim2act:pin-resolve-const.v1':RESOLVE}
    constants=function.__code__.co_consts
    function.__code__=function.__code__.replace(co_consts=tuple(
        markers.get(value,value) if type(value) is str else value for value in constants))


seal_entries(current)
seal_entries(close)

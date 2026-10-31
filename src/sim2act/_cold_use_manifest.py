"""First-producer per-use manifest ownership; never a permission or PASS.

An explicit immutable envelope keeps the model-storage view and the ORIGINAL
dump view together. It is not an AppManifest and never impersonates one.
"""
from . import _cold_source_packet as owned
from . import natural_specs as natural
from .contracts import AppManifest
from .errors import DomainError
import sys

TAG = 'sim2act:owned-per-use-manifest.v1'
SCHEMA = 'sim2act.contracts.AppManifest'
_COMPILE = natural.compile_candidate
_COMPILE_STATE = (_COMPILE.__code__, _COMPILE.__defaults__, _COMPILE.__kwdefaults__)
_TYPE, _LEN, _ALL, _DICT, _TUPLE, _STR, _VARS = type, len, all, dict, tuple, str, vars
_PROFILE, _TRACE = sys.getprofile, sys.gettrace
_BASE_EXCEPTION = BaseException


def _predicate():
    kind,size,sequence,text=type,len,tuple,str
    def is_manifest(value):
        return (kind(value) is sequence and size(value)==4 and kind(value[0]) is text
            and value[0]=='sim2act:owned-per-use-manifest.v1')
    return is_manifest


is_manifest=_predicate()


def _guarded(operation):
    kind,error=type,BaseException
    def checked(graph,*args,**kwargs):
        try:
            return operation(graph,*args,**kwargs)
        except error:
            from .natural_spec_runtime import _ColdGraphRead
            if kind(graph) is _ColdGraphRead:
                _ColdGraphRead.invalidate(graph)
            raise
    return checked


def compiler(guard):
    """Before the original call; unknown paths keep the complete old family."""
    if guard is None or not owned.available():
        return None
    owned.current()
    if guard._accounted_frontier is not None or _PROFILE() is not None or _TRACE() is not None:
        return None
    if (natural.compile_candidate is not _COMPILE or _COMPILE.__code__ is not _COMPILE_STATE[0]
            or _COMPILE.__defaults__ is not _COMPILE_STATE[1]
            or _COMPILE.__kwdefaults__ is not _COMPILE_STATE[2]):
        return None
    from ._cold_policy_segment import _fixed_schema
    if not _ALL(_fixed_schema(kind) for kind in owned.image.model_classes()):
        return None
    return _COMPILE


def _current(graph,value,*,key=None):
    """Fresh exact registry/scope/schema/ref join, not a saved validity answer."""
    from .natural_spec_runtime import _ColdGraphRead
    owned.current()
    owned.require(_TYPE(graph) is _ColdGraphRead and is_manifest(value) and _TYPE(value[1]) is _STR
        and (key is None or value[1]==key))
    owned.require(graph.active is True and value[1] in graph.inputs)
    pair=owned.fact(graph,value[1])
    owned.require(owned.image.is_kind(pair,'q') and _LEN(pair)==2
        and owned.image.is_kind(value[2],'m') and owned.image.is_kind(value[3],'d')
        and owned.image.same(pair[0],value[2]) and owned.image.same(pair[1],value[3]))
    tag,storage=value[2].node()
    owned.require(tag=='m' and value[2].read(storage[0])==SCHEMA
        and _DICT(value[2].data()[7]).get(value[2].ref())==5)
    return value[2]


current=_guarded(_current)


def dump(graph,value,*,key=None):
    current(graph,value,key=key)
    return value[3]


def _fallback(graph,key,model,scope):
    """A refusal is safe only before any output escaped in this same scope."""
    owned.current();owned._scope_current(graph,scope)
    registry=_VARS(graph).get('_source_fact_bindings',{})
    owned.require(graph.active is True and key not in graph.inputs
        and _TYPE(registry) is _DICT and key not in registry)
    graph.check(graph.store,graph.connection)
    owned._scope_current(graph,scope)
    owned.require(graph.active is True and key not in graph.inputs
        and key not in _VARS(graph).get('_source_fact_bindings',{}))
    return model


def _publish(graph,key,model,selected):
    """Only a locally captured qualified compiler may publish its fresh model."""
    from .natural_spec_runtime import _ColdGraphRead
    from . import natural_live_admission as gate
    owned.current()
    owned.require(_TYPE(graph) is _ColdGraphRead and _TYPE(key) is _STR
        and key not in graph.inputs and _TYPE(model) is AppManifest and selected is _COMPILE)
    graph.check(graph.store,graph.connection)
    owned.current()
    if compiler(graph) is not selected:
        raise DomainError('VERSION_CONFLICT','Per-use manifest compiler changed after output')
    raw=AppManifest.model_dump(model)
    gate._trial_typed_values([(AppManifest,model,raw)])
    graph.check(graph.store,graph.connection)
    scope=owned._scope(graph)
    outside=graph.input_bytes(_snapshot_values=True)
    try:
        parents=[]
        data,anchors=owned.image.capture((model,raw),outside,_parents=parents,_manifest=True)
    except (owned.image.Bounds,owned.image.Unsupported):
        return _fallback(graph,key,model,scope)
    owner=owned.native.make_composite(data,_TUPLE(parents))
    if owner is owned.native.UNSUPPORTED:
        return _fallback(graph,key,model,scope)
    owned.require(_TYPE(owner) is owned.native.Owned)
    graph.check(graph.store,graph.connection);owned.current();owned._scope_current(graph,scope)
    owned.require(owned.native.match_live(owner,(model,raw),anchors,owned._config(graph,_manifest=True),outside))
    packet=owned.native.make_binding(owner,graph.nonce,graph.epoch,graph.phase,anchors,scope)
    owned.require(_TYPE(packet) is owned._BINDING)
    pair=owned.native.read_owner(owner)
    value=(TAG,key,pair[0],pair[1])
    try:
        owned._scope_current(graph,scope)
        _ColdGraphRead.add(graph,key,(owned.FACT_TAG,owned.native.binding_pin(packet)))
        _VARS(graph).setdefault('_source_fact_bindings',{})[key]=(packet,pair)
        _ColdGraphRead.check(graph,graph.store,graph.connection)
        current(graph,value,key=key)
        return value
    except _BASE_EXCEPTION:
        _ColdGraphRead.invalidate(graph)
        raise


publish=_guarded(_publish)

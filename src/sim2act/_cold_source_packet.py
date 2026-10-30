"""Complete post Source ownership, never permission or a cached PASS.

The owner contains immutable facts only. Its separately scoped native binding
pins every original leaf and all shared outside anchors into the original graph.
"""
from pathlib import Path
import hashlib
from types import FunctionType, BuiltinFunctionType
from .errors import DomainError
from . import _cold_source_image as image

try:
    from . import _cold_source_owned_impl as native
except ImportError:
    native = None

KEY = 'cold-trial:accounted-source'
_MODULE = native
_FILES = ('_cold_source_owned_impl.c','_cold_source_live_match.h','_cold_source_code.h','_cold_source_view.h','_cold_source_shape.h')
_SOURCE_OK = native is not None and native.SOURCE_SHA256 == hashlib.sha256(
    b''.join(Path(__file__).with_name(name).read_bytes() for name in _FILES)).hexdigest()
_ENTRIES = (() if not _SOURCE_OK else tuple((name,getattr(native,name)) for name in
    ('Owned','Binding','View','read_owner','UNSUPPORTED','make_owned','owned_data','owned_pin','make_binding',
     'binding_owner','binding_current','binding_pin','match_live','match_node','match_nodes','register_code','verify_code')))
_BINDING = None if not _SOURCE_OK else native.Binding
if _SOURCE_OK:image.View=native.View


def require(value):
    if not value:raise DomainError('VERSION_CONFLICT','Complete owned Source changed')


def _witness(namespace,names):
    return (namespace,tuple((name,namespace[name],namespace[name].__code__,
        namespace[name].__defaults__,namespace[name].__kwdefaults__,
        tuple((namespace[name].__kwdefaults__ or {}).items())) for name in names))


def _class(cls):
    return (cls,type(cls),cls.__mro__,tuple(vars(cls).items()),
        _witness(vars(cls),tuple(name for name,value in vars(cls).items() if type(value) is FunctionType))[1])


def register(index, namespace, names, classes=(), constants=()):
    # Only import-time code metadata enters this one-time native registry.
    if _SOURCE_OK:
        native.register_code(index,((_witness(namespace,names),),tuple(_class(c) for c in classes),
            ((namespace,tuple((name,namespace[name]) for name in constants)),)))


class Capacity(ValueError):
    """Only before any Source edge escapes: run all original legacy checks."""


def available():
    return _SOURCE_OK


def current(_verify=None if not _SOURCE_OK else native.verify_code):
    # The immutable native callable is an import-time default, independent of
    # mutable require/module aliases. A changed qualifier cannot ignore False.
    if (_verify is None or _verify() is not True or native is not _MODULE or not _SOURCE_OK
            or any(vars(native).get(name) is not value for name,value in _ENTRIES)):
        raise DomainError('VERSION_CONFLICT','Complete Source code changed')


def is_packet(value):
    return _BINDING is not None and type(value) is _BINDING


def _scope(graph):
    return (graph.inputs,graph.role_limits,graph.binding,graph.connection,graph.transaction,graph.scope)


def _scope_current(graph,scope):
    if any(a is not b for a,b in zip(scope,_scope(graph),strict=True)):
        raise DomainError('VERSION_CONFLICT','Source publication roots were rebound')


def bound(graph,value=None):
    current()
    packet=vars(graph).get('_source_owned_binding')
    require(type(packet) is _BINDING and (value is None or value is packet)
        and graph.active and graph.phase=='post' and graph._accounted_frontier is None
        and native.binding_current(packet,native.binding_owner(packet),graph.nonce,graph.epoch,graph.phase,_scope(graph))
        and graph.inputs.get(KEY) is native.binding_pin(packet))
    return packet


def pin(graph,value):
    return native.binding_pin(bound(graph,value))


def facts(graph,value):
    packet=bound(graph,value)
    return native.read_owner(native.binding_owner(packet))[0]


def raw_fields(graph,expected_pin):
    packet=bound(graph)
    require(expected_pin is native.binding_pin(packet))
    return native.read_owner(native.binding_owner(packet))[1]


def _config(graph):
    from . import natural_spec_runtime as rt, natural_live_admission as gate
    from . import _cold_graph_structure_guard as structure, _cold_policy_segment as schema
    from . import production_trial_policy as policy, production_trial_sender as sender
    from .natural_source_archives import BodyArchive
    require(structure._qualified(graph))
    models=(policy.Slot,policy.ReservationIdentity,policy.Outcome,sender.Capture,BodyArchive)
    require(all(schema._fixed_schema(cls) for cls in models))
    def descriptor(cls,name):
        return next(vars(base)[name] for base in cls.__mro__ if name in vars(base))
    model_config=tuple((cls,cls.__module__+'.'+cls.__qualname__,
        *(descriptor(cls,name) for name in ('__dict__','__pydantic_fields_set__',
             '__pydantic_extra__','__pydantic_private__'))) for cls in models)
    limit_names=next(v for v in rt._cold_graph_limit_values.__code__.co_consts if type(v) is tuple
        and v==('max_requests','max_tools','max_repairs','max_total_tokens','max_output_tokens','run_seconds'))
    return (model_config,rt._ColdGraphRowMapping,
        tuple(descriptor(rt._ColdGraphRowMapping,k) for k in ('_parent','_data','_key_to_index')),
        tuple((cls,descriptor(cls,'_keys')) for cls in (rt._ColdGraphCursorMeta,rt._ColdGraphSimpleMeta)),
        rt._ColdGraphQuotedName,(rt.Limits,descriptor(rt.Limits,'__dict__'),limit_names))


def publish(graph,value,raw,guard):
    """Original producer complete first; never publish a legacy mutable family."""
    from .natural_spec_runtime import _ColdGraphRead
    require(type(graph) is _ColdGraphRead and graph.phase=='post' and KEY not in graph.inputs
        and vars(graph).get('_source_owned_binding') is None)
    current();scope=_scope(graph);config=_config(graph)
    _scope_current(graph,scope)
    outside=graph.input_bytes(_snapshot_values=True)
    try:
        data,anchors=image.capture((value,raw),outside)
    except (image.Bounds,image.Unsupported):
        # Nothing was published. The caller retains the entire legacy route.
        raise Capacity('Source prepublication capacity or representation') from None
    owner=native.make_owned(data)
    if owner is native.UNSUPPORTED:
        raise Capacity('Source native representation capacity')
    require(type(owner) is native.Owned)
    guard();current();_scope_current(graph,scope)
    # This bounded C interval observes full current storage and the complete
    # outside alias boundary without Python callbacks or automatic GC.
    require(native.match_live(owner,(value,raw),anchors,config,outside))
    packet=native.make_binding(owner,graph.nonce,graph.epoch,graph.phase,anchors,scope)
    require(type(packet) is _BINDING)
    _scope_current(graph,scope)
    try:
        _ColdGraphRead.add(graph,KEY,native.binding_pin(packet))
        vars(graph)['_source_owned_binding']=packet
        _ColdGraphRead.check(graph,graph.store,graph.connection)
        bound(graph,packet)
        _scope_current(graph,scope)
        return packet
    except BaseException:
        _ColdGraphRead.invalidate(graph)
        raise


def usage(parsed):
    """Same normalize_usage value semantics, reading only the owned image."""
    value=parsed.get('usage') if type(parsed) is image.View and parsed.node()[0]=='d' else None
    known={k:value[k] for k in ('prompt_tokens','completion_tokens','total_tokens')
        if type(value) is image.View and value.node()[0]=='d' and type(value.get(k)) is int and value[k]>=0}
    complete=len(known)==3 and known['total_tokens']==known['prompt_tokens']+known['completion_tokens']
    return dict(status='known' if complete else 'partial' if known else 'unknown',tokens=known or None)


def stage_usage(graph,packet,guard):
    root=facts(graph,packet)
    run,actual,chains,reads=root
    require(len(actual)==len(chains)==len(reads)==2)
    for slot,capture,parsed,checked,wire,payload in chains:
        normal=usage(parsed);guard();current()
        require(any(image.business_equal(checked,a) for a in actual)
            and checked['status']=='VERIFIED' and image.business_equal(checked['usage'],normal)
            and normal['status']=='known' and slot.settlement is not None
            and all(getattr(slot.settlement,k)==normal['tokens'].get(k)
                for k in ('prompt_tokens','completion_tokens','total_tokens')))


def slot_join(graph,packet,state,owned_slot,aid,guard):
    """Fresh full current Ledger Slot/Identity/Outcome join, never ID-only."""
    from . import natural_live_admission as gate, production_trial_policy as policy
    bound(graph,packet)
    require(type(state) is policy.Ledger)
    matches=tuple(slot for slot in state.slots if slot.identity.attempt_id==aid)
    require(len(matches)==1 and type(matches[0]) is policy.Slot
        and matches[0].identity.stage=='source' and type(owned_slot) is image.View
        and owned_slot.node()[0]=='m' and dict(owned_slot.data()[7]).get(owned_slot.ref())==0)
    current_slot=matches[0]
    config=_config(graph)
    original_slots=object.__getattribute__(state,'__dict__')['slots']
    roots=[]
    for chain in facts(graph,packet)[2]:
        expected=chain[0]
        candidates=tuple(slot for slot in original_slots
            if type(slot) is policy.Slot
            and object.__getattribute__(slot,'__dict__')['identity'].attempt_id==expected.identity.attempt_id)
        require(len(candidates)==1)
        roots.append((expected.ref(),candidates[0]))
    roots=tuple(roots)
    owner=native.binding_owner(bound(graph,packet))
    guard();current()
    require(object.__getattribute__(state,'__dict__')['slots'] is original_slots
        and native.match_nodes(owner,roots,config))
    # All source slots share one native comparison memo. Cross-slot field-set
    # and nested-container aliases cannot split/merge through per-slot checks.
    guard();current()
    require(object.__getattribute__(state,'__dict__')['slots'] is original_slots
        and native.match_nodes(owner,roots,config))
    return matches[0]


# Source's own functions, view semantics and bounded capture are fixed before
# any runtime callback. Consumer modules register their own completed code at
# import end; every original graph boundary rechecks the full registry in C.
if _SOURCE_OK:
    _own_names=tuple(k for k,v in globals().copy().items() if type(v) is FunctionType and v.__module__==__name__)
    _image_names=tuple(k for k,v in vars(image).items() if type(v) is FunctionType and v.__module__==image.__name__)
    _constants=tuple((k,globals()[k]) for k in ('KEY','native','image','_MODULE','_SOURCE_OK','_ENTRIES','_BINDING'))
    native.register_code(0,((_witness(globals(),_own_names),_witness(vars(image),_image_names)),
        tuple(_class(c) for c in (image.Unsupported,image.Bounds,Capacity)),
        ((globals(),_constants),(vars(native),_ENTRIES),(vars(image),tuple((k,vars(image)[k]) for k in
            ('_PACK','_MAX_NODES','_MAX_EDGES','_MAX_LEAF','View','Unsupported','Bounds','DomainError'))))))
CHECK=(current,current.__code__,current.__defaults__)

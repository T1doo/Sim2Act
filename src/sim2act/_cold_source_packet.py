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
FACT_TAG = 'sim2act:owned-source-fact.v1'
MIXED_FACT_TAG = 'sim2act:owned-source-with-mutable.v1'
_MODULE = native
_FILES = ('_cold_source_owned_impl.c','_cold_source_live_match.h','_cold_source_code.h','_cold_source_view.h','_cold_source_shape.h')
_SOURCE_OK = native is not None and native.SOURCE_SHA256 == hashlib.sha256(
    b''.join(Path(__file__).with_name(name).read_bytes() for name in _FILES)).hexdigest()
_ENTRIES = (() if not _SOURCE_OK else tuple((name,getattr(native,name)) for name in
    ('Owned','Binding','View','read_owner','UNSUPPORTED','make_owned','owned_data','owned_pin','make_binding',
     'binding_owner','binding_current','binding_pin','match_live','match_node','match_nodes','match_ledger','register_code','verify_code','make_composite','view_pin')))
_BINDING = None if not _SOURCE_OK else native.Binding
if _SOURCE_OK:image.View=native.View


def require(value):
    if not value:raise DomainError('VERSION_CONFLICT','Complete owned Source changed')


def _function_state(fn,active=None):
    if active is None:active=set()
    active.add(id(fn))
    closure=fn.__closure__
    cells=[]
    for cell in closure or ():
        value=cell.cell_contents
        child=(_function_state(value,active) if type(value) is FunctionType and id(value) not in active else None)
        cells.append((cell,value,child))
    active.remove(id(fn))
    return (fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,
        tuple((fn.__kwdefaults__ or {}).items()),closure,tuple(cells))


def _witness(namespace,names):
    return (namespace,tuple((name,namespace[name],(_function_state(namespace[name]),)) for name in names))


def _class(cls):
    methods=[]
    for name,value in vars(cls).items():
        functions=((value,) if type(value) is FunctionType else
            (value.__func__,) if type(value) in (classmethod,staticmethod) else
            tuple(v for v in (value.fget,value.fset,value.fdel) if type(v) is FunctionType)
                if type(value) is property else ())
        if functions:methods.append((name,value,tuple(_function_state(fn) for fn in functions)))
    return (cls,type(cls),cls.__mro__,tuple(vars(cls).items()),tuple(methods))


def register(index, namespace, names, classes=(), constants=(), helpers=(), constant_helpers=()):
    # Only import-time code metadata enters this one-time native registry.
    if _SOURCE_OK:
        native.register_code(index,((_witness(namespace,names),*(_witness(space,keys) for space,keys in helpers)),tuple(_class(c) for c in classes),
            ((namespace,tuple((name,namespace[name]) for name in constants)),
             *((space,tuple((name,space[name]) for name in keys)) for space,keys in constant_helpers))))


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
    return (graph,graph.inputs,graph.role_limits,graph.binding,graph.connection,graph.transaction,graph.scope)


def _scope_current(graph,scope):
    if any(a is not b for a,b in zip(scope,_scope(graph),strict=True)):
        raise DomainError('VERSION_CONFLICT','Source publication roots were rebound')


def fact_current(graph):
    """Fresh scoped registry/root identity checks; contains no cached PASS."""
    registry=vars(graph).get('_source_fact_bindings',{})
    require(graph.active and len(graph.scope)==1 and graph.scope[0] is graph.nonce)
    require(type(registry) is dict and type(graph.inputs) is dict)
    require(all(type(name) is str for name in registry))
    marked={name for name,value in graph.inputs.items() if type(value) is tuple
        and len(value) in (2,3) and type(value[0]) is str
        and (len(value)==2 and value[0]=='sim2act:owned-source-fact.v1'
             or len(value)==3 and value[0]=='sim2act:owned-source-with-mutable.v1')}
    require(set(registry)==marked)
    if not marked:return
    current()
    scope=_scope(graph)
    for name,entry in registry.items():
        require(type(name) is str and type(entry) is tuple and len(entry)==2)
        packet,view=entry
        require(type(packet) is _BINDING and type(view) is image.View
            and native.binding_current(packet,native.binding_owner(packet),graph.nonce,graph.epoch,graph.phase,scope)
            and graph.inputs[name][1] is native.binding_pin(packet)
            and image.same(view,native.read_owner(native.binding_owner(packet))))


def fact(graph,name):
    """Read one immutable value, never a whole-graph or authority verdict.

    Original checkpoints still validate the COMPLETE registry and mutable
    graph. A pure data lookup need only bind this requested immutable value
    to the current scope; it must not rescan every other fact as added work.
    """
    registry=vars(graph).get('_source_fact_bindings',{})
    require(type(registry) is dict and type(graph.inputs) is dict and type(name) is str)
    root=graph.inputs[name]
    marked=(type(root) is tuple and len(root) in (2,3) and type(root[0]) is str
        and (len(root)==2 and root[0]=='sim2act:owned-source-fact.v1' or len(root)==3 and root[0]=='sim2act:owned-source-with-mutable.v1'))
    if name not in registry:
        require(not marked)
        return root  # Actual legacy data needs no optional native extension.
    current()
    scope=_scope(graph)
    require(type(graph.inputs) is dict and graph.inputs is scope[1]
        and vars(graph).get('_source_fact_bindings') is registry)
    root=graph.inputs[name]
    marked=(type(root) is tuple and len(root) in (2,3) and type(root[0]) is str
        and (len(root)==2 and root[0]=='sim2act:owned-source-fact.v1' or len(root)==3 and root[0]=='sim2act:owned-source-with-mutable.v1'))
    require(marked and graph.active is True and type(graph.scope) is list
        and len(graph.scope)==1 and graph.scope[0] is graph.nonce)
    entry=registry[name]
    require(type(entry) is tuple and len(entry)==2)
    packet,view=entry
    require(type(packet) is _BINDING and type(view) is image.View
        and native.binding_current(packet,native.binding_owner(packet),graph.nonce,graph.epoch,graph.phase,scope)
        and root[1] is native.binding_pin(packet)
        and image.same(view,native.read_owner(native.binding_owner(packet))))
    _scope_current(graph,scope)
    require(graph.inputs is scope[1] and vars(graph).get('_source_fact_bindings') is registry
        and registry.get(name) is entry and graph.inputs.get(name) is root)
    return view


def fields_ref(graph,name,value):
    """Fresh control-field comparison, then the same immutable parent node."""
    registry=vars(graph).get('_source_fact_bindings',{})
    require(type(registry) is dict and type(graph.inputs) is dict)
    if name not in registry:
        root=graph.inputs.get(name)
        require(not (type(root) is tuple and len(root) in (2,3) and type(root[0]) is str
            and (len(root)==2 and root[0]=='sim2act:owned-source-fact.v1' or len(root)==3 and root[0]=='sim2act:owned-source-with-mutable.v1')))
        return value
    from .natural_spec_runtime import _source_fields_equal
    saved=fact(graph,name)
    require(_source_fields_equal(saved,value))
    return saved


def own_fact(graph,name,value,*,_mutable=None):
    """First-producer transfer, before returning a fact to any consumer.

    Same complete native live comparison and outside alias boundary as the
    accounted Source handoff. Existing mutable boundary anchors stay checked.
    """
    from .natural_spec_runtime import _ColdGraphRead
    require(type(graph) is _ColdGraphRead and graph.active and name not in graph.inputs)
    if type(value) in (str,bytes,int,float,bool,type(None)):
        require(_mutable is None)
        _ColdGraphRead.add(graph,name,value)
        return value
    graph.check(graph.store,graph.connection);current();scope=_scope(graph)
    from .natural_spec_runtime import _cold_graph_validate_inputs
    _cold_graph_validate_inputs(value,_forbid_root=graph.inputs)
    # Validate the original canonical comparison domain once at first output.
    # Subsequent same immutable-node references have exactly that same value.
    from .natural_spec_runtime import _model_inputs
    _model_inputs(value)
    outside=graph.input_bytes(_snapshot_values=True);parents=[]
    if _mutable is not None:
        # The live companion participates in the SAME outside alias domain.
        # A shared mutable descendant must remain an explicit anchor, never
        # silently split into an owned copy and a separately mutable value.
        _cold_graph_validate_inputs(_mutable,_forbid_root=graph.inputs)
        outside=(outside,_mutable)
    data,anchors=image.capture(value,outside,_parents=parents)
    owner=native.make_composite(data,tuple(parents))
    require(type(owner) is native.Owned)
    graph.check(graph.store,graph.connection);current();_scope_current(graph,scope)
    require(native.match_live(owner,value,anchors,_config(graph),outside))
    packet=native.make_binding(owner,graph.nonce,graph.epoch,graph.phase,anchors,scope)
    require(type(packet) is _BINDING)
    view=native.read_owner(owner)
    require(type(view) is image.View)
    try:
        _scope_current(graph,scope)
        # One publication can also retain an original LIVE input alongside
        # the immutable fact. Only value enters the Owner; the mutable input
        # remains in every full graph validation/codec/content comparison.
        pin=native.binding_pin(packet)
        root=(FACT_TAG,pin) if _mutable is None else (MIXED_FACT_TAG,pin,_mutable)
        _ColdGraphRead.add(graph,name,root)
        vars(graph).setdefault('_source_fact_bindings',{})[name]=(packet,view)
        _ColdGraphRead.check(graph,graph.store,graph.connection)
        return view
    except BaseException:
        _ColdGraphRead.invalidate(graph);raise


def bound(graph,value=None,*,stage='source'):
    current()
    require(type(stage) is str and stage in ('source','generate'))
    packet=vars(graph).get('_'+stage+'_owned_binding')
    require(type(packet) is _BINDING and (value is None or value is packet)
        and graph.active and graph.phase=='post' and graph._accounted_frontier is None
        and native.binding_current(packet,native.binding_owner(packet),graph.nonce,graph.epoch,graph.phase,_scope(graph))
        and graph.inputs.get('cold-trial:accounted-'+stage) is native.binding_pin(packet))
    return packet


def pin(graph,value):
    stage='generate' if value is vars(graph).get('_generate_owned_binding') else 'source'
    return native.binding_pin(bound(graph,value,stage=stage))


def facts(graph,value,*,stage='source'):
    packet=bound(graph,value,stage=stage)
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
    require(all(schema._fixed_schema(cls) for cls in (*models,policy.Ledger)))
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
        rt._ColdGraphQuotedName,(rt.Limits,descriptor(rt.Limits,'__dict__'),limit_names),
        (policy.Ledger,descriptor(policy.Ledger,'__dict__')))


def publish(graph,value,raw,guard,*,stage='source'):
    """Original producer complete first; never publish a legacy mutable family."""
    from .natural_spec_runtime import _ColdGraphRead
    require(type(stage) is str and stage in ('source','generate'))
    key='cold-trial:accounted-'+stage
    slot='_'+stage+'_owned_binding'
    require(type(graph) is _ColdGraphRead and graph.phase=='post' and key not in graph.inputs
        and vars(graph).get(slot) is None)
    current();scope=_scope(graph);config=_config(graph)
    # Ownership representation is broader than the original raw domain (for
    # model field sets and hidden row storage). Preserve the entire original
    # facts<->raw and schema/storage gate ONCE, before dropping the old cohort.
    from . import natural_live_admission as gate
    initial_models=[]
    gate._graph_trial_accounted_models_from_raw(initial_models,value,raw)
    gate._trial_typed_values(initial_models)
    guard();current()
    _scope_current(graph,scope)
    outside=graph.input_bytes(_snapshot_values=True)
    try:
        parents=[]
        data,anchors=image.capture((value,raw),outside,_parents=parents)
    except (image.Bounds,image.Unsupported):
        # Nothing was published. The caller retains the entire legacy route.
        raise Capacity('Source prepublication capacity or representation') from None
    owner=native.make_composite(data,tuple(parents))
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
        _ColdGraphRead.add(graph,key,native.binding_pin(packet))
        vars(graph)[slot]=packet
        _ColdGraphRead.check(graph,graph.store,graph.connection)
        bound(graph,packet,stage=stage)
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


def stage_usage(graph,packet,guard,*,stage='source'):
    require(type(stage) is str and stage in ('source','generate'))
    bound(graph,packet,stage=stage)
    root=facts(graph,packet,stage=stage)
    run,actual,chains,reads=root
    require(len(actual)==len(chains)==(3 if stage=='generate' else 2)
        and len(reads)==(0 if stage=='generate' else 2))
    for slot,capture,parsed,checked,wire,payload in chains:
        normal=usage(parsed);guard();current()
        require(any(image.business_equal(checked,a) for a in actual)
            and checked['status']==('RECEIVED' if stage=='generate' else 'VERIFIED') and image.business_equal(checked['usage'],normal)
            and normal['status']=='known' and slot.settlement is not None
            and all(getattr(slot.settlement,k)==normal['tokens'].get(k)
                for k in ('prompt_tokens','completion_tokens','total_tokens')))
        if stage=='generate':
            # Original _trial_result(_stage_usage_from_facts(...), guard)
            # kept a second fresh dynamic/typed/content boundary after each
            # complete row/settlement comparison. Ownership does not remove it.
            guard();current()


def slot_join(graph,packet,state,owned_slot,aid,guard):
    """Fresh full current Ledger Slot/Identity/Outcome join, never ID-only."""
    from . import natural_live_admission as gate, production_trial_policy as policy
    bound(graph,packet)
    require(type(state) is policy.Ledger)
    require(type(owned_slot) is image.View
        and owned_slot.node()[0]=='m' and dict(owned_slot.data()[7]).get(owned_slot.ref())==0
        and owned_slot.data() is native.owned_data(native.binding_owner(packet))
        and owned_slot.identity.attempt_id==aid)
    config=_config(graph)
    refs=tuple(chain[0].ref() for chain in facts(graph,packet)[2])
    owner=native.binding_owner(bound(graph,packet))
    guard();current()
    require(native.match_ledger(owner,refs,state,config))
    # Original post-callback dynamic/typed checks remain. C then reselects from
    # the actual Ledger and compares all source slots with one alias memo.
    guard();current()
    require(native.match_ledger(owner,refs,state,config))
    return None


# Source's own functions, view semantics and bounded capture are fixed before
# any runtime callback. Consumer modules register their own completed code at
# import end; every original graph boundary rechecks the full registry in C.
if _SOURCE_OK:
    _own_names=tuple(k for k,v in globals().copy().items() if type(v) is FunctionType and v.__module__==__name__)
    _image_names=tuple(k for k,v in vars(image).items() if type(v) is FunctionType and v.__module__==image.__name__)
    _constants=tuple((k,globals()[k]) for k in ('KEY','FACT_TAG','MIXED_FACT_TAG','native','image','_MODULE','_SOURCE_OK','_ENTRIES','_BINDING'))
    native.register_code(0,((_witness(globals(),_own_names),_witness(vars(image),_image_names)),
        tuple(_class(c) for c in (image.Unsupported,image.Bounds,Capacity)),
        ((globals(),_constants),(vars(native),_ENTRIES),(vars(image),tuple((k,vars(image)[k]) for k in
            ('_PACK','_MAX_NODES','_MAX_EDGES','_MAX_LEAF','View','Unsupported','Bounds','DomainError'))))))
CHECK=(current,current.__code__,current.__defaults__)

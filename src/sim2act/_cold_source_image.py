"""Immutable complete Source data; never dispatch authority.

One joint identity memo covers incoming actual+raw facts and outside graph data.
Only the incoming reachable immutable image is encoded. Shared mutable nodes
remain explicit outside anchors, never an untracked copy or permission cache.
"""
import struct
from sim2act.errors import DomainError

class Unsupported(ValueError):pass
class Bounds(ValueError):pass
_PACK=struct.Struct('!d').pack
_MAX_NODES=100000
_MAX_EDGES=1000000
_MAX_LEAF=16*1024*1024


def capture(incoming, outside):
    from sim2act import natural_spec_runtime as rt, natural_live_admission as gate
    from sim2act import production_trial_policy as policy, production_trial_sender as sender
    from sim2act.natural_source_archives import BodyArchive
    from sim2act._cold_typed_stream import _Comparison
    from sqlalchemy.engine import RowMapping
    from sqlalchemy.sql.elements import quoted_name
    from sim2act.contracts import Limits
    models=(policy.Slot,policy.ReservationIdentity,policy.Outcome,sender.Capture,BodyArchive)
    nodes=[];origins=[];memo={};held=[];active=set();synthetic=[];leaves=[];kinds=[]
    work=size=0
    virtual_leaves=set();real_leaves=set();virtual_ids=set();virtual_containers=set()
    def visit(value,depth=0,mode='source',synthetic_leaf=False):
        nonlocal work,size
        work+=1
        if work>_MAX_EDGES or depth>64 or len(nodes)>=_MAX_NODES:raise Bounds('capture')
        kind=type(value);ident=id(value)
        tag=('n' if value is None else 't' if value is True else 'f' if value is False else
            'i' if kind is int else 'v' if kind is float else 's' if kind is str else
            'b' if kind is bytes else 'd' if kind is dict else 'l' if kind is list else
            'q' if kind is tuple else 'r' if kind is RowMapping else 'u' if kind is quoted_name else
            'e' if kind is set and mode=='source' else 'm' if mode=='source' and any(kind is cls for cls in models) else
            'c' if kind is Limits and mode=='outside' else None)
        if tag is None:raise Unsupported('unsupported kind')
        if ident in active:raise Unsupported('cycle')
        scalar=tag in ('n','t','f','i','v')
        if not scalar and ident in memo:
            ref=memo[ident]
            if tag in ('s','b'):(virtual_leaves if synthetic_leaf else real_leaves).add(ref)
            if nodes[ref][0]!=tag:raise Unsupported('typed/raw interpretation conflict')
            return ref
        ref=len(nodes);nodes.append(None);origins.append(value);kinds.append(tag)
        if not scalar:memo[ident]=ref;held.append(value)
        active.add(ident)
        def child(v,virtual=False):return visit(v,depth+1,mode,virtual)
        if tag in ('s','b'):
            (virtual_leaves if synthetic_leaf else real_leaves).add(ref)
            size+=len(value)*(4 if tag=='s' else 1)
            if size>_MAX_LEAF:raise Bounds('leaf bytes')
            payload=len(leaves);leaves.append(value);edges=()
        elif tag=='i':
            if not -(1<<63)<=value<(1<<63):raise Unsupported('integer range')
            payload=value;edges=()
        elif tag=='v':payload=_PACK(value);edges=()
        elif tag in ('n','t','f'):payload=None;edges=()
        elif tag=='d':
            if not all(type(k) is str or type(k) is quoted_name for k in value):raise Unsupported('dict keys')
            payload=tuple((child(k,id(value) in virtual_containers and id(k) in virtual_ids),child(v)) for k,v in dict.items(value));edges=tuple(x for p in payload for x in p)
        elif tag in ('q','l'):
            payload=tuple(child(v) for v in value);edges=payload
        elif tag=='e':
            if not all(type(v) is str for v in value):raise Unsupported('only model field-name set')
            payload=tuple(child(v) for v in sorted(value));edges=payload
        elif tag=='r':
            storage=rt._cold_graph_row_storage(value);synthetic.append(storage)
            virtual_containers.add(id(storage[2]))
            rawindex=object.__getattribute__(value,'_key_to_index')
            originals={id(k) for k in (*storage[0],*tuple(rawindex)) if type(k) is str}
            virtual_ids.update(id(k) for k in storage[2] if id(k) not in originals)
            payload=tuple(child(v) for v in storage);edges=payload
        elif tag=='u':
            # Exactly the original graph's quoted-name reducer representation.
            text=str.__str__(value);synthetic.append(text)
            payload=child(text,True);edges=(payload,)
        elif tag=='c':
            storage=rt._cold_graph_limit_values(value);synthetic.append(storage)
            payload=child(storage);edges=(payload,)
        else:
            _Comparison(gate._trial_typed_nested_classes()).validate_model(value)
            raw=object.__getattribute__(value,'__dict__')
            selected=object.__getattribute__(value,'__pydantic_fields_set__')
            extra=object.__getattribute__(value,'__pydantic_extra__')
            private=object.__getattribute__(value,'__pydantic_private__')
            if type(raw) is not dict or type(selected) is not set or extra is not None or private is not None:raise Unsupported('model storage')
            schema=kind.__module__+'.'+kind.__qualname__;synthetic.append(schema)
            payload=(child(schema,True),child(raw),child(selected),child(extra),child(private));edges=payload
        nodes[ref]=(tag,payload,edges);active.remove(ident)
        return ref
    root=visit(incoming)
    outroot=visit(outside,mode='outside')
    def reachable(start):
        seen=set();todo=[start]
        while todo:
            ref=todo.pop()
            if ref in seen:continue
            seen.add(ref);todo.extend(nodes[ref][2])
        return seen
    owned=reachable(root);external=reachable(outroot)
    if any(nodes[ref][0] in ('m','e') for ref in external):
        raise Unsupported('outside graph cannot encode typed/model-set storage')
    if virtual_leaves & real_leaves:raise Unsupported('synthetic/original leaf interpretation conflict')
    shared=tuple(sorted(ref for ref in owned & external if kinds[ref] in ('d','l','q','r','u','e','m') and id(origins[ref]) not in virtual_containers))
    anchors=tuple(origins[ref] for ref in shared)
    try:rt._cold_graph_validate_inputs(anchors)
    except DomainError as error:raise Unsupported('unrepresentable boundary') from error
    order=tuple(sorted(owned));rename={ref:i for i,ref in enumerate(order)}
    emitted=[];carrier=[];leafmap={}
    for ref in order:
        tag,value,edges=nodes[ref]
        if tag in ('s','b'):
            # Ref->carrier is bijective; object identity remains the original.
            leafmap[value]=len(carrier);value=len(carrier);carrier.append(leaves[nodes[ref][1]])
        elif tag=='d':value=tuple((rename[k],rename[v]) for k,v in value)
        elif tag in ('q','l','e','r','m'):value=tuple(rename[v] for v in value)
        elif tag in ('u','c'):value=rename[value]
        emitted.append((tag,value))
    boundary=tuple((rename[ref],i) for i,ref in enumerate(shared))
    # This private prototype exposes the immutable parsed table as data. The
    # eventual graph pin must use encoded metadata+carrier, not rescan it.
    data=(rename[root],tuple(emitted),tuple(carrier),boundary,tuple(rename[r] for r in sorted(virtual_leaves & owned)),tuple(rename[r] for r in order if id(origins[r]) in virtual_containers),tuple(rename[r] for r in sorted(owned & external) if kinds[r] in ('s','b') and r not in virtual_leaves))
    data=(*data,tuple((rename[ref],next(i for i,c in enumerate(models) if type(origins[ref]) is c)) for ref in order if kinds[ref]=='m'))
    return data,anchors


def deep_immutable(value):
    if type(value) is tuple:return all(deep_immutable(v) for v in value)
    return type(value) in (str,bytes,int,bool,type(None))

# Installed only by the fixed native loader. No mutable Python view class is
# used in the production path; native absence keeps the original legacy route.
View=None


def business_equal(left,right,*,models_as_dict=False):
    """Original value equality, not handoff equality or a remembered proof."""
    from sqlalchemy.engine import RowMapping
    def shape(value):
        if type(value) is View:
            tag,_=value.node()
            if tag=='u':return None,value.label()
            if tag=='m':
                return 'dict',value.read(value.node()[1][1]) if models_as_dict else value
            if tag in ('d','r'):return 'dict',value
            if tag in ('q','l'):return ('tuple' if tag=='q' else 'list'),value
            return tag,value
        if type(value) in (dict,RowMapping):return 'dict',value
        if type(value) in (tuple,list):return ('tuple' if type(value) is tuple else 'list'),value
        return None,value
    lk,lv=shape(left);rk,rv=shape(right)
    if lk!=rk:return False
    if lk=='dict':
        keys=tuple(lv);other_keys=tuple(rv)
        return len(keys)==len(other_keys) and all(k in other_keys and business_equal(lv[k],rv[k],models_as_dict=models_as_dict) for k in keys)
    if lk in ('tuple','list'):
        return len(lv)==len(rv) and all(business_equal(a,b,models_as_dict=models_as_dict) for a,b in zip(lv,rv,strict=True))
    if lk is None:return lv==rv
    if type(left) is View or type(right) is View:return False
    return left==right

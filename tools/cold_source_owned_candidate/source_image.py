"""Uninstalled Source ownership candidate. Never dispatch authority.

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

_UNPACK=struct.Struct('!d').unpack
class View(tuple):
    __slots__=()
    def node(self):
        data,ref=tuple.__iter__(self)
        return data[1][ref]
    def label(self):
        tag,value=self.node()
        if tag=='u':return self.read(value)
        return scalar(self)
    def read(self,ref):
        return read(tuple.__getitem__(self,0),ref)
    def __getitem__(self,key):
        tag,value=self.node()
        if tag=='m':return self.read(value[1])[key]
        if tag=='r':
            keys,data,index=(self.read(v) for v in value)
            return data[index[key]]
        if tag=='d':
            if type(key) is not str:raise TypeError('data key')
            for k,v in value:
                candidate=self.read(k)
                if type(candidate) is View and candidate.node()[0]=='u':candidate=candidate.label()
                if candidate==key:return self.read(v)
            raise KeyError(key)
        if tag in ('q','l','e') and type(key) is int:return self.read(value[key])
        raise TypeError('not a source data lookup')
    def __getattr__(self,key):
        tag,value=self.node()
        if tag!='m' or type(key) is not str or key.startswith('_'):raise AttributeError(key)
        return self.read(value[1])[key]
    def __iter__(self):
        tag,value=self.node()
        if tag=='r':
            keys=self.read(value[0])
            return iter(tuple(v.label() if type(v) is View and v.node()[0]=='u' else v for v in keys))
        if tag=='d':return iter(tuple(self.read(k) for k,v in value))
        if tag in ('q','l','e'):return iter(tuple(self.read(v) for v in value))
        raise TypeError('not a source sequence')
    def __len__(self):
        tag,value=self.node()
        if tag=='r':return len(self.read(value[0]))
        if tag in ('d','q','l','e'):return len(value)
        raise TypeError('not a source container')
    def get(self,key,default=None):
        try:return self[key]
        except KeyError:return default
    def items(self):return tuple((k,self[k]) for k in self)


def scalar(view):
    data,ref=tuple.__iter__(view);tag,value=data[1][ref]
    if tag in ('s','b'):return data[2][value]
    if tag=='i':return value
    if tag=='v':return _UNPACK(value)[0]
    if tag in ('t','f'):return tag=='t'
    if tag=='n':return None
    raise TypeError('not scalar')


def read(data,ref=None):
    if ref is None:ref=data[0]
    result=tuple.__new__(View,(data,ref))
    return scalar(result) if data[1][ref][0] in ('s','b','i','v','t','f','n') else result


def image_equal(left,right):
    """Complete type/order/bits/alias comparison of reachable owned nodes."""
    if type(left) is not View or type(right) is not View:raise TypeError('owned views only')
    ld,lr=tuple.__iter__(left);rd,rr=tuple.__iter__(right);forward={};reverse={}
    def match(a,b):
        at,av=ld[1][a];bt,bv=rd[1][b]
        if at!=bt:return False
        if at=='m' and dict(ld[7]).get(a)!=dict(rd[7]).get(b):return False
        if at not in ('i','v','n','t','f'):
            if a in forward:return forward[a]==b
            if b in reverse:return False
            forward[a]=b;reverse[b]=a
        if at in ('s','b'):return ld[2][av]==rd[2][bv]
        if at in ('i','v','n','t','f'):return av==bv
        if at=='d':return len(av)==len(bv) and all(match(ak,bk) and match(aa,bb) for (ak,aa),(bk,bb) in zip(av,bv,strict=True))
        if at in ('q','l','e','r','m'):return len(av)==len(bv) and all(match(aa,bb) for aa,bb in zip(av,bv,strict=True))
        return match(av,bv)
    return match(lr,rr)


def matches_live(data,incoming,outside,anchors):
    """Prototype direct image/live matcher; no guard/serializer/deep copy.

    Not yet a native non-callback production verifier or code/schema witness.
    """
    from sim2act import natural_spec_runtime as rt,production_trial_policy as p,production_trial_sender as sender
    from sim2act.natural_source_archives import BodyArchive
    from sqlalchemy.engine import RowMapping
    from sqlalchemy.sql.elements import quoted_name
    from sim2act.contracts import Limits
    models=(p.Slot,p.ReservationIdentity,p.Outcome,sender.Capture,BodyArchive)
    root,nodes,leaves,boundary,virtual,virtual_containers,expected_shared_leaves,model_kinds=data
    model_kinds=dict(model_kinds)
    virtual=set(virtual);virtual_containers=set(virtual_containers)
    if type(anchors) is not tuple or len(boundary)!=len(anchors):return False
    pairs=dict(boundary)
    if len(pairs)!=len(boundary) or set(pairs.values())!=set(range(len(anchors))):return False
    forward={};reverse={};held=[];budget=[0]
    def tick():
        budget[0]+=1
        if budget[0]>_MAX_EDGES:raise Bounds('matcher work')
    def match(ref,live,depth=0):
        tick()
        if depth>64:return False
        tag,value=nodes[ref];kind=type(live)
        allowed=(tag=='n' and live is None or tag=='t' and live is True or tag=='f' and live is False
          or tag=='i' and kind is int or tag=='v' and kind is float or tag=='s' and kind is str
          or tag=='b' and kind is bytes or tag=='d' and kind is dict or tag=='l' and kind is list
          or tag=='q' and kind is tuple or tag=='e' and kind is set or tag=='r' and kind is RowMapping
          or tag=='u' and kind is quoted_name or tag=='m' and ref in model_kinds and 0<=model_kinds[ref]<len(models) and kind is models[model_kinds[ref]])
        if not allowed:return False
        if ref in pairs and anchors[pairs[ref]] is not live:return False
        if tag not in ('n','t','f','i','v'):
            if ref in forward:return forward[ref] is live
            if id(live) in reverse:return False
            forward[ref]=live;reverse[id(live)]=ref;held.append(live)
        if tag in ('s','b'):return live==leaves[value] if ref in virtual else live is leaves[value]
        if tag=='i':return live==value
        if tag=='v':return _PACK(live)==value
        if tag in ('n','t','f'):return True
        if tag=='d':
            return len(live)==len(value) and all(match(kr,k,depth+1) and match(vr,v,depth+1)
                for (kr,vr),(k,v) in zip(value,dict.items(live),strict=True))
        if tag in ('l','q','e'):
            if tag=='e':
                if not all(type(v) is str for v in live):return False
                sequence=sorted(live)
            else:sequence=live
            return len(sequence)==len(value) and all(match(r,v,depth+1) for r,v in zip(value,sequence,strict=True))
        if tag=='u':return match(value,str.__str__(live),depth+1)
        if tag=='r':
            storage=rt._cold_graph_row_storage(live);held.append(storage)
            return all(match(r,v,depth+1) for r,v in zip(value,storage,strict=True))
        schema=kind.__module__+'.'+kind.__qualname__
        storage=(schema,object.__getattribute__(live,'__dict__'),object.__getattribute__(live,'__pydantic_fields_set__'),
            object.__getattribute__(live,'__pydantic_extra__'),object.__getattribute__(live,'__pydantic_private__'))
        return all(match(r,v,depth+1) for r,v in zip(value,storage,strict=True))
    if not match(root,incoming):return False
    expected_mutables=set(pairs);seen_mutables=set();seen_leaves=set();visited=set();active=set()
    def mark_shared(ref):
        todo=[ref];seen=set()
        while todo:
            r=todo.pop()
            if r in seen:continue
            seen.add(r);tag,value=nodes[r]
            if tag in ('m','e'):raise Unsupported('typed/raw boundary conflict')
            if tag in ('d','l','q','r','u') and r not in virtual_containers:seen_mutables.add(r)
            if tag in ('s','b') and r not in virtual:seen_leaves.add(r)
            if tag=='d':todo.extend(v for pair in value for v in pair)
            elif tag in ('l','q','r'):todo.extend(value)
            elif tag in ('u','c'):todo.append(value)
    def walk(live,depth=0):
        tick();kind=type(live);ident=id(live)
        if depth>64 or ident in active:raise Unsupported('outside cycle/depth')
        if ident in reverse:
            mark_shared(reverse[ident]);return
        if kind in (str,bytes,int,bool,float,type(None)):return
        if ident in visited:return
        active.add(ident);held.append(live)
        if kind is dict:
            if not all(type(k) is str or type(k) is quoted_name for k in live):raise Unsupported('outside keys')
            for k,v in dict.items(live):walk(k,depth+1);walk(v,depth+1)
        elif kind in (list,tuple):
            for child in live:walk(child,depth+1)
        elif kind is RowMapping:
            storage=rt._cold_graph_row_storage(live);held.append(storage)
            for child in storage:walk(child,depth+1)
        elif kind is quoted_name:walk(str.__str__(live),depth+1)
        elif kind is Limits:
            storage=rt._cold_graph_limit_values(live);held.append(storage);walk(storage,depth+1)
        else:raise Unsupported('outside representation')
        active.remove(ident);visited.add(ident)
    walk(outside)
    return seen_mutables==expected_mutables and seen_leaves==set(expected_shared_leaves)

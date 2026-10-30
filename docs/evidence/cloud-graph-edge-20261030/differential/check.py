import copy,gc,hashlib,importlib.util,itertools,json,pickle,signal,statistics,sys,time,weakref
from pathlib import Path
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.sql.elements import quoted_name
from sim2act import natural_spec_runtime as r
from sim2act.contracts import Limits
from sim2act.errors import DomainError
root=Path('/workspace/scratch/graph-edge-candidate-20261030')
def load(name):
 p=next((root/name).glob('*.so'));spec=importlib.util.spec_from_file_location('_'+name+'._cold_graph_structure',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
modules=[load('baseline'),load('candidate')];args=(RowMapping,Limits,quoted_name,r._cold_graph_row_storage,r._cold_graph_limit_values);scope=(object(),object(),'dispatch-differential',0,'post')
def output(m,fn,*a):
 try:
  v=fn(*a)
  return ('UNSUPPORTED',) if v is m.UNSUPPORTED else ('RETURN',v)
 except BaseException as e:return ('EXCEPTION',type(e).__module__,type(e).__qualname__)
def limit():return Limits(max_requests=2,max_tools=4,max_repairs=0,max_total_tokens=64000,max_output_tokens=1024,run_seconds=300)
cases=0
for typ in ('dict','list','tuple','str','bytes'):
 def item():
  if typ=='str':return ('synthetic identity '+str(1001)).encode().decode()
  if typ=='bytes':return bytes(bytearray(b'synthetic identity 1001'))
  v={'v':[1001]};return v if typ=='dict' else ([v] if typ=='list' else (v,))
 original=[item() for _ in range(3)];clones=copy.deepcopy(original) if typ not in ('str','bytes') else [item() for _ in range(3)];choices=original+clones
 for before in itertools.product(range(3),repeat=3):
  value=[original[i] for i in before];caps=[m.snapshot(value,*args,scope) for m in modules];key=r._cold_graph_bytes(value)
  for after in itertools.product(range(6),repeat=3):
   v=[choices[i] for i in after];want=r._cold_graph_bytes(v)==key
   outs=[output(m,m.matches_fast,cap,v,scope) for m,cap in zip(modules,caps)]
   assert outs==[('RETURN',want)]*2,(typ,before,after,outs,want);cases+=1
# Type/value mismatches and unusual direct-API Encoder overlap.
values=[None,True,False,1,-1,1.0,-0.0,float('nan'),'x',b'x',[],{},(),[1],{'x':1},(1,)]
for a,b in itertools.product(values,repeat=2):
 caps=[output(m,m.snapshot,a,*args,scope) for m in modules]
 if caps[0][0]=='RETURN' and caps[1][0]=='RETURN':
  outs=[output(m,m.matches_fast,c[1],b,scope) for m,c in zip(modules,caps)]
  assert outs[0]==outs[1],(a,b,outs);cases+=1
for marker in [None,True,123,'synthetic marker',b'marker',str,object()]:
 saved=r._cold_graph_pickle_marker;r._cold_graph_pickle_marker=marker
 try:
  for a,b in [('x',marker),({'x':1},{'x':marker}),([marker,marker],[marker,marker])]:
   caps=[output(m,m.snapshot,a,*args,scope) for m in modules]
   assert caps[0][0]==caps[1][0],caps
   if caps[0][0]=='RETURN':
    outs=[output(m,m.matches_fast,c[1],b,scope) for m,c in zip(modules,caps)];assert outs[0]==outs[1],(marker,outs)
   else:assert caps[0]==caps[1],caps
   cases+=1
 finally:r._cold_graph_pickle_marker=saved
for classes in [(Limits,Limits,quoted_name),(RowMapping,RowMapping,quoted_name),(RowMapping,Limits,Limits)]:
 v=[limit(),quoted_name('quoted',None)]
 out=[output(m,m.snapshot,v,*classes,r._cold_graph_row_storage,r._cold_graph_limit_values,scope) for m in modules]
 assert out[0][0]==out[1][0]
 if out[0][0]=='RETURN':assert [m.matches_fast(c[1],v,scope) for m,c in zip(modules,out)]==[True,True]
 cases+=1
# A reducer changes an ALREADY memoized model's class before its later alias.
class OtherLimits(Limits):pass
class_mutation={}
for k,classes in [('r',(Limits,OtherLimits,quoted_name)),('c',(RowMapping,Limits,quoted_name)),('u',(RowMapping,OtherLimits,Limits))]:
 for m,name in zip(modules,('baseline','candidate')):
  first,second=limit(),limit();v=[first,second,first];cap=m.snapshot(v,*classes,r._cold_graph_row_storage,r._cold_graph_limit_values,scope);assert cap is not m.UNSUPPORTED
  original=r._cold_graph_limit_values;calls=[0]
  def changed(obj):
   calls[0]+=1
   if obj is second:object.__setattr__(first,'__class__',OtherLimits)
   return original(obj)
  r._cold_graph_limit_values=changed
  try:assert m.matches_fast(cap,v,scope) is False
  finally:r._cold_graph_limit_values=original;object.__setattr__(first,'__class__',Limits)
  class_mutation[k+'-'+name]='REJECTED'
# Reentrant original reducer and exception cleanup/refcounts.
for m in modules:
 model=limit();v=[model,model];cap=m.snapshot(v,*args,scope);original=r._cold_graph_limit_values;inside=[False];nested=[]
 def reentrant(obj):
  if not inside[0]:
   inside[0]=True
   try:nested.append(m.matches_fast(cap,v,scope))
   finally:inside[0]=False
  return original(obj)
 r._cold_graph_limit_values=reentrant
 try:assert m.matches_fast(cap,v,scope) is True and nested and all(nested)
 finally:r._cold_graph_limit_values=original
 refs=sys.getrefcount(model)
 def fail(obj):raise DomainError('VERSION_CONFLICT','Synthetic reducer failure')
 r._cold_graph_limit_values=fail
 try:assert output(m,m.matches_fast,cap,v,scope)==('EXCEPTION','sim2act.errors','DomainError')
 finally:r._cold_graph_limit_values=original
 gc.collect();assert sys.getrefcount(model)==refs and m.matches_fast(cap,v,scope) is True
# Existing owned reconstruction has different aliases from actual runtime; timing ONLY.
p=Path('/workspace/scratch/actual-g1-graph/values-own-synthetic.pickle');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='1d87fc6c0b790527481d7b512915b9ce26487ff722adfbd43c031c761e021115'
v=pickle.loads(raw);caps=[m.snapshot(v,*args,scope) for m in modules];assert all(cap is not m.UNSUPPORTED for m,cap in zip(modules,caps))
rounds=[]
for number in range(8):
 row={}
 for idx in ((0,1) if number%2==0 else (1,0)):
  start=time.perf_counter()
  for _ in range(100):assert modules[idx].matches_fast(caps[idx],v,scope) is True
  row[('baseline','candidate')[idx]]=time.perf_counter()-start
 rounds.append(row)
result=dict(status='PASS',classification='SAME_FLAGS_NATIVE_SEMANTIC_DIFFERENTIAL_PLUS_RECONSTRUCTED_SYNTHETIC_MICRO_NOT_ACTUAL_GRAPH_NOT_FULL_CHAIN',cases=cases,class_mutation=class_mutation,reentrant_and_exception_cleanup='PASS',rounds=rounds,median_ratio=statistics.median(x['candidate']/x['baseline'] for x in rounds))
(root/'differential-and-reconstructed-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

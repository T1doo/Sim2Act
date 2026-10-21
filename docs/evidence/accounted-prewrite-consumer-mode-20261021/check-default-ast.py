import ast,copy,json,subprocess
from pathlib import Path
BASE='f387c391b78554fa117c614c5a6af3ce37bf647e'
FILES={
 'src/sim2act/natural_live_admission.py':['_graph_stage_current','_graph_run_context','_graph_trial_stage_models_from_raw','_graph_trial_accounted_models','_graph_trial_stage_models','_graph_trial_stage_raw'],
 'src/sim2act/natural_source_archives.py':['_graph_source_bodies','_graph_resolve_trial_source'],
 'src/sim2act/pa_trial_dispatch.py':['_graph_stage_accounted','_graph_pb_accounting','_graph_pb_archive_chain'],
 'src/sim2act/natural_spec_runtime.py':['_ColdTrialGraph.__init__','_ColdTrialGraph._typed_parameters','_ColdTrialGraph._accounted_fields','_ColdTrialGraph._fields','_ColdTrialGraph.check','_ColdTrialGraph._prepare','_ColdTrialGraph.commit'],
}
def locate(tree,name):
 n=tree
 for part in name.split('.'):
  n=next(x for x in n.body if getattr(x,'name',None)==part)
 return n
class Default(ast.NodeTransformer):
 def __init__(self,runtime): self.runtime=runtime
 def truth(self,n):
  s=ast.unparse(n)
  candidates=['_owned','_accounted_prewrite','self.accounted_prewrite']
  if self.runtime: candidates += ['owned', "getattr(self, 'accounted_prewrite', None)"]
  for expr in candidates:
   if s==expr+' is None': return True
   if s==expr+' is not None': return False
  return None
 def visit_FunctionDef(self,n):
  new=[(a,d) for a,d in zip(n.args.kwonlyargs,n.args.kw_defaults) if a.arg not in ('_owned','_accounted_prewrite')]
  n.args.kwonlyargs=[a for a,d in new]; n.args.kw_defaults=[d for a,d in new]
  return self.generic_visit(n)
 def visit_Assign(self,n):
  if self.runtime and len(n.targets)==1:
   s=ast.unparse(n.targets[0]); v=ast.unparse(n.value)
   if s=='self.accounted_prewrite' and v=='_accounted_prewrite': return None
   if s=='owned' and v=="getattr(self, 'accounted_prewrite', None)": return None
  return self.generic_visit(n)
 def visit_If(self,n):
  v=self.truth(n.test)
  if v is None: return self.generic_visit(n)
  result=[]
  for child in (n.body if v else n.orelse):
   val=self.visit(child)
   if isinstance(val,list): result.extend(val)
   elif val is not None: result.append(val)
  return result
 def visit_IfExp(self,n):
  v=self.truth(n.test)
  return self.generic_visit(n) if v is None else self.visit(n.body if v else n.orelse)
 def visit_Call(self,n):
  self.generic_visit(n)
  n.keywords=[k for k in n.keywords if not(k.arg is None and isinstance(k.value,ast.Dict) and not k.value.keys)]
  return n
results=[]
for file,names in FILES.items():
 old=ast.parse(subprocess.check_output(['git','show',BASE+':'+file],text=True))
 cur=ast.parse(Path(file).read_text())
 for name in names:
  a=locate(old,name); b=Default(file.endswith('natural_spec_runtime.py')).visit(copy.deepcopy(locate(cur,name)))
  same=ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
  results.append(dict(file=file,function=name,default_none_ast_equal=same))
  if not same:
   Path('/tmp/sim2act-accounted-prewrite-20261021/ast-'+name.replace('.','-')+'-before.py').write_text(ast.unparse(a))
   Path('/tmp/sim2act-accounted-prewrite-20261021/ast-'+name.replace('.','-')+'-after.py').write_text(ast.unparse(b))
for file,names in {'src/sim2act/natural_spec_runtime.py':['_ColdGraphRead','_ColdGraphPickler','_cold_graph_validate_inputs','_cold_graph_row_storage','_cold_graph_bytes','_cold_graph_read'],'src/sim2act/natural_live_admission.py':['TrialContract','PBTrialContract','TrialCaps','_require_run_context_row']}.items():
 old=ast.parse(subprocess.check_output(['git','show',BASE+':'+file],text=True)); cur=ast.parse(Path(file).read_text())
 for name in names:
  try:a,b=locate(old,name),locate(cur,name)
  except StopIteration:continue
  results.append(dict(file=file,function=name,unchanged_ast=ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)))
path=Path('/tmp/sim2act-accounted-prewrite-20261021/default-path-ast.json')
path.write_text(json.dumps(dict(baseline=BASE,method='Specialize explicit new mode to None; flatten only its branches/kwargs and unused local mode assignment. Existing additive _accounted_test branches stay intact. Static evidence, not runtime qualification.',results=results),indent=2)+'\n')
print(json.dumps(results))

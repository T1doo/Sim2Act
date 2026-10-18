from pathlib import Path
import ast, copy, hashlib, json, subprocess
repo=Path('/workspace/Sim2Act'); out=Path('/workspace/production-trial-stages-review-20261018')
base='faac95dce3174c426295fda26e40acf14a11a9c1'
def git(*args): return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=repo).decode()
class RemoveReadWrappers(ast.NodeTransformer):
 def visit_ImportFrom(self,node):
  if node.module=='pa_trial_dispatch':
   node.names=[n for n in node.names if n.name!='_journal_reads']
   if not node.names: return None
  return node
 def visit_With(self,node):
  self.generic_visit(node)
  node.items=[i for i in node.items if not (isinstance(i.context_expr,ast.Call) and isinstance(i.context_expr.func,ast.Name) and i.context_expr.func.id=='_journal_reads')]
  return node if node.items else node.body
 def visit_FunctionDef(self,node):
  if node.name=='_journal_reads': return None
  return self.generic_visit(node)
paths=['src/sim2act/natural_spec_runtime.py','src/sim2act/pa_spec_apps.py','src/sim2act/pa_trial_dispatch.py']
for p in paths:
 old=ast.parse(git('show',base+':'+p))
 current=RemoveReadWrappers().visit(ast.parse((repo/p).read_text()))
 assert ast.dump(old,include_attributes=False)==ast.dump(current,include_attributes=False), p
p='tests/test_production_trial_stages.py'
old=ast.parse(git('show',base+':'+p)); current=ast.parse((repo/p).read_text())
oldfn=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='test_original_controller_store_is_fixed_through_late_body_and_failure')
newfn=next(n for n in current.body if isinstance(n,ast.FunctionDef) and n.name==oldfn.name)
changes=0
for n in ast.walk(newfn):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Store':
  for k in n.keywords:
   if k.arg=='test_only':
    assert isinstance(k.value,ast.Constant) and k.value.value is True
    k.value=ast.Constant(value=False);changes+=1
assert changes==1
assert ast.dump(old,include_attributes=False)==ast.dump(current,include_attributes=False)
record={'kind':'PURE_FILE_AST_ONLY','base':base,'status':'NO_DEFINITE_P1_P2_PENDING_FREEZE_ACTUAL','original_three_product_modules_ast_identical_after_removing_only_read_context_wrappers_and_helper':True,'all_original_guards_parsers_receipts_callbacks_and_SQL_write_order_preserved':True,'test_only_difference':'D second SQLite Store is test_only=True; other test AST unchanged','files':[{'path':p,'bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in paths+['tests/test_production_trial_stages.py']],'limits':['No product/test/application imports or DB/SQL/network','AST proves preserved syntax/order, not successful execution or performance','Directory remains unsealed']}
(out/'receive-segment-wip-ast-verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':record['status'],'product_modules_normalized_ast_equal':len(paths),'test_changed_literals':changes}))

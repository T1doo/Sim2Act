import ast,hashlib,json,subprocess
from pathlib import Path
repo=Path('/workspace/Sim2Act');out=Path('/workspace/csv-continuous-column-evidence-20261017')
shas=['ce3fa86677cdaa58e076cc03e15a9b5414fd1e77','d74f2fed55b6067e5d3c34ca6e4348b92e75f48a','b589809375c89b4d93617d91c780a1e0f7f704e2']
def content(sha,path):return subprocess.check_output(['git','show',sha+':'+path],cwd=repo)
def h(b):return hashlib.sha256(b).hexdigest()
unchanged={}
for path in ('src/sim2act/worker.py','src/sim2act/tools.py','src/sim2act/db.py','src/sim2act/contracts.py'):
 vals={sha:h(content(sha,path)) for sha in shas};assert len(set(vals.values()))==1;unchanged[path]=vals
algorithms={}
for path,names in {'src/sim2act/csv_goal_revisions.py':['effective','calculate','source_gate','eligibility','proposal_tx','job_gate'], 'src/sim2act/delivery_graph_apps.py':['current','derive','state','build','metadata','lookup','checked_request','load_family']}.items():
 algorithms[path]={}
 for name in names:
  vals={}
  for sha in shas:
   tree=ast.parse(content(sha,path));node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
   vals[sha]=h(ast.dump(node,include_attributes=False).encode())
  assert len(set(vals.values()))==1,(path,name);algorithms[path][name]=vals
exact={}
for path in ('src/sim2act/csv_column_revisions.py','src/sim2act/csv_goal_revisions.py','src/sim2act/lifecycle.py','tests/test_csv_column_revisions_negative.py'):
 vals={sha:h(content(sha,path)) for sha in shas[1:]};assert len(set(vals.values()))==1;exact[path]=vals
changes=subprocess.check_output(['git','diff','--name-status',shas[0],shas[-1]],cwd=repo,text=True).splitlines()
report=dict(status='PASS',source_shas=shas,unchanged_worker_executor_store_contract_files=unchanged,legacy_algorithms_ast_unchanged=algorithms,d74_to_b589_exact_backend_files=exact,changes_from_ce3=changes,scope='Proof of code continuity, not a claim that all test cases ran in one final frozen batch.')
(out/'source-continuity.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(status='PASS',unchanged_files=len(unchanged),unchanged_legacy_functions=sum(len(x) for x in algorithms.values()),d74_backend_files_unchanged=len(exact),changed_files=len(changes)),indent=2))

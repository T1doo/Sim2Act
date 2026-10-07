import ast,json,os,subprocess,sys,tempfile,time,statistics,hashlib
from pathlib import Path
root=Path('/workspace/Sim2Act-bounded-product-candidate');source=root/'scripts/conditional-ui/run_fixture.py';before=source.read_text();after=before
canonical='from sim2act.conditional_runs import GOAL, candidate_for, validate_snapshot\n'
verified='from sim2act.protocol_jobs import verified_pending\n'
worker='from sim2act.worker import Worker\n'
helper='    # Reuse the canonical test transport, never its gold or a product provider setting.\n    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))\n    from test_conditional_run_bindings import envelope, factory, report\n\n'
for line in [canonical,verified,worker,helper]:
 assert line in after;after=after.replace(line,'',1)
point='            snapshot = job["accepted_snapshot"]\n'
after=after.replace(point,'            '+canonical.strip()+'\n            '+verified.strip()+'\n'+point,1)
point='        if phase == "source":\n            replies = '
after=after.replace(point,'        '+worker.strip()+'\n'+helper.replace('    ','        ',1).replace('\n    ','\n        ')+point,1)
ast.parse(after)
child=r'''
import contextlib,importlib.util,json,sys,tempfile,types
from pathlib import Path
from sim2act import db
class Result:
 def mappings(self):return self
 def first(self):return None
class Conn:
 def execute(self,statement):return Result()
class FakeStore:
 def __init__(self,*a,**k):self.engine=self
 @contextlib.contextmanager
 def tx(self):yield Conn()
 def dispose(self):pass
db.Store=FakeStore
path=Path(sys.argv[1]);mode=sys.argv[2]; original=sys.argv[3]
m=types.ModuleType('run_fixture');m.__file__=original;exec(compile(path.read_text(),original,'exec'),m.__dict__);sys.modules['run_fixture']=m
s=importlib.util.spec_from_file_location('actual_fixture',str(Path(original).with_name('fixture.py')));f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
with tempfile.TemporaryDirectory(prefix='no-db-fifo-') as d:
 p=Path(d);(p/'fixture.db').touch();(p/'info.json').write_text(json.dumps({'bearer':'synthetic-protocol-browser-A','project':'synthetic-project','user':'synthetic-user','source':'synthetic-source'}))
 try:f.action(p,'run-source')
 except ValueError as e:
  if str(e)!="Expected current project's oldest queued Run":raise
 else:raise RuntimeError('missing FIFO guard')
 loaded={n:n in sys.modules for n in ['pytest','sim2act.worker','test_conditional_run_bindings','sim2act.conditional_runs','sim2act.protocol_jobs']}
 if mode=='after' and any(loaded.values()):raise RuntimeError('unexpected eager helper import')
 print(json.dumps({'fifo_guard':'same ValueError','loaded':loaded,'database_connected':False}))
'''
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':'Temporary transformed source only, exact original __file__, actual fixture action entry, fake Store/FIFO no queued row; no database/API/provider call.'}
env={**os.environ,'PYTHONPATH':str(root/'src')};py='/workspace/sim2act-pb-venv/bin/python'
with tempfile.TemporaryDirectory(prefix='run-import-review-') as d:
 paths={}
 for label,text in [('before',before),('after',after)]:
  paths[label]=Path(d)/(label+'.py');paths[label].write_text(text)
 samples={'before':[],'after':[]}
 for label in ['before','after','after','before']*3:
  start=time.perf_counter();p=subprocess.run([py,'-O','-c',child,str(paths[label]),label,str(source)],cwd=root,env=env,capture_output=True,text=True,timeout=10);elapsed=time.perf_counter()-start
  if p.returncode:print(p.stderr);raise RuntimeError('pure noqueued probe failed')
  samples[label].append(round(elapsed,6));result[label+'_witness']=json.loads(p.stdout)
 result['samples_seconds']=samples;result['medians_seconds']={k:statistics.median(v) for k,v in samples.items()}
Path('/tmp/independent-run-fixture-import-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

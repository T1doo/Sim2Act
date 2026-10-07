import json,os,subprocess,sys,tempfile,time,hashlib,statistics
from pathlib import Path
root=Path('/workspace/Sim2Act-bounded-product-candidate');py='/workspace/sim2act-pb-venv/bin/python';fixture=root/'scripts/conditional-ui/fixture.py';env={**os.environ,'PYTHONPATH':str(root/'src')};result={'source_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'fresh_checks':[],'micro':{}}
code=r'''
import importlib.util,sys,json,runpy,io
from pathlib import Path
path=sys.argv[1]; mode=sys.argv[2]; target=sys.argv[3]
if mode=='invalid':
 s=importlib.util.spec_from_file_location('fresh_fixture',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 for line in ['not-json','[]','{"action":"snapshot","extra":1}','{"action":null}','{"action":"unknown"}']:
  try:m.session_request(line)
  except ValueError:pass
  else:raise RuntimeError('accepted invalid protocol')
else:
 sys.argv=[path,'--root',target,'--session'];sys.stdin=io.StringIO('');runpy.run_path(path,run_name='__main__')
heavy=[n for n in ['sqlalchemy','sim2act.db','sim2act.conditional_checks'] if n in sys.modules]
if heavy:raise RuntimeError('heavy modules eagerly loaded')
if list(Path(target).iterdir()):raise RuntimeError('unexpected fixture preparation')
print(json.dumps({'mode':mode,'heavy_loaded':heavy,'optimized':not __debug__}))
'''
with tempfile.TemporaryDirectory(prefix='independent-lazy-') as d:
 for mode in ['invalid','eof']:
  o=subprocess.run([py,'-O','-c',code,str(fixture),mode,d],cwd=root,env=env,text=True,capture_output=True,timeout=10);assert o.returncode==0,(mode,o.returncode);result['fresh_checks'].append(json.loads(o.stdout))
 before=Path(d)/'fixture_before.py';before.write_bytes(subprocess.check_output(['git','show','9dc833a:scripts/conditional-ui/fixture.py'],cwd=root))
 for mode in ['eof','invalid']:
  samples={'before':[],'after':[]}
  for label in ['before','after','after','before']*3:
   source=before if label=='before' else fixture
   start=time.perf_counter();o=subprocess.run([py,'-O',str(source),'--root',d,'--session'],input='' if mode=='eof' else 'not-json\n',cwd=root,env=env,text=True,capture_output=True,timeout=10);elapsed=time.perf_counter()-start
   assert o.returncode==(0 if mode=='eof' else 1) and not o.stdout
   samples[label].append(round(elapsed,6))
  result['micro'][mode]={'samples_seconds':samples,'median_seconds':{label:statistics.median(values) for label,values in samples.items()},'order':'ABBA x3, each fresh process; no module/fixture cache'}
Path('/tmp/independent-lazy-dependency-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

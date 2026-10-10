import pathlib,json,hashlib,subprocess,sys,os,time,signal,runpy,traceback,threading
ROOT=pathlib.Path('/tmp/sim2act-native-diagnostics-independent-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='d8f2101b5259be5b51d00eca527db7cf3b4c5b37';PLUGIN=REPO/'scripts/native_pytest_diagnostics.py';api=runpy.run_path(str(PLUGIN));summarize=api['summarize'];results=[]
def freeze(label):
 m=json.loads(pathlib.Path('/tmp/sim2act-native-diagnostics-20261010/source-freeze.json').read_text())['files'];a={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in m};g={p:hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest() for p in m};h=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();out={'sha':h,'count':len(m),'worktree_match':a==m,'git_match':g==m,'files':a};(ROOT/('source-'+label+'.json')).write_text(json.dumps(out,indent=2));assert h==SHA and a==g==m;return out
freeze('before')
ENV={**os.environ,'PYTHONPATH':str(REPO),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONUTF8':'1'}
for key in ['PYTEST_ADDOPTS','SIM2ACT_TEST_DATABASE_URL','GITHUB_STEP_SUMMARY']:ENV.pop(key,None)
def command(folder,enabled=True,selection=None):
 args=[sys.executable,'-m','pytest','-q','--junitxml',str(folder/'junit.xml')]
 if enabled:args+=['-p','scripts.native_pytest_diagnostics','--ci-diagnostics',str(folder/'events.jsonl')]
 if selection:args+=selection
 return args

def report(folder,xml=None):
 env={**ENV,'GITHUB_STEP_SUMMARY':str(folder/'step-summary.md')};r=subprocess.run([sys.executable,str(PLUGIN),'--report',str(folder/'events.jsonl'),'--junit',str(xml or folder/'junit.xml')],env=env,cwd=folder,text=True,capture_output=True,timeout=15);(folder/'report.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr;return r

def ck(v,label,checks):assert v,label;checks.append(label)
# Real failing pytest phase data; every value is intentionally synthetic.
for case in ['redaction','normal-selection','hard-kill','tail-and-missing']:
 folder=ROOT/case;folder.mkdir(exist_ok=True);checks=[];start=time.monotonic()
 try:
  if case=='redaction':
   (folder/'test_fixture.py').write_text('''def test_failure():
    assert False, "postgresql+psycopg://ciuser:CI_SYNTHETIC_DB@127.0.0.1/db Bearer CI_SYNTHETIC_BEARER authorization='Basic CI_SYNTHETIC_BASIC' password='first CI_SYNTHETIC_SPACED_PASSWORD' api_key='CI_SYNTHETIC_API' token='CI_SYNTHETIC_TOKEN' secret='CI_SYNTHETIC_SECRET'"
''')
   child=subprocess.run(command(folder),cwd=folder,env=ENV,capture_output=True,text=True,timeout=15);(folder/'child.log').write_text(child.stdout+child.stderr);ck(child.returncode==1,'real synthetic failure exit1',checks);r=report(folder);events=(folder/'events.jsonl').read_text();diag='\n'.join(s for s in child.stdout.splitlines() if s.startswith('SIM2ACT_CI_DIAGNOSTIC '));channels={'file':events,'stdout_diagnostics':diag,'Report':r.stdout};tokens=['CI_SYNTHETIC_DB','CI_SYNTHETIC_BEARER','CI_SYNTHETIC_BASIC','CI_SYNTHETIC_SPACED_PASSWORD','CI_SYNTHETIC_API','CI_SYNTHETIC_TOKEN','CI_SYNTHETIC_SECRET'];leaks={name:[t for t in tokens if t in text] for name,text in channels.items()};(folder/'redaction-result.json').write_text(json.dumps({'leaks':leaks,'all_values_synthetic':True},indent=2));ck(not any(leaks.values()),'all credential-key values redacted in new diagnostic channels',checks)
  elif case=='normal-selection':
   (folder/'conftest.py').write_text('''from pathlib import Path
import pytest
@pytest.fixture(autouse=True)
def lifecycle(request):
    with Path('fixture-effects.txt').open('a') as stream:stream.write('setup '+request.node.name+'\\n')
    yield
    with Path('fixture-effects.txt').open('a') as stream:stream.write('teardown '+request.node.name+'\\n')
''');(folder/'test_fixture.py').write_text('''import pytest
def test_selected_pass():pass
def test_selected_fail():assert False, 'own bounded failure'
def test_unselected():raise AssertionError('must not be selected')
@pytest.mark.skip(reason='own expected skip')
def test_selected_skip():pass
''')
   base=subprocess.run(command(folder,False,['-k','selected and not unselected']),cwd=folder,env=ENV,text=True,capture_output=True,timeout=15);(folder/'baseline.log').write_text(base.stdout+base.stderr);effects=(folder/'fixture-effects.txt').read_text();(folder/'fixture-effects.txt').unlink();child=subprocess.run(command(folder,True,['-k','selected and not unselected']),cwd=folder,env=ENV,text=True,capture_output=True,timeout=15);(folder/'child.log').write_text(child.stdout+child.stderr);ck(base.returncode==child.returncode==1,'observer preserves actual baseline exit status',checks);ck((folder/'fixture-effects.txt').read_text()==effects,'observer preserves exact fixture setup/teardown effects and order',checks);summary=summarize(folder/'events.jsonl');ck(summary['collected']==3 and summary['started']==3 and summary['finished']==3,'exact -k selected set remains3',checks);ck(summary['suite_complete'] and len(summary['failures'])==1,'normal selected failure reports complete suite without pass claim',checks);r=report(folder);ck('"failure_reports": 1' in r.stdout and '"suite_complete": true' in r.stdout,'Report preserves normal failing suite completeness',checks)
  elif case=='hard-kill':
   (folder/'test_fixture.py').write_text('''import time
def test_first_failure():assert False, 'CI_KILL_EARLIER_FAILURE'
def test_active_block():time.sleep(60)
def test_never_started():raise AssertionError('not executed')
''');cmd=command(folder);(folder/'command.json').write_text(json.dumps(cmd));log=folder/'child.log'
   with log.open('w') as stream:child=subprocess.Popen(cmd,cwd=folder,env=ENV,stdout=stream,stderr=subprocess.STDOUT,text=True)
   try:
    end=time.monotonic()+10
    while time.monotonic()<end:
     if (folder/'events.jsonl').exists():
      entries=[json.loads(x) for x in (folder/'events.jsonl').read_text().splitlines()]
      if any(x['event']=='node_start' and 'test_active_block' in x.get('nodeid','') for x in entries):break
     assert child.poll() is None,'child ended before hard kill';time.sleep(.02)
    else:raise AssertionError('10s owned hard kill fixture failed to reach active')
    child.kill();child.wait(timeout=5)
   finally:
    if child.poll() is None:child.kill();child.wait(timeout=5)
   summary=summarize(folder/'events.jsonl');(folder/'summary.json').write_text(json.dumps(summary,indent=2));ck(child.returncode==-signal.SIGKILL,'owned child actually hard-killed without Python cleanup',checks);ck(summary['active_nodes']==['test_fixture.py::test_active_block'] and summary['not_started_count']==1,'hard kill recovers exact active and unstarted count',checks);ck(not summary['suite_complete'] and summary['exitstatuses']==[],'hard kill is explicitly incomplete with no fake finish',checks);ck(len(summary['failures'])==1 and 'CI_KILL_EARLIER_FAILURE' in summary['failures'][0]['failure'],'earlier failed phase remains in closed JSONL append',checks);text=log.read_text();diagnostics='\n'.join(s for s in text.splitlines() if s.startswith('SIM2ACT_CI_DIAGNOSTIC '));ck('CI_KILL_EARLIER_FAILURE' in diagnostics and 'test_active_block' in diagnostics,'failure and active node already flushed in stdout before kill',checks);r=report(folder);ck('CI_KILL_EARLIER_FAILURE' in r.stdout and 'test_active_block' in r.stdout and '"suite_complete": false' in r.stdout,'always-style Report recovers earlier failure and active after hard kill',checks);ck('"suite_complete": false' in (folder/'step-summary.md').read_text(),'step summary durable incomplete flag',checks)
  else:
   result=summarize(folder/'events.jsonl');ck(not result['evidence_present'] and not result['suite_complete'],'missing trace incomplete',checks);(folder/'events.jsonl').write_text(json.dumps({'event':'node_start','nodeid':'own-node'})+'\n{"event":');result=summarize(folder/'events.jsonl');ck(result['incomplete_tail'] and result['active_nodes']==['own-node'] and not result['suite_complete'],'partial final append retains prior active and incomplete',checks);r=report(folder);ck('"incomplete_tail": true' in r.stdout and 'own-node' in r.stdout,'Report survives incomplete final JSONL append',checks)
  results.append({'case':case,'status':'PASS','checks':checks,'seconds':time.monotonic()-start})
 except Exception:
  err=traceback.format_exc();(folder/'failure.log').write_text(err);results.append({'case':case,'status':'FAIL','checks':checks,'error':err});print(err,flush=True)
 print(case,results[-1]['status'],len(checks),flush=True)
(ROOT/'results.json').write_text(json.dumps(results,indent=2));freeze('after');assert all(r['status']=='PASS' for r in results)

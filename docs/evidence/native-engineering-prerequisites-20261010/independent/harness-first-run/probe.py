import pathlib,json,subprocess,hashlib,runpy,sys,os,traceback,ast
from decimal import Decimal
ROOT=pathlib.Path('/tmp/sim2act-native-prerequisites-independent-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='9002bf958f79972e576e831ebdf5e0d90fc44ea5';OLD='88cb3c64b5dcbaf3df7183ebbf72773547585e15'
# Explicitly keep this private probe SQLite-only.
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None)
sys.path.insert(0,str(REPO/'tests'))
from conftest import env as fixture
from sim2act.db import resources,operations,attempts
from sqlalchemy import select

def freeze(label):
 f=json.loads(pathlib.Path('/tmp/sim2act-native-prerequisites-20261010/source-freeze.json').read_text());a={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in f['files']};g={p:hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest() for p in f['files']};h=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip();assert h==SHA and a==g==f['files'];out={'sha':SHA,'count':len(a),'git_worktree_manifest_match':True,'files':a};(ROOT/('source-'+label+'.json')).write_text(json.dumps(out,indent=2));return out
freeze('before')
oldtext=subprocess.check_output(['git','show',OLD+':tests/test_csv_dag.py'],cwd=REPO,text=True);(ROOT/'old-88-test_csv_dag.py').write_text(oldtext)
old={'__file__':str(REPO/'tests/test_csv_dag.py'),'__name__':'independent_old_csv_test'};exec(compile(oldtext,old['__file__'],'exec'),old)
new=runpy.run_path(str(REPO/'tests/test_csv_dag.py'))
checks=[];results=[]
def check(v,label):assert v,label;checks.append(label)
for nl in ['lf','crlf']:
 folder=ROOT/nl;folder.mkdir(exist_ok=True);raw=(REPO/'tests/fixtures/column-binding.csv').read_bytes().replace(b'\r\n',b'\n');raw=raw if nl=='lf' else raw.replace(b'\n',b'\r\n');p=folder/'material.csv';p.write_bytes(raw);content=p.read_text(encoding='utf-8');normalized=content.encode('utf-8');check(content.splitlines()==['item,amount,quantity','A,10,7','B,20,8'],'independent exact input rows '+nl);check(str(sum([Decimal('7'),Decimal('8')]))=='15','independent Decimal total '+nl)
 hashes={'raw':hashlib.sha256(raw).hexdigest(),'uploaded_utf8':hashlib.sha256(normalized).hexdigest()};check((hashes['raw']==hashes['uploaded_utf8'])==(nl=='lf'),'newline raw/upload distinction '+nl)
 for version,module in [('old',old),('new',new)]:
  loc=folder/version;loc.mkdir(exist_ok=True);gen=fixture.__wrapped__(loc);e=next(gen)
  module['test_three_actual_receipts_exact_report_and_old_request_recovery'].__globals__['CSV']=p
  status='PASS'
  try:module['test_three_actual_receipts_exact_report_and_old_request_recovery'](e)
  except AssertionError:
   status='EXPECTED_FAIL' if version=='old' and nl=='crlf' else 'FAIL';(loc/'failure.log').write_text(traceback.format_exc())
  finally:
   try:next(gen)
   except StopIteration:pass
  check(status==('EXPECTED_FAIL' if version=='old' and nl=='crlf' else 'PASS'),'old/new unchanged full case '+nl+'/'+version);results.append({'newline':nl,'version':version,'status':status,'hashes':hashes})
 # Independent API oracle, separate from invoking the existing case body.
 loc=folder/'own-api';loc.mkdir(exist_ok=True);gen=fixture.__wrapped__(loc);e=next(gen)
 try:
  rid,base,plan,confirm,worker,job=new['setup'](e,content)
  worker.process(job);resp=e[2].get('/api/runs/'+job['id']);check(resp.status_code==200,'own accepted run readable '+nl);body=resp.json();check(body['status']=='SUCCEEDED','own run succeeded '+nl);o=body['result']['output'];check(o['resource_id']==rid and o['column']=='quantity' and o['count']==2 and o['sum']=='15' and o['source_hash']==hashes['uploaded_utf8'] and o['text']=='列 quantity；行数 2；合计 15','own independently expected exact data/hash/text '+nl)
  with e[0].engine.connect() as conn:
   resource=conn.execute(select(resources).where(resources.c.id==rid)).mappings().one();check(resource['content']==content and resource['hash']==hashes['uploaded_utf8'],'own actual saved content/hash '+nl);ops=list(conn.execute(select(operations).where(operations.c.run_id==job['id'])).mappings());check(len(ops)==3 and {r['call_id'] for r in ops}=={'preview','aggregate','report'},'own three durable receipts '+nl);check(not conn.execute(select(attempts)).first(),'own zero model attempts '+nl)
  check(body['model_requests']==body['business_writes']==0,'own zero model/business effects '+nl);again=e[2].post(base+'/plan/runs',json=confirm);check(again.status_code==202 and again.json()['cached'] and again.json()['run_id']==job['id'],'own exact old request recovery '+nl)
  e[2].headers['Authorization']='Bearer synthetic-test-B';denied=e[2].get('/api/runs/'+job['id']);check(denied.status_code==403,'own foreign owner cannot read '+nl);e[2].headers['Authorization']='Bearer synthetic-test-A';check(e[2].get('/api/runs/'+job['id']).json()==body,'own foreign read does not change result '+nl)
 finally:
  try:next(gen)
  except StopIteration:pass
origin=REPO/'docs/evidence/engineering-pg-phase-20261008/first/node-tools'
for name in ['package.json','package-lock.json']:check((REPO/'scripts/engineering-ci'/name).read_bytes()==(origin/name).read_bytes(),'exact existing engineering lock origin '+name)
lock=json.loads((REPO/'scripts/engineering-ci/package-lock.json').read_text());check(lock['packages']['node_modules/jsdom']['version']=='30.1.2' and lock['packages']['node_modules/playwright-core']['version']=='1.63.0','locked actual dependency versions')
ci=(REPO/'scripts/WindowsCI.ps1').read_text();oldci=subprocess.check_output(['git','show',OLD+':scripts/WindowsCI.ps1'],cwd=REPO,text=True)
check("$NodeTools = Join-Path $JobRoot 'engineering-node'" in ci and '--prefix $NodeTools --ignore-scripts --no-audit --no-fund' in ci and "--cache (Join-Path $JobRoot 'npm-cache')" in ci,'owned npm prefix/cache with lifecycle scripts disabled');check('--registry=https://registry.npmjs.org' in ci and '--fetch-retries=0 --fetch-timeout=30000' in ci and 'no alternative source' in ci,'explicit registry bounded fetch and failure closed');check('$PreviousNodePath = $env:NODE_PATH' in ci and '$env:NODE_PATH = $PreviousNodePath' in ci[ci.index('    } finally {',ci.index("} elseif ($Phase -eq 'Test')")):],'NODE_PATH previous value restored finally');check('require.resolve("jsdom/package.json")' in ci and '"30.1.2"' in ci and '!p.startsWith(process.argv[1]+require("path").sep)' in ci,'pre-pytest actual resolved jsdom version and owned path checked')
for p in ['.github/workflows/windows-native-mock.yml','scripts/Test.ps1','scripts/WindowsBrowserCI.ps1','scripts/browser-ci/package-lock.json']:
 if (REPO/p).exists():check((REPO/p).read_bytes()==subprocess.check_output(['git','show',OLD+':'+p],cwd=REPO),'untouched original scope/budget/script '+p)
oldfn=ast.parse(oldtext);newtext=(REPO/'tests/test_csv_dag.py').read_text();newfn=ast.parse(newtext);find=lambda tree:next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='test_three_actual_receipts_exact_report_and_old_request_recovery');a=find(oldfn).body;b=find(newfn).body
check([ast.dump(n,include_attributes=False) for n in a[6:]]==[ast.dump(n,include_attributes=False) for n in b[7:]],'all receipt/model/replay/durable assertions after hash remain AST identical')
(ROOT/'probe-results.json').write_text(json.dumps({'sha':SHA,'verdict':'PASS','checks':checks,'count':len(checks),'cases':results,'actual_models':0,'PG':False,'PS_runtime':False},indent=2));print(json.dumps({'verdict':'PASS','checks':len(checks),'cases':results},indent=2))

import hashlib,json,os,subprocess,tempfile
from pathlib import Path
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None)
from conftest import env as fixture
from test_project_column_material_reuse import setup,accept,work
from test_csv_dag_instances import create
ROOT=Path('/tmp/project-csv-reuse-independent-20261011');REPO=Path('/workspace/Sim2Act')
F=json.loads((REPO/'docs/evidence/project-column-material-reuse-20261011/frozen-before.json').read_text())['files'];assert F and all(hashlib.sha256((REPO/f).read_bytes()).hexdigest()==h for f,h in F.items())
hashes={f:h for f,h in F.items() if f.startswith('src/')}
tmp=Path(tempfile.mkdtemp(prefix='ui-',dir=ROOT));g=fixture.__wrapped__(tmp);e=next(g)
try:
 source,old,group,obj,body,path=setup(e,False,content='label,amount,quantity\nui-X,100,2.5\nui-Y,-8,1.25\n')
 value,accepted,_,_=accept(e,path,body,'ind-ui-run');job=work(e,accepted)
 r=e[2].post('/api/csv-dag/runs/'+job['id']+'/release-approvals',json=dict(expected_plan_fingerprint=value['plan']['plan_fingerprint'],request_key='ind-ui-release'));assert r.status_code==201,r.text
 r=e[2].post('/api/internal/approvals/'+r.json()['id']+'/commit',json=dict(fingerprint=r.json()['fingerprint']));assert r.status_code==200,r.text
 rel=r.json();i=create(e,rel);info=tmp/'info.json';out=tmp/'result.json';info.write_text(json.dumps(dict(project=e[5],app=body['target_app_id'],release=rel,instance=i['id'],web=str(REPO/'src/sim2act/web'),output=str(out))))
 proc=subprocess.Popen(['node',str(ROOT/'ui_probe.js'),str(info)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=os.environ.copy())
 for line in proc.stdout:
  q=json.loads(line)
  if q.get('done'):break
  r=e[2].request(q['method'],q['path'],json=q.get('body'),headers=q.get('headers'));answer=dict(id=q['id'],status=r.status_code,text=r.text,content_type=r.headers.get('content-type'));proc.stdin.write(json.dumps(answer)+'\n');proc.stdin.flush()
 code=proc.wait(timeout=20);error=proc.stderr.read();(tmp/'stderr.log').write_text(error)
 result=json.loads(out.read_text());result['source_sha256']=hashes;result['source_sha256_after']={f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in hashes};assert result['source_sha256_after']==hashes
 (ROOT/'ui-first-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('UI',result['status'],'checks',len(result['checks']),'failures',len(result['failures']),'output',out);print(error)
 raise SystemExit(code)
finally:
 if 'proc' in globals() and proc.poll() is None:proc.kill();proc.wait(timeout=10)
 g.close()

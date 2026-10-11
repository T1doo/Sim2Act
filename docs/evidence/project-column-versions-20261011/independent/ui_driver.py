import hashlib,json,os,subprocess,tempfile
from pathlib import Path
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None)
from conftest import env as fixture
from test_project_column_patches import start, work
from test_csv_dag import NoModel
from sim2act.worker import Worker
from test_delivery_graph_apps import snapshot
ROOT=Path('/tmp/project-column-versions-independent');REPO=Path('/workspace/Sim2Act')
frozen=json.loads((REPO/'docs/evidence/project-column-versions-20261011/frozen-before.json').read_text());hashes={f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in frozen if f.startswith('src/')};assert all(hashes[f]==frozen[f] for f in hashes)
tmp=Path(tempfile.mkdtemp(prefix='ui-',dir=ROOT));g=fixture.__wrapped__(tmp);e=next(g)
try:
    vals,p,confirm,acceptance=start(e);work(e,acceptance);r=e[2].post(vals[0]+'/project-binding/finalize',json=confirm);assert r.status_code==201,r.text
    base=vals[0]+'/project-binding/internal-versions';r=e[2].post(base,json=dict(expected_receipt_fingerprint=r.json()['receipt_fingerprint'],request_key='project-binding'));assert r.status_code==201,r.text
    pv=r.json();approvals={v['approval']['id']:e[2].get('/api/internal/approvals/'+v['approval']['id']).json() for v in pv['entries']}
    info=tmp/'info.json';out=tmp/'result.json';info.write_text(json.dumps(dict(project=e[5],app=vals[2],peer=vals[3],unrelated=vals[4],base=base,web=str(REPO/'src/sim2act/web'),output=str(out),approvals=approvals)))
    variant=os.environ.get('INDEPENDENT_UI_EXTRA')
    proc=subprocess.Popen(['node',str(ROOT/('ui-final.js' if variant=='final' else 'ui-accepted.js' if variant=='accepted' else 'ui-extra.js' if variant else 'ui.js')),str(info)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=os.environ.copy())
    for line in proc.stdout:
        q=json.loads(line)
        if q.get('done'):break
        if q.get('command')=='worker':
            w=Worker(e[0],e[1],NoModel());count=0
            while job:=e[0].claim(w.id,e[1].lease_seconds):w.process(job);count+=1
            answer=dict(id=q['id'],status=200,text=json.dumps({'count':count}))
        elif q.get('command')=='grow':
            r=e[2].post(f'/api/projects/{e[5]}/apps/csv-preview',json=dict(name='independent later app',goal='unrelated project growth',resource_id=vals[5]));assert r.status_code==201,r.text;answer=dict(id=q['id'],status=200,text='{}')
        else:
            r=e[2].request(q['method'],q['path'],json=q.get('body'),headers=q.get('headers'));answer=dict(id=q['id'],status=r.status_code,text=r.text,content_type=r.headers.get('content-type'))
        proc.stdin.write(json.dumps(answer)+'\n');proc.stdin.flush()
    code=proc.wait(timeout=20);error=proc.stderr.read();(tmp/'stderr.log').write_text(error)
    result=json.loads(out.read_text());result['source_sha256']=hashes;result['source_sha256_after']={f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in hashes};assert result['source_sha256_after']==hashes
    prefix='ui-final' if variant=='final' else 'ui-accepted' if variant=='accepted' else 'ui-extra' if variant else 'ui'
    name=prefix+('-result.json' if code==0 else '-failure.json')
    (ROOT/name).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('UI',result['status'],'checks',len(result['checks']),'output',out);print(error)
    raise SystemExit(code)
finally:
    if 'proc' in globals() and proc.poll() is None:proc.kill();proc.wait(timeout=10)
    g.close()

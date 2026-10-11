import hashlib,json,os,subprocess,tempfile
from pathlib import Path
os.environ.pop('SIM2ACT_TEST_DATABASE_URL',None)
from conftest import env as fixture
from test_project_column_patches import setup
from test_csv_dag import NoModel
from sim2act.worker import Worker
root=Path('/tmp/project-column-independent');tmp=Path(tempfile.mkdtemp(prefix='ui-',dir=root));g=fixture.__wrapped__(tmp);e=next(g)
try:
    values=setup(e);info=tmp/'info.json';out=tmp/'result.json';info.write_text(json.dumps({'project':e[5],'app':values[2],'web':'/workspace/Sim2Act/src/sim2act/web','output':str(out)}))
    process=subprocess.Popen(['node',str(root/'ui.cjs'),str(info)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=os.environ.copy())
    for line in process.stdout:
        q=json.loads(line)
        if q.get('done'):break
        if q.get('command')=='worker':
            worker=Worker(e[0],e[1],NoModel());count=0
            while job:=e[0].claim(worker.id,e[1].lease_seconds):worker.process(job);count+=1
            assert count==4,count
            answer={'id':q['id'],'status':200,'text':'{}'}
        else:
            r=e[2].request(q['method'],q['path'],json=q.get('body'),headers=q.get('headers'));answer={'id':q['id'],'status':r.status_code,'text':r.text,'content_type':r.headers.get('content-type')}
        process.stdin.write(json.dumps(answer)+'\n');process.stdin.flush()
    code=process.wait(timeout=20);error=process.stderr.read();(tmp/'driver.log').write_text(error)
    result=json.loads(out.read_text());(root/('ui-pass.json' if code==0 else 'ui-fail.json')).write_text(json.dumps(result,indent=2))
    print('artifact',out,'exit',code,'checks',len(result['checks']));print(error)
    raise SystemExit(code)
finally:
    if 'process' in globals() and process.poll() is None:process.kill();process.wait(timeout=10)
    g.close()

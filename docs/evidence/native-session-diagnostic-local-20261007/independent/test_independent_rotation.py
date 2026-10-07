import json
import os
import subprocess
import sys
import time
from pathlib import Path
import httpx
import pytest
REPO=Path('/workspace/Sim2Act-native-session-diagnostic')
sys.path.insert(0,str(REPO/'scripts/protocol-ui'))
import rotation

@pytest.mark.parametrize('mode',['slow-stop','wrong-source-hash'])
def test_independent_no_ack_and_owned_collection(tmp_path,monkeypatch,mode):
    (tmp_path/'fresh').mkdir()
    info={'port':12345,'project':'fresh-p','source':'fresh-s','bearer':'synthetic','initial_counts':{}}
    for root in [tmp_path,tmp_path/'fresh']:
        (root/'info.json').write_text(json.dumps(info))
    real_spawn=subprocess.Popen
    old=real_spawn([sys.executable,'-c','import time;time.sleep(30)'])
    children=[];observations=[]
    def spawn(command,**kwargs):
        if '--action' in command:
            assert old.poll() is not None
            command=[sys.executable,'-c','import time;time.sleep(30)']
        proc=real_spawn(command,**kwargs);children.append(proc);return proc
    monkeypatch.setattr(rotation.subprocess,'Popen',spawn)
    monkeypatch.setattr(rotation,'snapshot',lambda root:{'tables':{}})
    real_stop=rotation.stop
    def stop(proc):
        if proc is old and mode=='slow-stop':
            time.sleep(.4)
            observations.append(children[0].poll())
        real_stop(proc)
    monkeypatch.setattr(rotation,'stop',stop)
    monkeypatch.setattr(rotation.httpx,'get',lambda url,**kwargs:httpx.Response(200,json=[{'id':'fresh-s','hash':'0'*64}] if url.endswith('/resources') else {'status':'ok'}))
    request=str(tmp_path/'fresh-request.json')
    code=f'from pathlib import Path;import time;Path({request!r}).write_text(\'{json.dumps({"action":"fresh-protocol-fixture.v1"})}\');time.sleep(30)'
    with pytest.raises(subprocess.TimeoutExpired if mode == 'slow-stop' else (subprocess.TimeoutExpired, RuntimeError)):
        rotation.run_node([sys.executable,'-c',code,sys.executable],old,tmp_path,REPO,os.environ.copy(),timeout=.2)
    assert all(p.poll() is not None for p in [old,*children])
    assert not (tmp_path/'fresh-response.json').exists()
    if mode=='slow-stop':
        assert observations and observations[0] is not None
        assert len(children)==1
    else:
        assert len(children)==2


def test_atomic_node_request_not_visible_before_complete(tmp_path):
    """Instrument the real Node transition publication, not a string assertion."""
    script=tmp_path/'probe.cjs'
    script.write_text('''const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=process.argv[2],req=path.join(root,'fresh-request.json');
const realWrite=fs.writeFileSync,realRename=fs.renameSync;let seen=0;
fs.writeFileSync=function(p,data,...args){if(p===req+'.tmp'){assert(!fs.existsSync(req));realWrite.call(fs,p,String(data).slice(0,5));assert(!fs.existsSync(req));seen++;}return realWrite.call(fs,p,data,...args);};
fs.renameSync=function(from,to){if(to===req){assert.equal(JSON.parse(fs.readFileSync(from)).action,'fresh-protocol-fixture.v1');seen++;}return realRename.call(fs,from,to);};
fs.mkdirSync(path.join(root,'fresh'));realWrite.call(fs,path.join(root,'fresh','info.json'),JSON.stringify({port:1}));
setTimeout(()=>{assert.equal(JSON.parse(fs.readFileSync(req)).action,'fresh-protocol-fixture.v1');realWrite.call(fs,path.join(root,'fresh-response.json'),JSON.stringify({namespace:'owned-protocol-api-transition.v1',status:'READY',old_api_joined:true,max_concurrent_protocol_servers:1,same_port:1}));},30);
require('/workspace/Sim2Act-native-session-diagnostic/scripts/browser-ci/protocol-transition.cjs')(root).then(()=>{assert.equal(seen,2);console.log('ATOMIC_REQUEST_PASS');}).catch(e=>{console.error(e);process.exitCode=1;});''')
    result=subprocess.run(['node',str(script),str(tmp_path)],capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr
    assert 'ATOMIC_REQUEST_PASS' in result.stdout

def test_atomic_ready_and_current_bearer_gate(tmp_path,monkeypatch):
    (tmp_path/'fresh').mkdir()
    info={'port':12345,'project':'fresh-p','source':'fresh-s','bearer':'synthetic-fresh','initial_counts':{}}
    for root in [tmp_path,tmp_path/'fresh']:
        (root/'info.json').write_text(json.dumps(info))
    real_spawn=subprocess.Popen;children=[];calls=[];writes=[]
    old=real_spawn([sys.executable,'-c','import time;time.sleep(30)'])
    def spawn(command,**kwargs):
        if '--action' in command:
            assert old.poll() is not None
            command=[sys.executable,'-c','import time;time.sleep(30)']
        proc=real_spawn(command,**kwargs);children.append(proc);return proc
    monkeypatch.setattr(rotation.subprocess,'Popen',spawn)
    monkeypatch.setattr(rotation,'snapshot',lambda root:{'tables':{}})
    def get(url,**kwargs):
        calls.append(url)
        if url.endswith('/resources'):
            assert '/api/projects/fresh-p/' in url
            assert kwargs['headers']=={'Authorization':'Bearer synthetic-fresh'}
            return httpx.Response(200,json=[{'id':'fresh-s','hash':rotation.SOURCE_HASH}])
        return httpx.Response(200,json={'status':'ok'})
    monkeypatch.setattr(rotation.httpx,'get',get)
    real_write=Path.write_text
    def write(path,data,*args,**kwargs):
        if path.name=='fresh-response.json.tmp':
            public=path.with_name('fresh-response.json')
            real_write(path,data[:4],*args,**kwargs)
            assert not public.exists()
            writes.append('partial-not-public')
        return real_write(path,data,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',write)
    req=str(tmp_path/'fresh-request.json');res=str(tmp_path/'fresh-response.json')
    code=f'from pathlib import Path;import time;Path({req!r}).write_text(\'{json.dumps({"action":"fresh-protocol-fixture.v1"})}\');\nwhile not Path({res!r}).exists(): time.sleep(.01)'
    rotation.run_node([sys.executable,'-c',code,sys.executable],old,tmp_path,REPO,os.environ.copy(),timeout=3)
    assert writes==['partial-not-public']
    assert json.loads((tmp_path/'fresh-response.json').read_text())['status']=='READY'
    assert len(calls)==2 and all(p.poll() is not None for p in [old,*children])

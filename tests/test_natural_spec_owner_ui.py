"""Actual HTTP/JSDOM gestures over successful normal Worker artifacts."""
import json
import os
import subprocess
from pathlib import Path
import pytest
from test_natural_spec_owner_acceptance import flow

@pytest.mark.parametrize('family,scenario',[('pa','accept'),('pb','reject'),('pb','decision-lost')])
def test_visible_natural_owner(env,tmp_path,family,scenario):
    data,inst,rid,resource,goal,content,path=flow(env,family)
    app=data[2].get('/api/apps/'+inst['source_app_id']).json()
    info=dict(project=data[4],name=app['name'],run=rid,goal=goal['id'],content=content,
        scenario=scenario,output=str(tmp_path/'result.json'))
    p=tmp_path/'info.json';p.write_text(json.dumps(info))
    stderr=tmp_path/'node.stderr'
    with stderr.open('w') as err:
        process=subprocess.Popen(['node','tests/natural_spec_owner_ui.cjs',str(p)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=err,text=True,env={**os.environ,'NODE_PATH':'/workspace/node-tools/node_modules'})
        try:
            for line in process.stdout:
                request=json.loads(line)
                if request.get('done'):break
                response=data[2].request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
                process.stdin.write(json.dumps(dict(id=request['id'],status=response.status_code,
                    text=response.text,content_type=response.headers.get('content-type')))+'\n');process.stdin.flush()
            process.stdin.close();code=process.wait(timeout=20)
            assert code==0,stderr.read_text()
            proof=json.loads((tmp_path/'result.json').read_text());assert proof['status']=='PASS'
            assert len(proof['actions'])>20 and len(proof['checks'])>15
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)

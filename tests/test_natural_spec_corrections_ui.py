import json
import os
import subprocess
from pathlib import Path
import pytest
from test_natural_spec_corrections import rejected
from test_natural_spec_apps import transport
from test_pb_natural_specs import drive_to_success

@pytest.mark.parametrize('family,scenario',[('pa','normal'),('pb','run-lost')])
def test_visible_rejection_correction_and_independent_owner(env,tmp_path,family,scenario):
    data,inst,rid,_,goal,content,_,_,_=rejected(env,family)
    app=data[2].get('/api/apps/'+inst['source_app_id']).json()
    info=dict(project=data[4],name=app['name'],run=rid,goal_text=goal['content']['goal'],scenario=scenario,output=str(tmp_path/'result.json'))
    path=tmp_path/'info.json';path.write_text(json.dumps(info))
    stderr=tmp_path/'node.stderr';worked=[]
    with stderr.open('w') as err:
        process=subprocess.Popen(['node','tests/natural_spec_corrections_ui.cjs',str(path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,
            env={**os.environ,'NODE_PATH':'/workspace/node-tools/node_modules'})
        try:
            for line in process.stdout:
                request=json.loads(line)
                if request.get('done'):break
                if request.get('command')=='worker':
                    drive_to_success(data,request['rid'],transport([],content));worked.append(request['rid'])
                    answer=dict(id=request['id'],status=200,text='{}')
                else:
                    response=data[2].request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
                    answer=dict(id=request['id'],status=response.status_code,text=response.text,content_type=response.headers.get('content-type'))
                process.stdin.write(json.dumps(answer)+'\n');process.stdin.flush()
            process.stdin.close();code=process.wait(timeout=20)
            assert code==0,stderr.read_text()
            proof=json.loads((tmp_path/'result.json').read_text());assert proof['status']=='PASS'
            assert len(worked)==1 and len(proof['checks'])>20
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)

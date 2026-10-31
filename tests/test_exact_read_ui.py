"""Served task UI + real ASGI persistence; synthetic model, no native browser."""

import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import select
from test_exact_read import ExactModel

from sim2act.db import attempts, runs
from sim2act.worker import Worker


def test_normal_ui_finite_selection_unknown_recovery_and_actual_goal(env, tmp_path):
    store, settings, client, user, other_user, project, _ = env
    other=store.project(user,'Other synthetic project')
    store.project(other_user,'Other synthetic identity')
    material=[]
    for name,format,content in [('table.csv','csv','n\n1\n'),('finite.txt','txt','Keep this exact text.\n保留换行。\n'),
                               ('notes.md','md','# Synthetic\n'),('data.json','json','{"n":1}')]:
        r=client.post(f'/api/projects/{project}/resources',json={'name':name,'format':format,'content':content})
        assert r.status_code==201
        material.append({'id':r.json()['id'],'name':name,'format':format,'content':content})
    info=tmp_path/'info.json';output=tmp_path/'result.json'
    info.write_text(json.dumps({'case':'exact','project':project,'other':other,'materials':material,'output':str(output)}))
    process=None;worked=0
    try:
        with (tmp_path/'node.stderr').open('w') as errors:
            process=subprocess.Popen(['node','tests/ordinary_run_materials.cjs',str(info)],stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,stderr=errors,text=True,
                env={**os.environ,'NODE_PATH':os.environ.get('NODE_PATH',str(Path.cwd()/'scripts/engineering-ci/node_modules'))})
            for line in process.stdout:
                request=json.loads(line)
                if request.get('done'):break
                if request.get('command')=='worker':
                    model=ExactModel();assert Worker(store,settings,model).once();worked+=1
                    assert model.calls==2
                    answer={'status':200,'text':'{}'}
                elif request.get('command')=='verify':
                    with store.engine.connect() as c:
                        rows=c.execute(select(runs)).mappings().all()
                        assert len(rows)==1 and rows[0]['status']=='SUCCEEDED'
                        assert len(c.execute(select(attempts)).all())==2
                    assert worked==1
                    answer={'status':200,'text':'{}'}
                else:
                    r=client.request(request['method'],request['path'],json=request.get('body'),headers=request.get('headers'))
                    answer={'status':r.status_code,'text':r.text,'content_type':r.headers.get('content-type')}
                process.stdin.write(json.dumps({'id':request['id'],**answer})+'\n');process.stdin.flush()
            process.stdin.close();code=process.wait(timeout=20)
        assert code==0,(tmp_path/'node.stderr').read_text()
        assert json.loads(output.read_text())['status']=='PASS'
    finally:
        if process is not None and process.poll() is None:
            process.terminate();process.wait(timeout=10)

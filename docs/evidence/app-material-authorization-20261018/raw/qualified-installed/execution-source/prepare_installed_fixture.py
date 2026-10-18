"""API-prepared original App/A plus existing B with ZERO App/B grants.
No SQL Grant write, Worker, model or previous revision.
"""
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sim2act.db import grants
from sim2act.synthetic_workspace import TOKEN, open_workspace, settings_for, workspace_app

ROOT = Path('/workspace/app-material-authorization-20261018/qualified-installed')
DATA = ROOT / 'App材料 显式授权'
root,store,marker = open_workspace(DATA,new=True)
trace=[]

def save():
    (ROOT/'fixture-http.json').write_text(json.dumps(trace,ensure_ascii=False,indent=2)+'\n')

try:
    with TestClient(workspace_app(store,settings_for(root)))as client:
        client.headers.update({'Authorization':'Bearer '+TOKEN})
        def call(method,path,body=None,status=201):
            response=client.request(method,path,**({'json':body}if body is not None else{}))
            value=response.json();trace.append(dict(method=method,path=path,body=body,status=response.status_code,response=value));save();assert response.status_code==status,value;return value
        pid=call('POST','/api/projects',{'name':'首次直接换 CSV 合成工程'})['id']
        A='item,amount,quantity\nA,10,2\nB,20,3\n';B='item,amount,quantity\nC,100,7\nD,250,8\n'
        aid_resource=call('POST',f'/api/projects/{pid}/resources',dict(name='old-A.csv',format='csv',content=A))['id']
        bid=call('POST',f'/api/projects/{pid}/resources',dict(name='new-ungranted-B.csv',format='csv',content=B))['id']
        goal=dict(title='明确选择已授权CSV的列求和',goal='对明确选择的已有授权CSV数值列求和并报告记录数，保留各次历史',known=['两条合成记录'],assumptions=['用户核对材料与列的含义'],unresolved=['真实语义与人工签收未执行'],constraints=['无模型、无自动授权、无正式发布'],acceptance_checks=['精确求和所选数值列和两条记录'],resource_refs=[aid_resource])
        card=call('POST',f'/api/projects/{pid}/goal-cards',goal)
        app=call('POST',f"/api/goal-cards/{card['id']}/candidates",dict(expected_version=1,resource_id=aid_resource,capability='csv.sum',request_key='original-A-candidate'))
        draft=call('GET','/api/apps/'+app['id'],status=200)
        # The actual product UI must grant B: no fixture App/B Grant insertion.
        with store.tx()as c:
            existing=[dict(r)for r in c.execute(select(grants).where(grants.c.principal_id==draft['runtime_id'],grants.c.resource_id==bid)).mappings()]
            assert existing==[]
        approval=call('POST',f"/api/internal/apps/{app['id']}/release-approvals",dict(expected_draft_fingerprint=draft['fingerprint'],sample_input={'column':'amount'}))
        release=call('POST',f"/api/internal/approvals/{approval['id']}/commit",dict(fingerprint=approval['fingerprint']),status=200)
        inst=call('POST',f"/api/internal/releases/{release['id']}/instances",dict(expected_release_fingerprint=release['fingerprint'],request_key='original-business-instance'))
        assert inst['revision']==1 and inst['data_version']==0 and 'csv_goal_revision_source'not in release['snapshot']
        value=dict(scope='API prepared original fixture, ZERO App/B Grants; explicit business authorization is measured product behavior, no previous column revision or adoption or Run',project_id=pid,resource_id=aid_resource,B_id=bid,A_hash=hashlib.sha256(A.encode()).hexdigest(),B_hash=hashlib.sha256(B.encode()).hexdigest(),app_id=app['id'],instance_id=inst['id'],old_release_id=release['id'],goal=draft['candidate']['generation'],fixture_App_B_grants=0,initial_instance=inst,original_release=release,principal_id=marker['principal_id'])
        (ROOT/'fixture.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(dict(status='FIXTURE_READY',scope=value['scope'],instance_id=inst['id'],fixture_App_B_grants=0),ensure_ascii=False))
finally:store.engine.dispose()

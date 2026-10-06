import copy
from test_bounded_agent_apps import setup, limits, replay
from test_agent_ui_replay import body_for
from sim2act import app_jobs as jobs
from sim2act.agent_apps import offline_replay_model
from sim2act.worker import Worker

def test_frozen_replay_transcript_rebinding(env):
    _, ids, _, _, _, rel, inst, value = setup(env)
    body = body_for(env, inst, rel, ids[0], value)
    queued = env[2].post(f"/api/internal/instances/{inst['id']}/runs",json=body).json()
    w=Worker(env[0],env[1])
    run=env[0].claim(w.id,30)
    assert run['id']==queued['run_id']
    plan=jobs.prepare_dispatch(w,run)
    altered=copy.deepcopy(plan['offline_replay'])
    altered[0]['choices'][0]['message']['tool_calls'][0]['id']='changed-after-acceptance'
    output=jobs.compute(plan,offline_replay_model(altered),lambda _:plan['source'])
    jobs.commit_result(w,run,plan,output)
    result=env[2].get(f"/api/internal/instances/{inst['id']}/runs/{run['id']}")
    print('INDEPENDENT_ALTERNATE_FROZEN_TRANSCRIPT',result.status_code,result.json()['status'])
    assert result.json()['status']=='SUCCEEDED'

def test_frozen_replay_numeric_plan_comparison(env):
    _, ids, _, _, _, rel, inst, value = setup(env)
    body = body_for(env, inst, rel, ids[0], value)
    body['offline_replay'][0]['created']=1
    queued=env[2].post(f"/api/internal/instances/{inst['id']}/runs",json=body).json()
    w=Worker(env[0],env[1]);run=env[0].claim(w.id,30)
    plan=jobs.prepare_dispatch(w,run)
    plan['offline_replay'][0]['created']=True
    output=jobs.compute(plan,offline_replay_model(plan['offline_replay']),lambda _:plan['source'])
    jobs.commit_result(w,run,plan,output)
    result=env[2].get(f"/api/internal/instances/{inst['id']}/runs/{run['id']}")
    print('INDEPENDENT_NUMERIC_FROZEN_PLAN',result.status_code,result.json()['status'])
    assert result.json()['status']=='SUCCEEDED'

"""Explicit owned PG migration, CRUD-role dual fixture and bounded LIVE execution.
No credentials logged/persisted: normal settings and child environment handle access.
prepare performs zero provider calls; execute is single-use, never automatic retry.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, attempts, grants, operations, principals, projects, resources, runs, reservations, quotas, events
from sim2act.errors import DomainError
from sim2act.process_env import application_environment
from send_guard import Guard

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
CONTAINER = 'sim2act-at02-live-20261006'
PYTHON = sys.executable
TOKENS = ['synthetic-dual-live-A', 'synthetic-dual-live-B']  # fixture auth only

def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str)+'\n')

def read(name):
    return json.loads((OUT/name).read_text())

def snapshot(store):
    with store.tx() as c:
        result = {t.name:[dict(x) for x in c.execute(select(t)).mappings()] for t in [principals,projects,grants,resources,runs,attempts,operations,reservations,quotas,events]}
    for p in result['principals']:
        p.pop('token_hash',None)
    return result

def settings(url, root):
    # Standard app config only; do not inspect the token value or dump settings/env.
    os.environ['SIM2ACT_DATABASE_URL']=url
    os.environ['SIM2ACT_DATA_DIR']=str(root)
    s=replace(Settings.from_env(), database_url=url, data_dir=Path(root), mode='live',live_enabled=True,model='intern-s2',rpm=10,max_requests=2,max_tools=1,max_repairs=0,max_total_tokens=5000,max_output_tokens=512,run_seconds=300)
    assert bool(s.token), 'Normal configured model access unavailable'
    return s

def prepare():
    assert not (OUT/'wire.json').exists(), 'Existing durable authorization ledger must never be reset'
    root=Path(tempfile.mkdtemp(prefix='sim2act-at02-dual-live-'))
    owner_url='postgresql+psycopg://postgres:synthetic-at02-owner-only@127.0.0.1:32769/at02_dual'
    app_url='postgresql+psycopg://at02_app:synthetic-at02-crud-only@127.0.0.1:32769/at02_dual'
    owner=Store(owner_url)
    owner.initialize()  # Explicit owned migration, never API/worker DDL.
    users=[owner.user('synthetic '+label,TOKENS[n]) for n,label in enumerate(['A','B'])]
    with owner.tx() as c:
        c.exec_driver_sql("CREATE ROLE at02_app LOGIN PASSWORD 'synthetic-at02-crud-only' NOSUPERUSER NOCREATEDB NOCREATEROLE")
        c.exec_driver_sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
        c.exec_driver_sql('GRANT USAGE ON SCHEMA public TO at02_app')
        c.exec_driver_sql('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO at02_app')
    owner.engine.dispose()
    store=Store(app_url);s=settings(app_url,root)
    checks=[]
    def check(name,condition):
        assert condition,name
        checks.append(name)
    with store.engine.connect() as c:
        flags=dict(c.exec_driver_sql("SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user").mappings().one())
        check('minimum-role non-superuser/no createDB/no createRole',not any(flags.values()))
        try:c.exec_driver_sql('CREATE TABLE forbidden_at02_probe(id integer)')
        except Exception as e:
            check('minimum-role schema DDL denied',getattr(getattr(e,'orig',None),'sqlstate',None)=='42501')
            c.rollback()
        else:raise AssertionError('Application role can create table')
    groups=[]
    with TestClient(create_app(store,s)) as client:
        for n,label in enumerate(['A','B']):
            client.headers['Authorization']='Bearer '+TOKENS[n]
            p=client.post('/api/projects',json={'name':'synthetic '+label});check('create owned project '+label,p.status_code==201)
            pid=p.json()['id']
            r=client.post(f'/api/projects/{pid}/resources',json={'name':'value.txt','format':'txt','content':'42' if n==0 else '84'});check('create owned resource '+label,r.status_code==201)
            groups.append({'label':label,'owner_id':users[n],'project_id':pid,'resource_id':r.json()['id'],'expected_answer':'42' if n==0 else '84'})
        with store.tx() as c:
            c.execute(update(grants).where(grants.c.tool_ref!='resource.read').values(revoked=True))
            for g in groups:g['runtime_id']=c.execute(select(projects.c.runtime_id).where(projects.c.id==g['project_id'])).scalar_one()
        start=snapshot(store)
        check('two owners/two projects/two distinct runtime identities',len(start['principals'])==4 and len({g['owner_id'] for g in groups}|{g['runtime_id'] for g in groups})==4)
        active=[g for g in start['grants'] if not g['revoked']]
        check('only four own owner/runtime read grants',len(active)==4 and all(x['tool_ref']=='resource.read' and any(x['project_id']==g['project_id'] and x['resource_id']==g['resource_id'] and x['principal_id'] in [g['owner_id'],g['runtime_id']] for g in groups) for x in active))
        negatives=[]
        for n,g in enumerate(groups):
            other=groups[1-n];client.headers['Authorization']='Bearer '+TOKENS[n]
            for method,url,body in [('GET','/api/resources/'+other['resource_id'],None),('GET',f"/api/projects/{other['project_id']}/runs",None),('POST',f"/api/projects/{other['project_id']}/runs",{'goal':'Read; echo.','resource_refs':[other['resource_id']],'request_key':'denied-owner'}),('POST',f"/api/projects/{g['project_id']}/runs",{'goal':'Read; echo.','resource_refs':[other['resource_id']],'request_key':'denied-resource'})]:
                r=client.request(method,url,**({'json':body} if body else {}));negatives.append({'group':g['label'],'method':method,'url':url,'status':r.status_code})
                check('cross-scope negative '+g['label']+' '+url,r.status_code==403 and '"content"' not in r.text)
            check('own resource readable '+g['label'],client.get('/api/resources/'+g['resource_id']).json()['content']==g['expected_answer'])
            with store.tx() as c:
                try:store.authorize(c,g['owner_id'],other['runtime_id'],g['project_id'],g['resource_id'],'resource.read')
                except DomainError:checks.append('foreign runtime rejected '+g['label'])
                else:raise AssertionError('Foreign runtime accepted')
        for who in [groups[0]['owner_id'],groups[0]['runtime_id']]:
            with store.tx() as c:
                c.execute(update(grants).where(grants.c.principal_id==who,grants.c.tool_ref=='resource.read').values(revoked=True))
                try:store.authorize(c,groups[0]['owner_id'],groups[0]['runtime_id'],groups[0]['project_id'],groups[0]['resource_id'],'resource.read')
                except DomainError as e:check('revoked intersection rejected '+who,e.code=='GRANT_REVOKED')
                else:raise AssertionError('Revoked grant accepted')
                c.rollback()
        check('preflight no runs/attempts/operations/reservations',all(not start[t] for t in ['runs','attempts','operations','reservations']))
    store.engine.dispose()
    # Only synthetic DB credentials in private owned config; never real model credentials.
    (root/'config.json').write_text(json.dumps({'database_url':app_url}))
    save('fixture.json',{'groups':groups})
    Guard(OUT).save({'authorization':'at most four new Intern requests, output<=512 each, synthetic dual fixture only; no automatic retries','requests':[],'blocked':[],'halted':False})
    save('state.json',{'root':str(root),'phase':'PREPARED_ZERO_SENDS','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()})
    save('preflight.json',{'status':'PASS','external_requests':0,'checks':checks,'minimum_role_flags':flags,'starting_fixture':start,'negative_http':negatives,'live_budget_total':4,'per_request_output_cap':512,'per_run_request_cap':2,'repairs':0,'full_body_character_cap':2000,'minimum_seconds_since_previous_response':6,'model':'intern-s2','access':'normal configured application; credential value never inspected or persisted'})
    print(json.dumps({'preflight':'PASS','checks':len(checks),'external_requests':0,'phase':'PREPARED_ZERO_SENDS'}))

def execute():
    state=read('state.json');assert state['phase']=='PREPARED_ZERO_SENDS','Single-use controller; never restart an executed case'
    wire=read('wire.json');assert not wire['requests'] and not wire['halted']
    state['phase']='EXECUTING_SINGLE_USE';save('state.json',state)
    root=Path(state['root']);url=json.loads((root/'config.json').read_text())['database_url'];s=settings(url,root)
    store=Store(url);groups=read('fixture.json')['groups'];start=read('preflight.json')['starting_fixture']
    report={'status':'IN_PROGRESS','checks':[],'group_results':[],'source_commit':state['source_commit'],'limits':{'total_requests':4,'max_tokens':512,'request_cap_per_run':2,'tools_per_run':1,'repairs':0,'complete_body_characters':2000,'separation_seconds':6},'formal_F1_signoff':False,'weight_version':'unknown','processes':[]}
    def check(name,condition):
        assert condition,name
        report['checks'].append(name)
    api=None;logs=[]
    try:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        api_log=(root/'api.log').open('w');logs.append(api_log)
        api=subprocess.Popen([PYTHON,str(OUT/'api_entry.py'),str(port)],cwd=REPO,env=application_environment(s),stdout=api_log,stderr=api_log)
        report['processes'].append({'kind':'independent API','pid':api.pid,'port':port,'role':'CRUD-only','DDL':False})
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=15,trust_env=False) as client:
            for _ in range(100):
                if api.poll() is not None:raise AssertionError('Owned API exited before readiness')
                try:
                    if client.get('/health').status_code==200:break
                except httpx.ConnectError:pass
                time.sleep(.1)
            else:raise AssertionError('Owned API readiness timeout')
            check('independent API ready with owned CRUD database',client.get('/health').json()['mode']=='LIVE')
            for n,g in enumerate(groups):
                client.headers['Authorization']='Bearer '+TOKENS[n]
                accepted=client.post(f"/api/projects/{g['project_id']}/runs",json={'goal':'Read; echo.','resource_refs':[g['resource_id']],'request_key':'dual-live-'+g['label']})
                check('one accepted intent '+g['label'],accepted.status_code==202)
                run_id=accepted.json()['run_id'];g['run_id']=run_id
                worker_log=(root/('worker-'+g['label']+'.log')).open('w');logs.append(worker_log)
                worker=subprocess.Popen([PYTHON,str(OUT/'worker_entry.py'),str(OUT)],cwd=REPO,env=application_environment(s),stdout=worker_log,stderr=worker_log)
                record={'kind':'independent one-shot worker','group':g['label'],'pid':worker.pid,'role':'CRUD-only','DDL':False};report['processes'].append(record)
                try:record['returncode']=worker.wait(timeout=310)
                except subprocess.TimeoutExpired:
                    worker.terminate()
                    try:worker.wait(timeout=10)
                    except subprocess.TimeoutExpired:worker.kill();worker.wait(timeout=5)
                    record['returncode']=worker.returncode
                    raise AssertionError('Owned worker deadline exceeded; no retry')
                check('one-shot worker exits '+g['label'],record['returncode']==0)
                result=client.get('/api/runs/'+run_id).json();report['group_results'].append({'group':g['label'],'run_id':run_id,'readback':result})
                trace=snapshot(store);report['final_trace']=trace
                aa=[x for x in trace['attempts'] if x['run_id']==run_id];oo=[x for x in trace['operations'] if x['run_id']==run_id]
                check('actual two-round PARTIAL answer and verified receipt '+g['label'],result['status']=='PARTIAL' and result['result']['answer'].strip()==g['expected_answer'] and len(aa)==2 and all(x['status']=='RECEIVED' and x['mode']=='LIVE' and x['parameters']['model_identity']['enforced'] and x['parameters']['model_identity']['verdict']=='ACCEPTED' for x in aa) and len(oo)==1 and oo[0]['status']=='VERIFIED')
                ownrun=next(x for x in trace['runs'] if x['id']==run_id);messages=ownrun['context']['messages']
                check('tool feedback persisted before second request '+g['label'],[m['role'] for m in messages]==['system','user','assistant','tool','assistant'])
                check('other group reference absent from own entire context '+g['label'],groups[1-n]['resource_id'] not in json.dumps(messages))
                cold=Store(url)
                check('cold-store persistent result '+g['label'],cold.inspect(g['owner_id'],run_id)['result']['answer'].strip()==g['expected_answer']);cold.engine.dispose()
                client.headers['Authorization']='Bearer '+TOKENS[1-n]
                check('other owner denied completed run '+g['label'],client.get('/api/runs/'+run_id).status_code==403)
                check('other owner denied completed history '+g['label'],client.get(f"/api/projects/{g['project_id']}/runs").status_code==403)
                save('results-progress.json',report)
                check('wire ledger healthy after group '+g['label'],not read('wire.json')['halted'])
            final=snapshot(store);report['final_trace']=final;wire=read('wire.json')
            check('exactly four sends across same shared durable guard',len(wire['requests'])==4 and [x['group'] for x in wire['requests']]==['A','A','B','B'])
            check('all actual shapes bounded and separated',all(x['max_tokens']==512 and x['input_characters']<=2000 and (x['seconds_since_previous_response'] is None or x['seconds_since_previous_response']>=6) for x in wire['requests']))
            check('grants unchanged from starting fixture',final['grants']==start['grants'])
            check('both synthetic resources unchanged',final['resources']==start['resources'])
            check('same account quota, four reservations',len(final['quotas'])==1 and len(final['reservations'])==4 and len({x['subject'] for x in final['reservations']})==1)
            for n,g in enumerate(groups):
                client.headers['Authorization']='Bearer '+TOKENS[n]
                check('own resource still readable '+g['label'],client.get('/api/resources/'+g['resource_id']).json()['content']==g['expected_answer'])
            report['status']='PASS_BOUNDED_DUAL_LIVE_SLICE'
    except BaseException as error:
        report['status']='FAILED_PRESERVED_NO_RETRY'
        report['failure']={'type':type(error).__name__,'check':str(error) if isinstance(error,AssertionError) else 'Exception details withheld; inspect safe trace/error codes'}
        report['final_trace']=snapshot(store)
        guard=Guard(OUT);wire=read('wire.json');wire['halted']=True;guard.save(wire)
    finally:
        if api and api.poll() is None:
            api.terminate()
            try:api.wait(timeout=10)
            except subprocess.TimeoutExpired:api.kill();api.wait(timeout=5)
        for log in logs:log.close()
        store.engine.dispose()
        report['wire']=read('wire.json')
        report['actual_send_slots']=len(report['wire']['requests'])
        report['unused_authorized_slots']=4-report['actual_send_slots']
        report['usage']=[{'sequence':x['sequence'],'group':x['group'],'usage':x['usage']} for x in report['wire']['requests']]
        # Only this task's explicitly named disposable container and private directory.
        stopped=subprocess.run(['docker','stop',CONTAINER],capture_output=True).returncode==0
        removed=subprocess.run(['docker','rm',CONTAINER],capture_output=True).returncode==0
        shutil.rmtree(root)
        exists=subprocess.run(['docker','inspect',CONTAINER],capture_output=True).returncode==0
        report['cleanup']={'api_exited':api is None or api.poll() is not None,'container_stopped':stopped,'container_removed':removed and not exists,'owned_temp_removed':not root.exists(),'worker_returncodes':[p.get('returncode') for p in report['processes'] if p['kind']=='independent one-shot worker']}
        state['phase']='COMPLETE_NO_REEXECUTION';save('state.json',state);save('results.json',report)
        print(json.dumps({'status':report['status'],'send_slots':report['actual_send_slots'],'unused':report['unused_authorized_slots'],'checks':len(report['checks']),'cleanup':report['cleanup']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','execute']);args=parser.parse_args()
    prepare() if args.phase=='prepare' else execute()

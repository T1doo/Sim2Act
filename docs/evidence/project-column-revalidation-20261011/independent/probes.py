import copy, hashlib, json, os, tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
os.environ.pop('SIM2ACT_TEST_DATABASE_URL', None)
from conftest import env as fixture
from test_project_column_patches import start, work
from test_delivery_graph_apps import snapshot
from test_internal_lifecycle import limits
from sim2act import project_column_patches as p
from sim2act.db import delivery_graph_requests as reqs, runs, grants, fingerprint
from sim2act.errors import DomainError
from sqlalchemy import select, update
ROOT=Path('/tmp/project-column-independent')
source=Path('/workspace/Sim2Act/src/sim2act/project_column_patches.py')
result={'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'checks': []}
@contextmanager
def env():
    d=Path(tempfile.mkdtemp(prefix='ind-', dir=ROOT))
    g=fixture.__wrapped__(d)
    e=next(g)
    try: yield e
    finally: g.close()
def check(name, response, before, e):
    assert response.status_code in (400,403,409), (name,response.status_code,response.text)
    assert snapshot(e)==before, name+' changed DB'
    result['checks'].append({'name':name,'status':'PASS','http_status':response.status_code,'error':response.json()['error']['code'],'no_partial_changes':True})
with env() as e:
    vals, candidate, body, accepted = start(e)
    work(e, accepted)
    before=snapshot(e)
    deadline=min(j['deadline'] for j in accepted['jobs'])
    with patch('sim2act.project_column_patches.time.time', lambda:deadline):
        r=e[2].post(vals[0]+'/project-binding/finalize',json=body)
    check('exact immutable deadline rejects',r,before,e)
    r=e[2].get(vals[0]+'/project-binding')
    assert r.status_code==200 and r.json()['checks_status']=='PASS'
    assert snapshot(e)==before
    result['checks'].append({'name':'four actual jobs and read-only oracle recover','status':'PASS','workers':len(accepted['jobs']),'outputs':[(j['phase'],j['proof']['result']['output']['sum']) for j in r.json()['jobs']]})
    with e[0].tx() as c:
        rid=accepted['jobs'][0]['run_id']
        row=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
        c.execute(update(runs).where(runs.c.id==rid).values(created_at=row['created_at']+10000))
    before=snapshot(e)
    check('mutable Run time cannot extend frozen deadline',e[2].post(vals[0]+'/project-binding/finalize',json=body),before,e)
with env() as e:
    vals, candidate, body, accepted=start(e);work(e,accepted)
    original=p.save_pair
    def revoked(c,user,aid,kind,key,b,value):
        original(c,user,aid,kind,key,b,value)
        if kind==p.FINISH:
            c.execute(update(grants).where(grants.c.resource_id==vals[5]).values(expires_at=0))
    before=snapshot(e)
    with patch.object(p,'save_pair',revoked):r=e[2].post(vals[0]+'/project-binding/finalize',json=body)
    check('authority expires after receipt insert before commit',r,before,e)
with env() as e:
    vals,candidate,body,accepted=start(e);work(e,accepted)
    r=e[2].post(vals[0]+'/project-binding/finalize',json=body)
    assert r.status_code==201,r.text
    with e[0].tx() as c:
        for row in c.execute(select(reqs).where(reqs.c.kind.in_([p.FINISH,p.FINISH+'_seal']))).mappings().all():
            value=copy.deepcopy(row['snapshot']);value['response']['finite_revalidation_completed']=1
            c.execute(update(reqs).where(reqs.c.app_id==row['app_id'],reqs.c.principal_id==row['principal_id'],reqs.c.kind==row['kind'],reqs.c.request_key==row['request_key']).values(snapshot=value,fingerprint=fingerprint(value)))
    before=snapshot(e)
    check('re-signed bool-int final seal corruption rejects',e[2].get(vals[0]+'/project-binding'),before,e)
with env() as e:
    vals,candidate,body,accepted=start(e);work(e,accepted)
    original=p.save_pair
    clock=[p.time.time()]
    deadline=min(j['deadline'] for j in accepted['jobs'])
    def elapsed(c,user,aid,kind,key,b,value):
        original(c,user,aid,kind,key,b,value)
        if kind==p.FINISH:clock[0]=deadline
    before=snapshot(e)
    with patch('sim2act.project_column_patches.time.time',lambda:clock[0]),patch.object(p,'save_pair',elapsed):
        r=e[2].post(vals[0]+'/project-binding/finalize',json=body)
    check('deadline reached after final receipt insert rolls back',r,before,e)
with env() as e:
    vals,candidate,body,accepted=start(e)
    rid=accepted['jobs'][0]['run_id']
    r=e[2].post('/api/runs/'+rid+'/commands',json={'command':'cancel','version':1})
    assert r.status_code==200,r.text
    before=snapshot(e)
    check('real queued cancellation forbids project finalize',e[2].post(vals[0]+'/project-binding/finalize',json=body),before,e)
with env() as e:
    vals,candidate,body,accepted=start(e)
    aid=vals[2]
    with e[0].tx() as c:
        saved=p.graph.current(e[0],c,e[3],e[5],aid,limits(e))
        _,manifest,action,*_=p.graph.load_family(e[0],c,e[3],e[5],aid,limits(e))
    for attack in ['SEMANTIC','MODEL_CANDIDATE','unknown_APP_reason','extra_unknown']:
        bad=copy.deepcopy(saved)
        if attack=='SEMANTIC':bad['graph']['edges'][0]['type']='SEMANTIC'
        elif attack=='MODEL_CANDIDATE':bad['graph']['edges'][0]['provenance']='MODEL_CANDIDATE'
        elif attack=='unknown_APP_reason':bad['graph']['unknown_dependencies'][0]['reason']='opaque dependency'
        else:bad['graph']['unknown_dependencies'].append({'node_id':aid,'scope':'APP','reason':'opaque'})
        try:p.finite(bad,manifest,action)
        except DomainError as exc:
            assert exc.code=='UNSUPPORTED_CAPABILITY'
            result['checks'].append({'name':'finite fail-closed '+attack,'status':'PASS','error':exc.code})
        else:raise AssertionError(attack)
result['source_sha256_after']=hashlib.sha256(source.read_bytes()).hexdigest()
result['status']='PASS'
(ROOT/'backend-probes.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

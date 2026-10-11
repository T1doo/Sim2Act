import pytest
from sqlalchemy import update,select
from conftest import env
from test_csv_dag_instances import release,create,enqueue
from test_delivery_graph_apps import snapshot
from sim2act.db import internal_instances,internal_instance_data,fingerprint,runs,internal_app_runs

def test_revision_aba_control_reads_and_cancel_without_protected_content_or_write(env):
    _,_,_,_,rel=release(env)
    i=create(env,rel)
    accepted,_=enqueue(env,i,rel)
    with env[0].tx() as c:
        c.execute(update(internal_instances).where(internal_instances.c.id==i['id']).values(revision=3))
    before=fingerprint(snapshot(env))
    metadata=env[2].get(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}/control-status")
    assert metadata.status_code==200,metadata.text
    assert metadata.json()['content_access'] is False
    assert 'input' not in metadata.json() and 'result' not in metadata.json() and 'output' not in metadata.json()
    protected=env[2].get(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}")
    assert protected.status_code==409,protected.text
    assert fingerprint(snapshot(env))==before
    cancelled=env[2].post(f"/api/internal/instances/{i['id']}/runs/{accepted['run_id']}/commands",json={'command':'cancel','version':accepted['version']})
    assert cancelled.status_code==200,cancelled.text
    with env[0].tx() as c:
        job=c.execute(select(runs).where(runs.c.id==accepted['run_id'])).mappings().one()
        ar=c.execute(select(internal_app_runs).where(internal_app_runs.c.id==accepted['app_run_id'])).mappings().one()
        assert job['status']=='CANCELLED' and job['result'] is None
        assert ar['status']=='CANCELLED' and ar['output'] is None and ar['result_version'] is None
        assert not c.execute(select(internal_instance_data).where(internal_instance_data.c.instance_id==i['id'])).first()

import pytest
from conftest import env as original_env
from test_conditional_run_bindings import env as bounded_env
from test_report_presentations import prepared
from test_delivery_graph_apps import snapshot

@pytest.fixture
def env(tmp_path):
    generator=original_env.__wrapped__(tmp_path)
    try: yield bounded_env.__wrapped__(next(generator))
    finally: generator.close()

def test_old_real_project_scope_has_no_public_deterministic_check_routes(env,tmp_path):
    _,_,url,_,_,wires=prepared(env,tmp_path,peer=True)
    base=url.removesuffix('report-presentations')+'scope-checks'
    before=snapshot(env)
    for response in (env[2].get(base+'/options',params={'plan_key':'presentation-plan'}),env[2].post(base,json={'request_key':'old-negative'}),env[2].get(base,params={'plan_key':'presentation-plan'})):
        assert response.status_code==404,response.text
    assert snapshot(env)==before and len(wires)==4

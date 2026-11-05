"""Adapter/wire budget identity, with no provider/network or authority overrides."""
from dataclasses import replace
from types import SimpleNamespace
import httpx,pytest
from sim2act.goal_applications import _generation_provider
from sim2act.errors import DomainError
from test_natural_trial_preparation import prepared_data,scope


def test_each_generation_adapter_matches_requested_budget_without_changing_worker(env):
    settings=env[1]
    transport=httpx.MockTransport(lambda request:httpx.Response(200,json={}))
    worker=SimpleNamespace(s=settings,goal_planner_transport=transport,store=SimpleNamespace(test_only=True))
    first=_generation_provider(worker,1024);candidate=_generation_provider(worker,4096)
    assert worker.s is settings and settings.max_output_tokens==1024
    assert first.settings.max_output_tokens==1024 and candidate.settings.max_output_tokens==4096
    assert first.transport is candidate.transport is transport
    assert replace(first.settings,max_output_tokens=4096)==candidate.settings
    with pytest.raises(DomainError):_generation_provider(worker,8192)


def test_actual_sender_consistency_check_rejects_old_adapter_and_accepts_fixed_one(prepared_data):
    import json
    from sim2act import natural_live_admission as gate
    from sim2act.goal_planner import configured_provider
    from sim2act.production_trial_sender import _check_business_provider
    data,_,_,receipt=scope(prepared_data)
    contract=gate.parse_contract({**receipt['contract'],'generation_profile':'pa-natural-output4096.v1'})
    settings=replace(data[1],quota_subject=contract.quota_subject)
    worker=SimpleNamespace(s=settings,goal_planner_transport=httpx.MockTransport(lambda request:httpx.Response(200,json={})),store=SimpleNamespace(test_only=True))
    wire=json.dumps({'max_tokens':4096,'tools':[{'function':{'name':'check_candidate'}}]}).encode()
    item=SimpleNamespace(stage='generate')
    with pytest.raises(DomainError):_check_business_provider(configured_provider(worker),settings,contract,item,wire,False)
    _check_business_provider(_generation_provider(worker,4096),settings,contract,item,wire,False)
    with pytest.raises(DomainError):_check_business_provider(_generation_provider(worker,4096),settings,contract,SimpleNamespace(stage='source'),wire,False)

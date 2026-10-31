"""Prospective finite model goal, original tool effects and cold independent check."""

import copy
import json
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, insert, select, update

from sim2act.api import create_app
from sim2act.db import Store, attempts, fingerprint, grants, operations, reservations, run_contracts, runs
from sim2act.errors import DomainError
from sim2act.exact_read import GOAL, VERSION
from sim2act.model import MockModel
from sim2act.worker import Worker


class ExactModel:
    def __init__(self, *, wrong=None):
        self.calls = 0
        self.wrong = wrong

    def request(self, messages, tools):
        self.calls += 1
        assert len(tools) == 1 and tools[0]["function"]["name"] == "resource.read"
        raw = MockModel().request(messages, tools)
        raw["usage"] = {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        if messages[-1]["role"] == "tool":
            content = json.loads(messages[-1]["content"])["data"]["content"]
            answer = json.dumps({"content": content}, ensure_ascii=False)
            if self.wrong == "content": answer = json.dumps({"content": content.rstrip()})
            if self.wrong == "duplicate": answer = '{"content":"wrong","content":'+json.dumps(content)+'}'
            if self.wrong == "extra": answer = json.dumps({"content": content, "extra": True})
            if self.wrong == "empty": answer = '{"content":""}'
            if self.wrong == "markdown": answer = '```json\n'+answer+'\n```'
            raw["choices"][0]["message"]["content"] = answer
        elif self.wrong == "tool":
            raw["choices"][0]["message"]["tool_calls"][0]["function"]["name"] = "artifact.save_text"
            raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = '{"text":"forbidden"}'
        return raw


def prepare(env, content="Keep the exact source.\n保留原始换行。\n", *, key="exact-read:once"):
    store, settings, client, user, _, pid, _ = env
    resource = client.post(f"/api/projects/{pid}/resources", json={
        "name": "synthetic-exact.txt", "format": "txt", "content": content}).json()["id"]
    body = {"goal": GOAL, "resource_refs": [resource], "request_key": key, "acceptance": VERSION}
    reply = client.post(f"/api/projects/{pid}/runs", json=body)
    assert reply.status_code == 202, reply.text
    return reply.json()["run_id"], resource, body, content


def test_real_original_loop_complete_goal_saved_and_cold_read(env):
    rid, resource, body, content = prepare(env)
    model = ExactModel()
    assert Worker(env[0], env[1], model).once()
    result = env[2].get(f"/api/runs/{rid}")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["status"] == "SUCCEEDED" and result["result"]["goal_acceptance"] == "PASS_EXACT_READ_CONTRACT"
    assert result["result"]["read_result"]["content"] == content
    assert result["result"]["task_acceptance"]["whole_task_accepted"] is True
    assert result["result"]["task_acceptance"]["owner_acceptance"] == "PENDING"
    assert model.calls == 2
    assert env[2].post(f"/api/projects/{env[5]}/runs", json=body).json()["run_id"] == rid
    changed = {**body, "goal": "silently compute instead"}
    rejected=env[2].post(f"/api/projects/{env[5]}/runs", json=changed)
    assert rejected.status_code == 400 and rejected.json()["error"]["code"] == "VERIFICATION_FAILED"
    cold = Store(env[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, env[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            assert client.get(f"/api/runs/{rid}").json() == result
        assert not Worker(cold, env[1], ExactModel()).once()
    finally:
        cold.engine.dispose()


@pytest.mark.parametrize("fault", ["content", "duplicate", "extra", "empty", "markdown", "tool"])
def test_no_success_for_wrong_final_json_or_effect(env, fault):
    rid, *_ = prepare(env)
    assert Worker(env[0], env[1], ExactModel(wrong=fault)).once()
    with env[0].engine.connect() as c:
        row = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        assert row["status"] != "SUCCEEDED" and row["result"] is None
        if fault != "tool":
            assert len(c.execute(select(attempts).where(attempts.c.run_id == rid)).all()) == 2
            assert len(c.execute(select(operations).where(operations.c.run_id == rid)).all()) == 1
        if fault in {'duplicate','markdown'}:
            assert row['error']['code']=='MODEL_OUTPUT_INVALID'
            saved=c.execute(select(attempts.c.response).where(attempts.c.run_id==rid)
                            .order_by(attempts.c.created_at.desc())).scalars().first()
            if fault=='markdown':assert saved['content'].startswith('```json')


@pytest.mark.parametrize("fault", ["result", "response", "receipt", "intent", "context", "usage",
    "reservation", "strip", "unknown", "source", "grant", "owner", "adapter", "identity-policy", "weight", "params-none", "params-list", "result-list", "receipt-none", "reservation-time"])
def test_cold_read_rejects_changed_evidence_or_authority(env, fault):
    rid, resource, _, _ = prepare(env)
    assert Worker(env[0], env[1], ExactModel()).once()
    with env[0].tx() as c:
        r = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
        aa = [dict(x) for x in c.execute(select(attempts).where(attempts.c.run_id == rid)).mappings()]
        if fault == "result":
            result = copy.deepcopy(r["result"]); result["read_result"]["content"] = "forged"
            c.execute(update(runs).where(runs.c.id == rid).values(result=result))
        elif fault == "result-list":
            c.execute(update(runs).where(runs.c.id == rid).values(result=[]))
        elif fault == "receipt-none":
            c.execute(update(operations).where(operations.c.run_id==rid).values(receipt=None))
        elif fault == "response":
            c.execute(update(attempts).where(attempts.c.id == aa[0]["id"]).values(response={"role":"assistant","content":"forged"}))
        elif fault == "receipt":
            c.execute(update(operations).where(operations.c.run_id == rid).values(receipt={"status":"VERIFIED"}))
        elif fault == "intent":
            from sim2act.db import operation_intents
            oid = c.execute(select(operations.c.id).where(operations.c.run_id == rid)).scalar_one()
            c.execute(update(operation_intents).where(operation_intents.c.operation_id == oid).values(request={"tool":"resource.read","args":{"resource_id":"res_"+"0"*32}}))
        elif fault == "context":
            ctx = copy.deepcopy(r["context"]);ctx["messages"][0]["content"] = "changed"
            c.execute(update(runs).where(runs.c.id == rid).values(context=ctx))
        elif fault == "usage":
            c.execute(update(attempts).where(attempts.c.id == aa[0]["id"]).values(usage={"status":"unknown","tokens":None}))
        elif fault == "reservation":
            c.execute(update(reservations).where(reservations.c.run_id == rid).values(subject="other-account"))
        elif fault == "reservation-time":
            c.execute(update(reservations).where(reservations.c.run_id == rid).values(created_at=0))
        elif fault == "strip":
            row = c.execute(select(run_contracts).where(run_contracts.c.run_id == rid)).mappings().one()
            raw=copy.deepcopy(row["snapshot"]);raw.pop("exact_read")
            c.execute(update(run_contracts).where(run_contracts.c.run_id == rid).values(snapshot=raw,fingerprint=fingerprint(raw)))
        elif fault == "unknown":
            raw = dict(aa[0]);raw.update(id="attempt_"+"f"*32,status="STARTED")
            c.execute(insert(attempts).values(**raw))
        elif fault == "source":
            from sim2act.db import resources
            c.execute(update(resources).where(resources.c.id == resource).values(content="changed"))
        elif fault == "grant":
            c.execute(update(grants).where(grants.c.principal_id == env[3],grants.c.resource_id == resource).values(revoked=True))
        elif fault == "owner":
            c.execute(update(runs).where(runs.c.id == rid).values(principal_id=env[4]))
        elif fault in {"adapter", "identity-policy", "weight", "params-none", "params-list"}:
            params=copy.deepcopy(aa[0]["parameters"])
            if fault=="params-none":params=None
            elif fault=="params-list":params=[]
            else:params[{"adapter":"adapter_version","identity-policy":"model_identity_policy_version","weight":"weight_version"}[fault]]="changed"
            c.execute(update(attempts).where(attempts.c.id==aa[0]["id"]).values(parameters=params))
    response = env[2].get(f"/api/runs/{rid}")
    assert response.status_code in {400,403,409}, response.text
    assert response.json()["error"]["code"] in {"VERIFICATION_FAILED","VERSION_CONFLICT","GRANT_REVOKED","PERMISSION_DENIED"}


def test_generic_finish_cannot_bypass_prospective_goal(env):
    rid, *_ = prepare(env)
    worker=Worker(env[0],env[1],ExactModel())
    run=env[0].claim(worker.id,env[1].lease_seconds)
    with pytest.raises(DomainError):
        worker.finish(rid,run["fence"],"SUCCEEDED",result={"goal_acceptance":"PASS_EXACT_READ_CONTRACT"})


def test_all_mutable_family_hints_stripped_cannot_execute_as_plain_f1(env):
    rid, *_=prepare(env)
    with env[0].tx() as c:
        r=dict(c.execute(select(runs).where(runs.c.id==rid)).mappings().one())
        row=c.execute(select(run_contracts).where(run_contracts.c.run_id==rid)).mappings().one()
        raw=copy.deepcopy(row['snapshot']);raw.pop('exact_read');raw['goal']['acceptance_version']='F1-tool-chain.v1'
        context=copy.deepcopy(r['context']);context.pop('exact_read_frozen')
        c.execute(update(run_contracts).where(run_contracts.c.run_id==rid).values(snapshot=raw,fingerprint=fingerprint(raw)))
        c.execute(update(runs).where(runs.c.id==rid).values(request_key='stripped-old-path',context=context))
    model=ExactModel()
    refused=env[2].get(f'/api/runs/{rid}')
    assert refused.status_code in {400,409} and refused.json()['error']['code'] in {'VERIFICATION_FAILED','VERSION_CONFLICT'}
    assert Worker(env[0],env[1],model).once()
    assert model.calls==0
    with env[0].engine.connect() as c:
        assert not c.execute(select(attempts.c.id).where(attempts.c.run_id==rid)).first()
        assert not c.execute(select(operations.c.id).where(operations.c.run_id==rid)).first()


@pytest.mark.parametrize('key',['plain-same-goal','exact-read:legacy-unselected'])
def test_plain_f1_same_words_or_old_key_never_gain_a_goal_pass(env,key):
    _,resource,_,_=prepare(env,key='exact-read:unused-setup')
    # Cancel only the deliberately unused setup through its normal owner command.
    with env[0].engine.connect() as c:
        setup=c.execute(select(runs).where(runs.c.request_key=='exact-read:unused-setup')).mappings().one()
    assert env[2].post(f"/api/runs/{setup['id']}/commands",json={'command':'cancel','version':setup['version']}).status_code==200
    reply=env[2].post(f'/api/projects/{env[5]}/runs',json={'goal':GOAL,'resource_refs':[resource],'request_key':key})
    assert reply.status_code==202
    assert Worker(env[0],env[1],MockModel()).once()
    result=env[2].get('/api/runs/'+reply.json()['run_id'])
    assert result.status_code==200,result.text
    assert result.json()['status']=='PARTIAL' and result.json()['result']['goal_acceptance']=='NOT_RUN'


@pytest.mark.parametrize('format,content',[('csv','n\n1\n'),('json','{}'),('txt','a'*4097)])
def test_invalid_prospective_input_creates_no_run_or_cost(env,format,content):
    resource=env[2].post(f'/api/projects/{env[5]}/resources',json={'name':'input','format':format,'content':content}).json()['id']
    response=env[2].post(f'/api/projects/{env[5]}/runs',json={'goal':GOAL,'resource_refs':[resource],
        'acceptance':VERSION,'request_key':'exact-read:invalid'})
    assert response.status_code==400
    with env[0].engine.connect() as c:
        assert not c.execute(select(runs.c.id)).first()
        assert not c.execute(select(attempts.c.id)).first()
        assert not c.execute(select(reservations.c.id)).first()


def test_finish_callback_stop_rolls_back_success(env):
    rid, *_ = prepare(env)
    observed=[]
    def elapsed(c):
        if c.execute(select(runs.c.status).where(runs.c.id==rid)).scalar_one()=="SUCCEEDED":
            observed.append(True)
            worker.stop.set()
    def connected(c):
        event.listen(c,"commit",elapsed)
    model=ExactModel()
    original=model.request
    def request(messages,tools):
        raw=original(messages,tools)
        if messages[-1]["role"]=="tool":
            event.listen(env[0].engine,"engine_connect",connected)
        return raw
    model.request=request
    worker=Worker(env[0],env[1],model)
    try:
        assert worker.once()
    finally:
        event.remove(env[0].engine,"engine_connect",connected)
    assert observed, "Must actually reach the Connection callback after provisional success"
    with env[0].engine.connect() as c:
        assert c.execute(select(runs.c.status).where(runs.c.id==rid)).scalar_one()!="SUCCEEDED"

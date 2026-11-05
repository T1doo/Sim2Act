"""Versioned tool selection wire and sender whitelist; no model calls."""
import json
from types import SimpleNamespace
import pytest
from sim2act.goal_applications import body,generation_tool_choice,generation_output_tokens
from sim2act.production_trial_sender import _wire
from sim2act.errors import DomainError


def messages(protocol=None):
    selected={'version':'goal-natural-spec-application.v1'}
    if protocol:selected['output_protocol']=protocol
    return [{'role':'system','content':'unmodified authority'},{'role':'user','content':json.dumps({'server_ids':selected})}]


@pytest.mark.parametrize('name',['resource.read','spec.check_candidate'])
def test_new_protocol_forces_only_current_registered_tool_and_keeps_budget(name):
    tools=[{'type':'function','function':{'name':name,'parameters':{'type':'object'}}}]
    new=messages('natural-checked-candidate.v1')
    wire=body(new,tools,1024);decoded=json.loads(wire)
    assert decoded['tool_choice']=={'type':'function','function':{'name':name}}
    assert decoded['max_tokens']==1024 and generation_output_tokens(new,tools,1024)==1024
    contract=SimpleNamespace(caps=SimpleNamespace(max_wire_bytes=32768,max_output_tokens=1024),model='intern-s2')
    _wire(contract,wire,stage='generate')
    for invalid in ['auto',{'type':'function','function':{'name':'other'}}]:
        modified={**decoded,'tool_choice':invalid}
        with pytest.raises(DomainError):_wire(contract,json.dumps(modified).encode(),stage='generate')
    old=json.loads(body(messages(),tools,1024))
    assert 'tool_choice' not in old and 'thinking_mode' not in old
    _wire(contract,json.dumps(old).encode(),stage='generate')


def test_final_and_unknown_tools_do_not_gain_tool_selection():
    new=messages('natural-checked-candidate.v1')
    assert generation_tool_choice(new,[]) is None
    assert generation_tool_choice(new,[{'function':{'name':'unregistered'}}]) is None
    assert 'tool_choice' not in json.loads(body(new,[],1024))
    assert generation_tool_choice([],[]) is None


def test_v2_required_mode_and_v1_named_mode_remain_distinct():
    tools=[{'type':'function','function':{'name':'resource.read'}}]
    old=json.loads(body(messages('natural-checked-candidate4096.v1'),tools,1024))
    new=json.loads(body(messages('natural-checked-candidate4096.v2'),tools,1024))
    assert old['tool_choice']=={'type':'function','function':{'name':'resource.read'}}
    assert new['tool_choice']=='required' and new['tools']==old['tools']
    assert 'tool_choice' not in json.loads(body(messages('natural-checked-candidate4096.v2'),[],4096))


def test_v4_structure_stage_thinking_flag_does_not_change_v3_or_read_wire():
    read=[{'type':'function','function':{'name':'read'}}]
    check=[{'type':'function','function':{'name':'check_candidate'}}]
    new=messages('natural-checked-candidate4096.v4');old=messages('natural-checked-candidate4096.v3')
    assert 'thinking_mode' not in json.loads(body(new,read,1024))
    assert json.loads(body(new,check,4096))['thinking_mode'] is False
    assert json.loads(body(new,[],4096))['thinking_mode'] is False
    assert 'thinking_mode' not in json.loads(body(old,check,4096))
    assert 'thinking_mode' not in json.loads(body(old,[],4096))


def test_old_natural_generation_remains_confirmable_after_new_default(env,monkeypatch):
    from test_natural_spec_apps import setup,generate
    from test_pa_spec_apps import confirm
    from sim2act import goal_applications
    data=setup(env);original=goal_applications.policy
    with monkeypatch.context() as patch:
        def legacy(*args,**kwargs):
            selected=original(*args,**kwargs);selected.pop('output_protocol',None);return selected
        patch.setattr(goal_applications,'policy',legacy)
        rid,result,sent=generate(data)
    assert all('tool_choice' not in request for request in sent)
    assert 'output_protocol' not in result['contract']['snapshot']['application_generation']
    saved=confirm(data,rid,result)
    assert saved.status_code==200,saved.text

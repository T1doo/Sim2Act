"""Only declared v3 wire names map to canonical tools; raw history is retained."""
import copy,json
from types import SimpleNamespace
import pytest
from sim2act.natural_wire_tools import PROTOCOL,tools,parse
from sim2act.goal_applications import parse_generation,READ_TOOLS
from sim2act.production_trial_sender import _derive
from sim2act.errors import DomainError


def reply(name='read',args=None):
    return {'model':'intern-s2','choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':'','tool_calls':[{'id':'call-1','type':'function','function':{'name':name,'arguments':json.dumps(args or {'resource_id':'res_'+'a'*32})}}]}}], 'usage':{'prompt_tokens':5,'completion_tokens':5,'total_tokens':10}}


def test_wire_names_are_explicit_and_raw_assistant_names_remain_unchanged():
    original=copy.deepcopy(READ_TOOLS);wire=tools(READ_TOOLS)
    assert READ_TOOLS==original and wire[0]['function']['name']=='read'
    raw=reply();saved=copy.deepcopy(raw)
    message,calls=parse_generation(raw,SimpleNamespace(output_protocol=PROTOCOL))
    assert message['tool_calls'][0]['function']['name']=='read'
    assert calls[0]['function']['name']=='resource.read' and raw==saved


@pytest.mark.parametrize('name',['resource.read','unregistered'])
def test_v3_does_not_accept_names_outside_its_wire_declaration(name):
    with pytest.raises(DomainError):parse(reply(name))


def test_original_parameter_validation_and_old_capture_verdict_are_preserved():
    with pytest.raises(DomainError):parse(reply(args={'resource_id':3}))
    raw=json.dumps(reply()).encode()
    old=_derive(raw,True,True,_generation=True)
    new=_derive(raw,True,True,_generation=True,_generation_protocol=PROTOCOL)
    assert old.response_verdict=='UNKNOWN_OR_REJECTED'
    assert new.response_verdict=='VALID_PROTOCOL'

"""Regression for the real invalid data.hash output; no external model calls."""
import json
import pytest
from jsonschema import Draft202012Validator, ValidationError
from sim2act.goal_applications import _literal_initial_messages


def test_v6_describes_valid_edges_and_rejects_observed_invalid_source():
    goal={'snapshot':{'content':{'title':'frozen','goal':'literal'}}}
    material={'resource_id':'res_'+'a'*32,'hash':'b'*64,'format':'txt'}
    def payload(version):
        return json.loads(_literal_initial_messages(goal,{'output_protocol':version},material,{})[1]['content'])
    old=payload('compact-candidate-json4096.v5')
    new=payload('compact-candidate-json4096.v6')
    schema=new['candidate_schema']
    Draft202012Validator.check_schema(schema)
    outputs=schema['properties']['manifest']['properties']['outputs']
    valid={name:{'source':'step','ref':'generated_step','field':name} for name in outputs['required']}
    Draft202012Validator(outputs).validate(valid)
    invalid={**valid,'source_hash':{'source':'data','ref':'data_resource','field':'hash'}}
    with pytest.raises(ValidationError):Draft202012Validator(outputs).validate(invalid)
    invalid={**valid,'source_hash':{'source':'step','ref':'generated_step','field':'hash'}}
    with pytest.raises(ValidationError):Draft202012Validator(outputs).validate(invalid)
    inputs=schema['$defs']['WorkflowStep']['properties']['inputs']
    Draft202012Validator(inputs).validate({'resource_id':{'source':'data','ref':'resource','field':'resource_id'},'term':{'source':'input','field':'term'}})
    with pytest.raises(ValidationError):
        Draft202012Validator(inputs).validate({'resource_id':{'source':'step','ref':'resource','field':'resource_id'},'term':{'source':'input','field':'term'}})
    assert new['saved_goal']==old['saved_goal']==goal
    assert new['source']==old['source']
    assert 'field_sources' not in old['literal_contract']['declaration_rules']
    assert old['candidate_schema']['properties']['manifest']['properties']['outputs']!=outputs

"""Published port rules must describe actual compilation, never source answers."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest
from test_natural_spec_apps import recipe
from sim2act import natural_specs as natural
from sim2act.contracts import Limits
from sim2act.errors import DomainError


def limits():
    return Limits(max_requests=2,max_tools=4,max_repairs=0,max_total_tokens=64000,max_output_tokens=1024,run_seconds=300)


@pytest.mark.parametrize('style',['single','parallel','sequential'])
def test_wiring_catalog_agrees_with_real_compiler_for_each_supported_topology(style):
    graph=recipe(style);catalog=natural.wiring_contract();models=[s for s in graph['steps'] if s['operator'] in natural.MODEL_KINDS]
    replacements={'<read_step_id>':graph['steps'][0]['step_id'],'<first_model_step_id>':models[0]['step_id'],
        '<earlier_model_step_id>':models[0]['step_id'],'<second_model_step_id>':models[-1]['step_id'],
        '<model_or_merge_step_id>':graph['steps'][-3]['step_id'],'<verify_step_id>':graph['steps'][-2]['step_id']}
    for step in graph['steps']:
        kind={natural.READ:'read',natural.MERGE:'merge',natural.VERIFY:'verify',natural.SAVE:'save'}.get(step['operator'],'model')
        expected=copy.deepcopy(catalog[kind]['inputs'])
        if 'prior_items' in step['inputs']:expected.update(catalog['model']['optional_review_inputs'])
        wire=json.dumps(expected)
        for symbol,identity in replacements.items():wire=wire.replace(symbol,identity)
        expected=json.loads(wire)
        assert expected==step['inputs']
        assert set(step['depends_on'])=={v['ref'] for v in expected.values() if v['source']=='step'}
    rid='res_'+'a'*32;goal=dict(title='Review',goal='Keep source and uncertainty',known=[],assumptions=[],unresolved=[],constraints=[],acceptance_checks=[],resource_refs=[rid])
    args=('app_'+'b'*32,'goal_'+'c'*32,'proj_'+'d'*32,'e'*64,rid,goal,limits(),'f'*64)
    natural.expand(graph,*args)
    bad=copy.deepcopy(graph);bad['steps'][1]['inputs']['text']=bad['steps'][1]['inputs'].pop('content')
    with pytest.raises(DomainError,match='Exact source/predecessor ports'):natural.expand(bad,*args)


def test_read_index_uses_exact_unicode_positions_without_semantic_labels():
    text='甲\r\nβeta\n\nPending?'
    index=natural.source_line_index(text)
    assert index['content_length']==len(text) and index['unit']=='unicode_codepoints' and index['end']=='exclusive'
    assert index['lines']==[dict(start=0,end=1,quote='甲'),dict(start=3,end=7,quote='βeta'),dict(start=9,end=17,quote='Pending?')]
    assert all(text[row['start']:row['end']]==row['quote'] and set(row)=={'start','end','quote'} for row in index['lines'])


def test_only_v6_prompt_publishes_wiring_old_v5_payload_stays_unchanged():
    material=dict(resource_id='res_'+'a'*32,hash=hashlib.sha256(b'Unresolved.').hexdigest(),format='txt',content='Unresolved.')
    def messages(protocol):
        selected=SimpleNamespace(output_protocol=protocol,model_dump=lambda **_:dict(output_protocol=protocol))
        contract=SimpleNamespace(application_generation=selected,source_goal_card=SimpleNamespace(model_dump=lambda:dict(snapshot={})),limits=limits())
        return natural._initial_messages_from_facts(contract,material)
    old=json.loads(messages('natural-checked-candidate4096.v5')[1]['content'])
    new=json.loads(messages('natural-checked-candidate4096.v6')[1]['content'])
    assert old['codec']==natural.codec_contract() and 'operator_wiring' not in old['codec']
    assert new['codec'].pop('operator_wiring')==natural.wiring_contract() and new['codec']==old['codec']
    assert new['source']==old['source'] and set(new['source'])=={'resource_id','hash','format'}
    assert new['oracle_gold_supplied'] is False

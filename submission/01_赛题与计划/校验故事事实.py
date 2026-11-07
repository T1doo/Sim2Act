from pathlib import Path
from decimal import Decimal
import json,copy

BASE=Path(__file__).resolve().parent
def verify(d):
    assert d['duration_seconds']==270
    assert d['scope']['story_team_is_entrant_team'] is False
    rules={r['rule_revision']:r for r in d['rules']}
    cases={x['case_id']:x for x in d['cases']}
    instances={x['instance_id']:x for x in d['instances']}
    releases={(a['app_id'],r['app_release']):r['rule_revision'] for a in d['applications'] for r in a['releases']}
    ids=set();run_ids=set()
    for r in d['results']:
        assert r['result_id'] not in ids and r['run_id'] not in run_ids
        ids.add(r['result_id']);run_ids.add(r['run_id'])
        instance=instances[r['instance_id']]
        assert releases[(instance['app_id'],r['app_release'])]==r['rule_revision']
        total=sum((Decimal(x['amount']) for x in cases[instance['case_id']]['budget_items']),Decimal(0))
        limit=Decimal(rules[r['rule_revision']]['budget_limit'])
        assert total==Decimal(r['budget_total'])
        assert max(total-limit,Decimal(0))==Decimal(r['over_limit'])
        assert max(limit-total,Decimal(0))==Decimal(r['remaining'])
        assert r['immutable'] and r['owner_acceptance']=='PENDING'
    assert [r['display_number'] for r in d['results']]==[1,2,3]
    assert [r['result_revision'] for r in d['results']]==[1,1,2]
    pb=d['pb_contract']
    assert pb['source_app_id'] is None and pb['source_is_pa_result'] is False
    assert pb['source_run_id'] not in run_ids
    assert pb['guide_rule_changed']=='BLOCK_REUSE_AND_ENTER_T3'
    assert pb['guide_rule_unknown']=='WAIT_FOR_CONFIRMATION'
    binding=d['typed_binding']
    assert binding['input_field']=='budget_items[].amount'
    assert binding['output_field']=='budget_total'
    assert set(binding['check_inputs'])=={'budget_total','budget_limit'}
    assert Decimal(binding['normalization']['CNY_10000'])==10000
    events=d['events'];actions={e['action']:e for e in events}
    assert len([e for e in events if e['action']=='editorial_time_jump_to_result'])==3
    assert len(actions)==len(events)-2
    for e in events:
        scene=int(e['scene'][1:]);assert (scene-1)*10<=e['time']<scene*10
    def before(a,b):assert actions[a]['time']<actions[b]['time']
    before('confirm_publish_scope','click_publish_v1')
    before('click_publish_v1','show_published_v1')
    before('show_published_v1','click_run_a1')
    before('confirm_case_b_inputs','click_run_b1')
    before('show_independent_task','click_extract_application')
    before('bind_new_inputs','click_input_checks')
    before('click_input_checks','show_check_report')
    before('show_check_report','confirm_pb_scope')
    before('confirm_pb_scope','publish_pb')
    before('publish_pb','click_pb_run')
    before('confirm_change_and_publish_v2','show_published_v2')
    before('show_published_v2','click_run_a2')
    for rid in ['story_run_a1','story_run_b1','story_run_a2']:
        relevant=[e for e in events if e.get('run_id')==rid]
        assert len(relevant)==2 and relevant[0]['time']<relevant[1]['time']
    assert d['runtime_evidence']['semantic_acceptance']=='NOT_RUN'
    return True

if __name__=='__main__':
    d=json.loads((BASE/'故事事实源_v03.json').read_text(encoding='utf-8'))
    verify(d)
    mutations=[]
    x=copy.deepcopy(d);x['results'][0]['app_release']='v2';mutations.append(('旧结果误绑新版',x))
    x=copy.deepcopy(d);x['results'][2]['budget_total']='80000.00';mutations.append(('把预算改成上限',x))
    x=copy.deepcopy(d);x['pb_contract']['source_app_id']='story_app_research';mutations.append(('P-B来源混回P-A',x))
    x=copy.deepcopy(d);x['events'][0]['time']=129;mutations.append(('发布先于确认',x))
    x=copy.deepcopy(d);x['pb_contract']['guide_rule_changed']='ALLOW';mutations.append(('新指南绕过规则演进',x))
    caught=[]
    for label,x in mutations:
        try:verify(x)
        except (AssertionError,KeyError):caught.append(label)
        else:raise AssertionError('未拒绝：'+label)
    report={'status':'DESIGN_FACTS_CHECKED_NOT_RENDERED','budget_chains':3,'ordering_events':len(d['events']),'rejected_mutations':caught,'pending_frames':[e['action'] for e in d['events'] if e.get('asset_status')=='NEEDS_NEW_FRAME'],'scope':'正式设计数据与动作顺序；不证明图片、H3、运行环境或派生文件已同步'}
    (BASE/'故事事实校验_v03.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

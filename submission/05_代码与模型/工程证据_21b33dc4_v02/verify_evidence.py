"""Offline consistency checks on the shipped frozen evidence. Standard library only."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import json,hashlib,csv,copy,re

HERE=Path(__file__).resolve().parent
def read(name):return json.loads((HERE/name).read_text(encoding='utf-8-sig'))
def canonical(obj):return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def verify(raw,claims,candidate,timings):
    assert raw['source_commit']=='21b33dc4e8d6f0dfb74c65e9cf91cd5af31ed9ce'
    assert raw['model_alias']==raw['model_alias_ledger']=='intern-s2'
    assert raw['release']['formal_publication_enabled'] is False
    assert raw['release']['namespace']=='INTERNAL_ENGINEERING_ONLY'
    assert raw['instance']['release_id']==raw['release']['id']
    assert raw['generation_status']=='PARTIAL'
    slots=raw['request_slots'];assert len(slots)==claims['request_count']==5
    assert Counter(x['identity']['stage'] for x in slots)=={'generate':3,'source':1,'cold':1}
    assert len({x['identity']['attempt_id'] for x in slots})==5
    totals=Counter()
    for slot in slots:
        identity=slot['identity'];settlement=slot['settlement']
        assert slot['attempted'] and slot['accepted'] and settlement['outcome']=='RECEIVED'
        assert settlement['prompt_tokens']+settlement['completion_tokens']==settlement['total_tokens']
        for key in ['prompt_tokens','completion_tokens','total_tokens']:totals[key]+=settlement[key]
        events=raw['events'][identity['stage']]
        assert all(e['run_id']==identity['run_id'] for e in events)
        received=[e for e in events if e['kind'] in ['GA_RECEIVED','NS_RECEIVED'] and e['data'].get('attempt_id')==identity['attempt_id']]
        assert len(received)==1 and slot['reserved_at']<=received[0]['created_at']
        body_events=[e['data'] for e in events if e['kind']=='PA_TRIAL_BODY' and e['data'].get('attempt_id')==identity['attempt_id']]
        request=next(e for e in body_events if e['family']=='pa_trial_request_body.v1')
        response=next(e for e in body_events if e['family']=='pa_trial_response_body.v1')
        assert request['complete'] and response['complete']
        assert request['decoded_sha256']==identity['wire_sha256']
        assert response['decoded_sha256']==settlement['response_sha256']
        # The ledger binds received bytes; GA_RECEIVED binds JSON reserialization.
        # They legitimately differ when whitespace or Unicode escaping changes.
        if identity['stage']=='generate':assert received[0]['data']['raw_fingerprint']==response['canonical_sha256']
    assert dict(totals)==claims['totals']
    assert totals['total_tokens']==17336
    for t in timings:
        events=raw['events'][t['stage']]
        start=next(e for e in events if e['id']==t['start_event_id'])
        end=next(e for e in events if e['id']==t['end_event_id'])
        assert start['kind']=='ACCEPTED' and end['kind']=='STATE'
        assert start['created_at']==t['accepted_unix'] and end['created_at']==t['terminal_unix']
        assert Decimal(str(end['created_at']))-Decimal(str(start['created_at']))==Decimal(t['seconds'])
        assert end['data']['status']==t['terminal_status']
    g=candidate['goal_application'];original={k:v for k,v in candidate.items() if k!='goal_application'}
    assert canonical(original)==g['candidate_fingerprint']
    checked=next(e for e in raw['events']['generate'] if e['kind']=='GA_CANDIDATE_VALIDATED')
    assert checked['data']['candidate_fingerprint']==g['candidate_fingerprint']
    assert [x['step_id'] for x in candidate['spec_recipe']['steps']]==['read','model_all','verify','save']
    for label,revision in [('source',1),('cold',2)]:
        run=raw['runs'][label]
        assert run['instance_id']==raw['instance']['id'] and run['release_id']==raw['release']['id']
        assert run['result_version']==revision and run['status']=='SUCCEEDED'
        assert run['semantic_goal_acceptance']=='NOT_RUN' and run['owner_acceptance']=='PENDING'
        assert run['citation_status']=='PASS'
        assert len(run['steps'])==4 and all(x['status']=='VERIFIED' for x in run['steps'])
        effect=run['known_effects'][0]
        assert effect['instance_id']==run['instance_id'] and effect['version']==revision and effect['release_id']==run['release_id']
    assert raw['source_cold_read'] is True
    return dict(totals)

def main():
    raw=read('冻结记录_脱敏字段.json');claims=read('主张与证据索引.json');candidate=read('候选应用规格.json');timings=read('阶段耗时定义与明细.json')
    totals=verify(raw,claims,candidate,timings)
    original=read('verification.json');assert original['source_commit']==raw['source_commit']
    for name,expected in original['files'].items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==expected,name
    citations=0
    for prefix in ['原材料','新材料']:
        source=(HERE/(prefix+'.txt')).read_bytes().decode('utf-8');check=read(prefix+'_清单.json')
        assert source==check['source_content']
        assert hashlib.sha256(source.encode()).hexdigest()==check['source']['hash']
        for item in check['items']:
            for citation in item['citations']:
                assert 0<=citation['start']<citation['end']<=len(source)
                assert source[citation['start']:citation['end']]==citation['quote']
                citations+=1
    assert citations==6
    csvrows=list(csv.DictReader((HERE/'逐次模型用量.csv').open(encoding='utf-8-sig')))
    assert len(csvrows)==5
    for row,slot in zip(csvrows,raw['request_slots']):
        assert row['attempt_id']==slot['identity']['attempt_id']
        for key in totals:assert int(row[key])==slot['settlement'][key]
    negatives=[]
    bad=copy.deepcopy(raw);bad['request_slots'][0]['settlement']['total_tokens']+=1;negatives.append(('用量篡改',bad))
    bad=copy.deepcopy(raw);bad['runs']['cold']['instance_id']='different';negatives.append(('不同实例冒充复用',bad))
    bad=copy.deepcopy(raw);bad['runs']['source']['semantic_goal_acceptance']='PASS';negatives.append(('引用通过冒充语义通过',bad))
    rejected=[]
    for label,bad in negatives:
        try:verify(bad,claims,candidate,timings)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Negative case was accepted: '+label)
    report=dict(status='PASS_OFFLINE_RECORD_CONSISTENCY',model_requests=5,totals=totals,citation_slices=citations,input_bytes=[(HERE/(x+'.txt')).stat().st_size for x in ['原材料','新材料']],result_versions=[1,2],same_instance=True,same_release=True,candidate_fingerprint_verified=True,rejected_mutations=rejected,not_verified=['供应商侧独立原始响应证明','新业务运行','中文四类文件申报','P-B实际提取执行','原生窗口生命周期','正式发布资格或R0'])
    (HERE/'独立核对结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()

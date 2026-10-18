import datetime
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

base=Path('/workspace/pa-current-unseen-flow-evidence-20261018')
def load(name):
    return json.loads((base/name).read_text())
folders=[p for p in (base/'actual-tmp').iterdir() if p.is_dir() and not p.is_symlink() and (p/'proof.json').is_file()]
assert len(folders)==1
folder=folders[0]
def case(name):
    return json.loads((folder/name).read_text())
proof=case('proof.json');page=case('page-result.json');wires=case('stage-wires.json');workers=case('business-workers.json')
before=load('inputs-before.json');after=load('inputs-after.json')
assert before['inputs']==after['inputs'] and before['input_count']==689 and before['production_count']==133
direct_before=case('source-before.json');direct_after=case('source-after.json')
assert direct_before==direct_after
assert all(before['inputs'][p]==v for p,v in direct_before.items())
nodes=list(ET.parse(base/'actual-junit.xml').getroot().iter('testcase'))
assert len(nodes)==1 and not list(nodes[0])
assert load('execution.json')['exit_code']==0 and proof['status']==page['status']=='PASS'
assert [len(wires[n]) for n in ['generation','pa-v1','pa-v2']]==[3,1,1]
assert len(workers)==2 and all(w['claims']==w['worker_calls']==w['mock_requests']==1 for w in workers)
assert page['worker_calls']==1 and len(page['viewed_results'])==2
assert page['downloads']=='NOT_EXERCISED' and page['fault_injections']=='NONE'
http=case('page-http.json');posts=[r for r in http if r['method']=='POST']
assert len(posts)==5 and len([r for r in posts if r['status']==400 and r['response']['error']['code']=='INVALID_INPUT'])==1
assert len(page['v1_accepted_history'])==2 and page['v1_accepted_history'][-1]['status']=='ACCEPTED'
checkpoints=case('checkpoints.json')
assert len(checkpoints)==7 and all(c['all_expected_rows_verified'] for c in checkpoints)
progress=[json.loads(s) for s in (folder/'progress.jsonl').read_text().splitlines()]
responses=[r for r in progress if r['kind']=='http_response_saved']
for row in responses:
    data=(folder/row['response_file']).read_bytes()
    assert len(data)==row['response_bytes'] and hashlib.sha256(data).hexdigest()==row['response_sha256']
summary=dict(status='PASS_LIMITED_PA_CURRENT_UNSEEN_AND_OVERSIZE_FLOW',time_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    execution=load('execution.json'),unique_pytest_nodes=1,executions=1,failed_executions=0,
    junit=dict(name=nodes[0].attrib['name'],seconds=float(nodes[0].attrib['time'])),
    checks=len(page['checks']),actions=len(page['actions']),page_api=len(page['requests']),
    page_http=len(http),static_asset_responses=len(page['static_resource_loads']),boots=page['boots'],
    all_fixture_and_page_http_responses=len(responses),page_posts=5,simulated_owner_posts=2,
    invalid_preview_posts=1,valid_preview_posts=1,valid_run_posts=1,
    model_mock_requests={k:len(v) for k,v in wires.items()},total_mock_requests=5,
    generation_worker_calls=1,business_worker_calls=2,page_worker_calls=1,real_model_requests=0,
    owner_declaration='PAGE_REAL_PREPARE_DECIDE_WITH_EXPLICITLY_SIMULATED_CHOICES_NOT_REAL_HUMAN_SIGNOFF',
    invalid_input='EXACT_SAVED_2049_ASCII_TXT_MATCHING_GOAL_ACTUAL_400_INVALID_INPUT_ALL_TABLES_UNCHANGED',
    result_versions=[1,2],cold_authorized_artifact_views=2,downloads_exercised=0,
    proof=proof,execution_inputs=dict(count=689,production=133,direct_count=len(direct_before),drift=[]),
    qualification_limits=['single-model finite P-A recipe, not complete general P-A','one synthetic principal/project, not independent dual-principal authorization qualification',
        'JSDOM actual TestClient HTTP, not native browser/Windows','simulated owner choices, not real human/semantic acceptance',
        'PostgreSQL/remote CI/deployment not run','old cancelled installation window and exit139/full-disk evidence gaps unchanged'])
(base/'qualification-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['status','unique_pytest_nodes','junit','checks','actions','page_api','page_http','static_asset_responses','boots','all_fixture_and_page_http_responses','total_mock_requests','execution_inputs']},ensure_ascii=False))

import datetime
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

base=Path('/workspace/pb-first-logic-current-page-evidence-20261018')
def load(path):
    return json.loads(path.read_text())
def sha(data):
    return hashlib.sha256(data).hexdigest()
def fp(value):
    return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
folders=[p for p in (base/'actual-tmp').iterdir() if p.is_dir() and not p.is_symlink() and (p/'proof.json').is_file()]
assert len(folders)==1
folder=folders[0]
proof=load(folder/'proof.json')
page=load(folder/'page-result.json')
workers=load(folder/'business-workers.json')
wires=load(folder/'stage-wires.json')
execution=load(base/'execution.json')
original_before=load(base/'inputs-before.json')
before=load(base/'inputs-fourth-before.json')
after=load(base/'inputs-after.json')
assert before['inputs']==after['inputs'] and before['input_count']==691 and before['production_count']==133
assert before['head']==execution['head']
direct_before=load(folder/'source-before.json')
direct_after=load(folder/'source-after.json')
assert direct_before==direct_after
assert all(before['inputs'][path]==value for path,value in direct_before.items())
nodes=list(ET.parse(base/'actual-junit.xml').getroot().iter('testcase'))
assert len(nodes)==1 and nodes[0].find('failure') is None and nodes[0].find('error') is None and nodes[0].find('skipped') is None
assert execution['exit_code']==0 and proof['status']==page['status']=='PASS'
expected_wires={'generation':3,'source-original':2,'pb-original':2,'logic-check':2,'logic-use':2}
assert {key:len(value) for key,value in wires.items()}==expected_wires
assert proof['total_mock_requests']==sum(expected_wires.values())==11
assert len(workers)==4 and all(row['status']=='SUCCEEDED' and row['mock_requests']==2 and row['worker_calls']==row['claims']>=1 for row in workers)
assert proof['business_worker_calls']==sum(row['worker_calls'] for row in workers)
assert page['worker_calls']==proof['page_worker_commands']==2
assert page['downloads']=='NOT_EXERCISED' and page['fault_injections']=='NONE' and page['owner_decision']=='NOT_EXERCISED'
assert page['logic_revision']==2 and len(page['viewed_results'])==2
assert all(row['result_version']==1 for row in page['run_dimensions'].values())
assert len({row['instance_id'] for row in page['run_dimensions'].values()})==3
assert page['run_dimensions']['original_business']['release_id']==page['run_dimensions']['isolated_check']['release_id']!=page['run_dimensions']['new_logic_business']['release_id']
http=load(folder/'page-http.json')
posts=[row for row in http if row['method']=='POST']
assert len(posts)==7 and [row['status'] for row in posts]==[201,202,201,200,201,200,202]
checkpoints=load(folder/'checkpoints.json')
assert len(checkpoints)==7 and all(row['all_expected_rows_verified'] for row in checkpoints)
for row in checkpoints:
    rows=load(folder/('checkpoint-'+row['phase']+'-rows.json'))
    assert fp(rows)==row['full_table_fingerprint']
progress=[json.loads(line) for line in (folder/'progress.jsonl').read_text().splitlines()]
responses=[row for row in progress if row['kind']=='http_response_saved']
for row in responses:
    data=(folder/row['response_file']).read_bytes()
    assert len(data)==row['response_bytes'] and sha(data)==row['response_sha256']
interruption=load(base/'interrupted-1/interruption-classification.json')
interrupted_after=load(base/'interrupted-1/inputs-after-interruption.json')
retry_before=load(base/'inputs-retry-before.json')
assert original_before['inputs']==interrupted_after['inputs']==retry_before['inputs']
assert 'exit_code' not in load(base/'interrupted-1/execution.json')
assert not (base/'interrupted-1/actual-junit.xml').exists()
retained=load(base/'interrupted-1/retained-original-manifest.json')
for row in retained:
    data=(base/'interrupted-1'/row['path']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['sha256']
assert sum(interruption['saved_mock_counts'].values())==9
timeout=load(base/'timed-out-2/timeout-classification.json')
assert timeout['exit_code']==124 and sum(timeout['saved_mock_counts'].values())==11
assert load(base/'timed-out-2/inputs-after-timeout.json')['inputs']==load(base/'inputs-third-before.json')['inputs']==original_before['inputs']
for row in load(base/'timed-out-2/retained-original-manifest.json'):
    data=(base/'timed-out-2'/row['path']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['sha256']
watchdog=load(base/'watchdog-3/watchdog-classification.json')
assert watchdog['exit_code']==1 and sum(watchdog['saved_mock_counts'].values())==11
assert load(base/'watchdog-3/inputs-after-watchdog.json')['inputs']==original_before['inputs']
for row in load(base/'watchdog-3/retained-original-manifest.json'):
    data=(base/'watchdog-3'/row['path']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['sha256']
watchdog_nodes=list(ET.parse(base/'watchdog-3/actual-junit.xml').getroot().iter('testcase'))
assert len(watchdog_nodes)==1 and watchdog_nodes[0].find('failure') is not None
assert 'BrokenPipeError' in watchdog_nodes[0].find('failure').attrib['message']
input_changes={path for path in before['inputs'] if original_before['inputs'].get(path)!=before['inputs'][path]}
assert input_changes=={'tests/test_pa_natural_spec_ui.py','tests/test_pb_first_logic_current_page_ui.py'}
assert all(original_before['inputs'][path]==record for path,record in before['inputs'].items() if path.startswith('src/'))
assert execution['command'][2]=='1500s'
node_start=next(row for row in progress if row['kind']=='node_started')
test_start=next(row for row in progress if row['kind']=='test_start')
assert node_start['watchdog_seconds']==test_start['subprocess_watchdog_seconds']==1200
assert progress[-1]['kind']=='test_end' and progress[-1]['passed'] and not progress[-1]['watchdog_fired']
summary=dict(status='PASS_LIMITED_PB_FIRST_LOCAL_LOGIC_CURRENT_PAGE',time_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    execution=execution,unique_pytest_nodes=1,executions=4,successful_executions=1,junit_completed_executions=2,completed_executions=2,exited_executions=3,interrupted_executions=1,timed_out_executions=1,failed_executions=2,pytest_failures=1,pytest_assertion_failures=0,
    completed_executions_definition='Two JUnit terminal cases: one PASS and one BrokenPipeError FAIL; only one complete page PASS.',
    failed_executions_definition='One known timeout exit124 plus one pytest exit1; the environment interruption has unknown exit and is separate.',
    junit=dict(name=nodes[0].attrib['name'],seconds=float(nodes[0].attrib['time'])),
    checks=len(page['checks']),actions=len(page['actions']),page_api=len(page['requests']),
    page_http=len(http),static_asset_responses=len(page['static_resource_loads']),boots=page['boots'],
    all_fixture_and_page_http_responses=len(responses),page_posts=7,
    full_table_checkpoints_saved=7,first_check_pass_get_added_sealed_metadata_rows=2,
    model_mock_requests={key:len(value) for key,value in wires.items()},total_mock_requests=11,
    all_rounds_mock_requests=sum(expected_wires.values())+sum(interruption['saved_mock_counts'].values())+sum(timeout['saved_mock_counts'].values())+sum(watchdog['saved_mock_counts'].values()),interrupted_mock_requests=9,timed_out_mock_requests=11,watchdog_mock_requests=11,interrupted_execution=interruption,timed_out_execution=timeout,watchdog_execution=watchdog,
    generation_worker_calls=proof['generation_worker_calls'],business_execution_stages=4,
    business_worker_calls=proof['business_worker_calls'],page_worker_commands=2,
    actual_claim_counts=proof['actual_claim_counts'],real_model_requests=0,
    logic_revision=2,run_dimensions=page['run_dimensions'],cold_authorized_artifact_views=2,
    downloads_exercised=0,owner_decision_exercised=0,fault_injections='NONE',
    proof=proof,execution_inputs=dict(count=691,production=133,direct_count=len(direct_before),drift=[],earlier_source=original_before['head'],harness_correction_paths=sorted(input_changes)),
    qualification_limits=['first finite P-B six-step dependency adjustment, not complete general P-B or all AT-13 categories',
        'normal generation, source execution, extraction, original PB COLD v1 and graph derive are backend fixtures, not page-created',
        'one synthetic principal/project, not independent dual-principal authorization qualification',
        'JSDOM actual TestClient HTTP, not native browser/Windows',
        'Mock outputs and pending owner state, not real model/semantic/human acceptance',
        'PostgreSQL/remote CI/deployment not run; old cancelled window/exit139/full-disk evidence gaps unchanged'],
    diagnostic_history='One pre-product inline environment diagnostic SyntaxError, corrected and explicitly transcribed. Attempt1 environment transport interruption UNKNOWN, no exit/JUnit/finally,443 originals retained. Attempt2 whole-case900s timeout124 after four business stages/11Mock,599 originals retained. Attempt3 whole-case1200s with owned Node900s watchdog killed the receiver during cold tail; pytest1 BrokenPipeError,870 originals retained,11Mock/four business stages/five claims completed. Attempt4 only existing observer parameterization (default900 unchanged; this case1200) and outer1500, all product run300/lease30/clock/budget and assertions unchanged. Earlier691 inputs0drift on2fa, final691 inputs0drift on new freeze; only two test harness paths differ. Preservation helper first zombie assertion and dependent FileNotFound corrected with no process control; RO pure-file diagnostic mistakes are separately retained. Not a full-green history.')
(base/'qualification-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({key:summary[key] for key in ['status','unique_pytest_nodes','junit','checks','actions','page_api','page_http','static_asset_responses','boots','all_fixture_and_page_http_responses','total_mock_requests','business_worker_calls','execution_inputs']},ensure_ascii=False))

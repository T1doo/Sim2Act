import datetime
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

base = Path('/workspace/natural-result-navigation-evidence-20261018')
def load(path):
    return json.loads((base/path).read_text())
def changed(a, b):
    return sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
def junit(name):
    root = ET.parse(base/name).getroot()
    return [dict(name=n.attrib['name'], classname=n.attrib.get('classname'),
        seconds=float(n.attrib.get('time',0)), status='FAIL' if n.find('failure') is not None or n.find('error') is not None else 'PASS')
        for n in root.iter('testcase')]
actual_dirs = [p for p in (base/'actual-complete-tmp').iterdir() if p.is_dir() and not p.is_symlink() and (p/'proof.json').is_file()]
assert len(actual_dirs)==1
folder=actual_dirs[0]
proof=json.loads((folder/'proof.json').read_text())
page=json.loads((folder/'page-result.json').read_text())
wires=json.loads((folder/'stage-wires.json').read_text())
workers=json.loads((folder/'business-workers.json').read_text())
initial_folder=base/'actual-tmp/test_same_pb_instance_navigate0'
initial_wires=json.loads((initial_folder/'stage-wires.json').read_text())
initial_workers=json.loads((initial_folder/'business-workers.json').read_text())
second_folder=base/'actual-final-tmp/test_same_pb_instance_navigate0'
second_wires=json.loads((second_folder/'stage-wires.json').read_text())
second_workers=json.loads((second_folder/'business-workers.json').read_text())
assert [len(second_wires[n]) for n in ['generation','source','pb-v1','pb-v2']]==[3,1,1,1]
assert len(second_workers)==3 and all(x['claims']==1 for x in second_workers)
assert [len(initial_wires[n]) for n in ['generation','source','pb-v1','pb-v2']]==[3,1,1,0]
assert len(initial_workers)==2 and all(x['claims']==1 and x['worker_calls']==1 for x in initial_workers)
http=json.loads((folder/'page-http.json').read_text())
checkpoints=json.loads((folder/'checkpoints.json').read_text())
progress=[json.loads(x) for x in (folder/'progress.jsonl').read_text().splitlines()]
responses=[x for x in progress if x['kind']=='http_response_saved']
initial_before=load('inputs-before.json');initial_after=load('inputs-after-actual.json')
assert initial_before['inputs']==initial_after['inputs']
second_before=load('inputs-second-source.json');second_after=load('inputs-after-second-actual.json')
assert second_before['inputs']==second_after['inputs']
before=load('inputs-final-source.json');after=load('inputs-after-final.json')
actual_drift=changed(before['inputs'],after['inputs'])
archived_source_before=json.loads((folder/'source-before.json').read_text())
assert set(archived_source_before)=={'job','binding','clock','claims'}
active_sources_before={k:before['inputs'][k] for k in json.loads((folder/'source-after.json').read_text())}
active_sources_after=json.loads((folder/'source-after.json').read_text())
current=load('inputs-final-source.json')
final_changes=changed(initial_before['inputs'],current['inputs'])
synthetic_first=junit('synthetic-junit.xml');synthetic_final=junit('synthetic-final-junit.xml');actual_initial=junit('actual-junit.xml');actual_second=junit('actual-final-junit.xml');actual=junit('actual-complete-junit.xml')
assert proof['status']==page['status']=='PASS'
assert [len(wires[n]) for n in ['generation','source','pb-v1','pb-v2']]==[3,1,1,1]
assert len(workers)==3 and all(x['claims']==1 and x['worker_calls']==1 for x in workers)
assert not actual_drift and active_sources_before==active_sources_after
assert final_changes==['tests/natural_application_navigation.cjs','tests/test_natural_result_navigation_ui.py']
assert all(n['status']=='PASS' for n in actual+synthetic_final) and len(actual+synthetic_final)==2
assert len(synthetic_first)==len(actual_initial)==len(actual_second)==1 and synthetic_first[0]['status']==actual_initial[0]['status']==actual_second[0]['status']=='FAIL'
assert len(page['downloads'])==4 and page['worker_calls']==1
assert len([x for x in http if x['method']=='POST'])==2
assert len(checkpoints)==6 and all(x['all_expected_rows_verified'] for x in checkpoints)
synthetic_dirs=[p for p in (base/'synthetic-final-tmp').iterdir() if p.is_dir() and not p.is_symlink() and (p/'navigation.json').is_file()]
assert len(synthetic_dirs)==1
navigation=json.loads((synthetic_dirs[0]/'navigation.json').read_text())
assert navigation['status']=='PASS' and len(navigation['checks'])==36
for download in page['downloads']:
    blob=(folder/'page-result.json.downloads'/download['name']).read_bytes()
    assert len(blob)==download['blob_bytes'] and hashlib.sha256(blob).hexdigest()==download['blob_utf8_sha256']
summary=dict(status='PASS_WITH_THREE_RETAINED_INITIAL_TEST_FAILURES',time_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    actual_execution=load('actual-complete-execution.json'),actual_second_execution=load('actual-final-execution.json'),actual_first_execution=load('actual-execution.json'),synthetic_first_execution=load('synthetic-execution.json'),
    synthetic_final_execution=load('synthetic-final-execution.json'),
    actual_junit=actual,actual_second_junit=actual_second,actual_first_junit=actual_initial,synthetic_first_junit=synthetic_first,synthetic_final_junit=synthetic_final,
    unique_final_pytest_nodes=2,total_pytest_executions=5,passed_executions=2,failed_executions=3,
    actual_page=dict(checks=len(page['checks']),actions=len(page['actions']),api_requests=len(page['requests']),
        static_asset_responses=len(page['static_resource_loads']),boots=page['boots'],downloads=len(page['downloads']),
        page_posts=len([x for x in http if x['method']=='POST']),page_actual_http=len(http),
        all_fixture_and_page_http_responses=len(responses),page_worker_calls=page['worker_calls'],
        late_run_switch=page['late_run_switch']),
    synthetic_checks=36,model_mock_requests={n:len(v) for n,v in wires.items()},total_mock_requests=sum(map(len,wires.values())),
    all_rounds_mock_requests=sum(map(len,initial_wires.values()))+sum(map(len,second_wires.values()))+sum(map(len,wires.values())),initial_actual_mock_requests=sum(map(len,initial_wires.values())),all_rounds_business_worker_calls=len(initial_workers)+len(second_workers)+len(workers),generation_worker_calls_all_rounds=3,second_actual_mock_requests=6,real_model_requests=0,business_workers=workers,proof=proof,
    execution_inputs=dict(actual_count=before['input_count'],production_count=before['production_count'],
        actual_drift=actual_drift,final_source_count=current['input_count'],final_source_changes=final_changes,
        actual_direct_dependency_count=len(active_sources_before),actual_direct_dependency_drift=[],direct_before_authority='687 pre-execution inputs-final-source.json subset; page source-before.json was overwritten by normal source Worker header, preserved as-is; test in-memory before/after assertion passed',initial_actual_drift=[],second_actual_drift=[],synthetic_source_bridge='8f76 -> ba6e changes only unused actual Python test; selected synthetic Python/CJS and all production byte-identical'),
    excluded=['closing/recovery test reruns','cancelled old installation digest window','native browser/Windows',
        'PostgreSQL','real model/semantic/scenario acceptance','remote CI/deployment'])
(base/'qualification-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['status','unique_final_pytest_nodes','total_pytest_executions','actual_page','total_mock_requests','execution_inputs']},ensure_ascii=False))

"""Record every closed execution, including an incomplete final checkpoint."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path('/workspace/production-trial-stages-20261018')
names = ['run-'+str(i) for i in range(1,6)] + [
    'run-6-chain','run-6-negatives','run-7-chain','run-7-negatives',
    'run-8-chain','run-8-negatives']
all_runs = []
for name in names:
    out = root/name
    execution = json.loads((out/'execution.json').read_text())
    assert 'exit_code' in execution, 'Do not summarize an active run'
    missing = [p for p in ('offline-guard.json','junit.xml','inputs-after.json','helpers-after.json')
               if not (out/p).exists()]
    guard = json.loads((out/'offline-guard.json').read_text()) if (out/'offline-guard.json').exists() else None
    cases = []
    if (out/'junit.xml').exists():
        cases = [dict(name=c.attrib['name'], classname=c.attrib.get('classname'),
            seconds=c.attrib.get('time'), verdict='ERROR' if c.find('error') is not None else
            'FAIL' if c.find('failure') is not None else
            'SKIP' if c.find('skipped') is not None else 'PASS')
            for c in ET.parse(out/'junit.xml').iter('testcase')]
    maps_match = None
    if (out/'inputs-after.json').exists():
        maps_match = json.loads((out/'inputs-before.json').read_text()) == json.loads((out/'inputs-after.json').read_text())
    all_runs.append(dict(directory=name, execution=execution, cases=cases,
        missing_closed_artifacts=missing,input_maps_match=maps_match,
        actual_adapter_entries=None if guard is None else sum(
            m['method']=='request_serialized_captured' for m in guard['adapter_methods']),
        forbidden_real_io_attempts=None if guard is None else len(guard['attempts'])))
final = all_runs[-2:]
qualified = (all(r['execution']['exit_code']==0 and not r['missing_closed_artifacts']
    and r['input_maps_match'] is True and r['execution']['input_drift'] is False
    and r['execution']['helper_drift'] is False and r['forbidden_real_io_attempts']==0 for r in final)
    and [c['verdict'] for r in final for c in r['cases']]==['PASS']*4
    and final[0]['execution']['source_commit']==final[1]['execution']['source_commit'])
dbs = []
for p in sorted(root.glob('run-*/actual-tmp/**/fixture.db')):
    if any(part.endswith('current') for part in p.parts): continue
    data=p.read_bytes()
    dbs.append(dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                    copy_to_git=False,synthetic_fixture=True))
value = dict(status='FINAL_FROZEN_FOUR_NODES_PASS_WITH_ALL_PRIOR_FAILURES_PRESERVED'
    if qualified else 'INCOMPLETE_BOUNDED_CHECKPOINT_NOT_QUALIFIED',
    final_freeze=final[-1]['execution']['source_commit'],runs=all_runs,
    planned_unique_nodes=4,unique_nodes=len({c['name'] for r in all_runs for c in r['cases']}),
    total_executions=sum(len(r['cases']) for r in all_runs),
    pass_count=sum(c['verdict']=='PASS' for r in all_runs for c in r['cases']),
    error_count=sum(c['verdict']=='ERROR' for r in all_runs for c in r['cases']),
    failure_count=sum(c['verdict']=='FAIL' for r in all_runs for c in r['cases']),
    final_qualification_executions=sum(len(r['cases']) for r in final),
    final_qualification_passes=sum(c['verdict']=='PASS' for r in final for c in r['cases']),
    final_synthetic_adapter_entries=sum(r['actual_adapter_entries'] or 0 for r in final),
    actual_synthetic_adapter_entries=sum(r['actual_adapter_entries'] or 0 for r in all_runs),
    all_adapter_counters_closed=all(r['actual_adapter_entries'] is not None for r in all_runs),
    real_model_requests=0,old_19_12_8_9_nodes_rerun=0,databases_external_only=dbs)
(root/'qualification-summary.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k not in ('runs','databases_external_only')}))

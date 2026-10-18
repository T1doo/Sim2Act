from pathlib import Path
import collections, hashlib, json, xml.etree.ElementTree as ET
root=Path('/workspace/production-trial-stages-20261018/run-6-chain')
out=Path('/workspace/production-trial-stages-review-20261018')
execution=json.loads((root/'execution.json').read_bytes())
assert execution['exit_code']==1 and 'ended_utc' in execution
stdout=(root/'pytest.stdout').read_text()
line=next(line for line in stdout.splitlines() if 'AssertionError: {"namespace":"INTERNAL_APPRUN"' in line)
result=json.loads(line.split('AssertionError: ',1)[1])
rid=result['id']
assert result['status']=='RUNNING' and result['result'] is None
received=next(e for e in result['events'] if e['kind']=='NS_RECEIVED')
rejected=next(e for e in result['events'] if e['kind']=='NS_REJECTED')
assert rejected['data']['error']=='VERSION_CONFLICT'
guard=json.loads((root/'offline-guard.json').read_bytes())
assert guard['attempts']==[]
heartbeats=[h for h in guard['heartbeats'] if h['run_id']==rid]
last=max(heartbeats,key=lambda h:h['committed_at'])
assert last['lease_seconds']==30
actual_calls=[m for m in guard['adapter_methods'] if m['method']=='request_serialized_captured']
assert collections.Counter(m['family'] for m in actual_calls)=={'synthetic-offline-planner':3,'synthetic-offline-natural-spec':1}
assert json.loads((root/'inputs-before.json').read_bytes())==json.loads((root/'inputs-after.json').read_bytes())
assert json.loads((root/'helpers-before.json').read_bytes())==json.loads((root/'helpers-after.json').read_bytes())
cases=[{'name':x.get('name'),'time':x.get('time'),'error':x.find('error') is not None,'failure':x.find('failure') is not None} for x in ET.fromstring((root/'junit.xml').read_bytes()).iter('testcase')]
files=['execution.json','junit.xml','pytest.stdout','pytest.stderr','offline-guard.json','inputs-before.json','inputs-after.json','helpers-before.json','helpers-after.json']
record={'review':'CLOSED_RUN6_CHAIN_PURE_FILES_ONLY','source':execution['source_commit'],'runner_exit':execution['exit_code'],'runner_outer_seconds':execution['elapsed_seconds'],'junit_cases':cases,'source_run':rid,'actual_captured_adapters':len(actual_calls),'actual_captured_families':dict(collections.Counter(m['family'] for m in actual_calls)),'real_guard_attempts':guard['attempts'],'last_original_heartbeat':last,'ns_received_at':received['created_at'],'ns_rejected_at':rejected['created_at'],'seconds_heartbeat_commit_to_rejection':rejected['created_at']-last['committed_at'],'seconds_rejection_after_lease':rejected['created_at']-last['renewed_until'],'remaining_original_node_deadline_at_rejection':next(h['deadline'] for h in reversed(heartbeats) if h['deadline'] is not None)-rejected['created_at'],'persisted_run_status':result['status'],'persisted_result':result['result'],'input_and_helper_metadata_zero_drift':True,'limits':['No DB opened/stat needed, no SQL/product/test/profile/network execution','Persisted events alone do not locate which in-transaction guard failed: attempted transaction events may roll back','No PASS or recovery/resend claim'],'evidence':[{'path':str(root/name),'bytes':(root/name).stat().st_size,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()} for name in files]}
(out/'run6-closed-lease-observation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ['runner_exit','runner_outer_seconds','junit_cases','actual_captured_adapters','seconds_heartbeat_commit_to_rejection','seconds_rejection_after_lease','remaining_original_node_deadline_at_rejection']}))

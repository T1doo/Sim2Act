from common import *
old=pathlib.Path('/tmp/sim2act-report-dag-reuse-20261010/old-f13')
assert pathlib.Path(instances.__file__).is_relative_to(old)
actual=hashlib.sha256(pathlib.Path(instances.__file__).read_bytes()).hexdigest();expected=hashlib.sha256(subprocess.check_output(['git','show','f13ff8d7661490a7e42a1f7ce3e9179bda54da4b:src/sim2act/csv_dag_instances.py'],cwd=REPO)).hexdigest();assert actual==expected
folder=ROOT/'old-f13-actual-negative';e=env(folder)
try:
 aid,rid,plan,source=fixture(e);proof=request(e,'GET','/api/csv-dag/runs/'+source);assert proof['status']=='SUCCEEDED' and len(proof['steps'])==3
 before=fingerprint(snapshot(e));r=e[2].post('/api/csv-dag/runs/'+source+'/release-approvals',json={'expected_plan_fingerprint':plan['plan_fingerprint'],'request_key':'independent-old-negative'});after=fingerprint(snapshot(e));out={'source_sha':'f13ff8d7661490a7e42a1f7ce3e9179bda54da4b','module_sha256':actual,'actual_original_completed_source':{'status':proof['status'],'steps':len(proof['steps']),'report':proof['result']['output_by_step']},'public_release_response_status':r.status_code,'body':r.json(),'zero_allDB_writes':before==after};assert r.status_code==409 and r.json()['error']['code']=='VERSION_CONFLICT' and before==after;out['verdict']='EXPECTED_NEGATIVE_PASS';(ROOT/'old-f13-negative-result.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
finally:
 (folder/'database-evidence.json').write_text(json.dumps(snapshot(e),indent=2,default=str));e[2].close();e[0].engine.dispose()

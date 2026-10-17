import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

root = Path('/workspace/Sim2Act')
out = Path('/workspace/csv-goal-confirmation-return-evidence-20261017/author-776d7658')
out.mkdir(exist_ok=True)
sha = subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=root,text=True).strip()
assert sha == '776d76581c7f811f39af584283578d9b252a994b'
files = subprocess.check_output(['git','-c','core.fsmonitor=false','ls-files','src','tests','schemas','pyproject.toml','scripts/engineering-ci/package.json','scripts/engineering-ci/package-lock.json'],cwd=root,text=True).splitlines()
def hashes():
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
before=hashes()
(out/'inputs-before.json').write_text(json.dumps(dict(source_sha=sha,files=before),indent=2))
prefix='tests/test_csv_goal_revisions.py::test_visible_same_goal_revision_check_release_adopt_and_new_run'
core=[
    'tests/test_csv_goal_revisions.py::test_same_app_actual_check_explicit_release_adoption_and_new_goal_run',
    'tests/test_csv_goal_revisions.py::test_adopt_without_drift_new_worker_result_and_new_run_pending',
    'tests/test_csv_goal_revisions.py::test_checked_proposal_rejects_current_drift_and_keeps_original',
    'tests/test_csv_goal_revisions.py::test_check_role_pins_wrong_input_and_independent_marker_downgrade',
    'tests/test_csv_goal_revisions.py::test_revoked_new_goal_material_gate_precedes_private_goal_and_proposal_reads',
    'tests/test_persistent_app_runs.py::test_atomic_enqueue_reopen_existing_worker_fresh_result_no_model_no_grants',
    'tests/test_internal_lifecycle.py::test_switch_exact_approval_data_and_pointer_cas[data]',
    'tests/test_csv_owner_review.py::test_no_retroactive_scope_new_result_does_not_inherit_or_sign_old_run',
    'tests/test_application_use.py::test_application_use_actual_http',
]
groups={
    'original':core+[prefix+'['+x+']' for x in ('deliver','lost','navigation','rejected')],
    'confirmation-return':[prefix+'['+x+']' for x in ('return-preview','return-release','return-adoption','return-stale','lost-adoption')],
}
env={**os.environ,'NODE_PATH':str(root/'scripts/engineering-ci/node_modules'),'PYTHONPATH':str(root/'src')}
env.pop('SIM2ACT_TEST_DATABASE_URL',None)
def run(item):
    name,tests=item
    folder=out/name
    folder.mkdir(exist_ok=True)
    cmd=['/workspace/sim2act-venv/bin/python','-m','pytest','-q',*tests,'-o','tmp_path_retention_policy=all','-o','tmp_path_retention_count=99','--basetemp=/tmp/csv-goal-confirmation-return-author-776d7658-'+name+'-20261017','--junitxml='+str(folder/'junit.xml')]
    (folder/'command.json').write_text(json.dumps(dict(source_sha=sha,command=cmd,sqlite_forced_by_unset_external_database=True),indent=2))
    started=time.time()
    with (folder/'pytest.log').open('w') as log:
        result=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT,env=env)
    cases=[dict(x.attrib,failures=[f.text for f in x.findall('failure')],errors=[f.text for f in x.findall('error')],skipped=bool(x.findall('skipped'))) for x in ET.parse(folder/'junit.xml').iter('testcase')]
    value=dict(source_sha=sha,returncode=result.returncode,wall_seconds=time.time()-started,cases=cases)
    (folder/'report.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
    print(json.dumps(dict(shard=name,returncode=result.returncode,cases=len(cases)),indent=2),flush=True)
    return value
started=time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(run,groups.items()))
after=hashes()
(out/'inputs-after.json').write_text(json.dumps(dict(source_sha=sha,files=after),indent=2))
cases=[c for group in results for c in group['cases']]
value=dict(source_sha=sha,returncodes=[v['returncode'] for v in results],wall_seconds=time.time()-started,source_inputs=len(files),source_unchanged=before==after,unique_cases=len({(c['classname'],c['name']) for c in cases}),actual_executions=len(cases),failures=sum(bool(c['failures'] or c['errors']) for c in cases),skips=sum(c['skipped'] for c in cases),cases=cases,scope='Synthetic SQLite, actual ASGI endpoints and complete product DOM in JSDOM, original NoModel CSV Worker. No real model/semantic/Windows/PG/native browser/remote CI/deployment.')
(out/'report.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in value.items() if k!='cases'},indent=2),flush=True)
raise SystemExit(0 if all(v['returncode']==0 for v in results) and before==after and len(cases)==21 else 1)

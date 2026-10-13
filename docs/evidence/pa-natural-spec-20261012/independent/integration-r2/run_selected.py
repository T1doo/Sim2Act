from pathlib import Path
import os,subprocess,time,json
p=Path(__file__).resolve().parent;repo=Path('/workspace/Sim2Act-pa-provider')
selected=['tests/test_bounded_agent_apps.py::test_current_read_grant_rechecked_before_dispatch','tests/test_bounded_agent_apps.py::test_revoked_queued_pair_can_resume_only_after_grant_restored','tests/test_bounded_agent_apps.py::test_queued_scope_rejection_does_not_follow_corrupt_app_run_pointer','tests/test_natural_spec_apps.py::test_queued_revocation_updates_pair_without_private_body_reads','tests/test_text_software_qualification.py','tests/test_text_continuations.py::test_exact_old_db_cold_current_continuation_preserves_and_new_worker',*[f'tests/test_goal_text_ui.py::test_goal_text_offline_page_actual_worker[{s}]' for s in ['valid','lost-generation','lost-confirm','late-confirm-edit-undo','late-confirm-read-edit-undo']]]
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'src')+':'+str(repo/'tests'),NODE_PATH='/workspace/node-tools/node_modules')
base=['/workspace/Sim2Act/.venv/bin/python','-m','pytest',*selected,'-q']
collect=base+['--collect-only','-o','cache_dir='+str(p/'collection-cache')]
with (p/'collection.stdout').open('w') as o,(p/'collection.stderr').open('w') as e:col=subprocess.run(collect,cwd=repo,env=env,stdout=o,stderr=e)
nodes=[x.strip() for x in (p/'collection.stdout').read_text().splitlines() if x.startswith('tests/') and '::' in x];(p/'collection-exit.json').write_text(json.dumps({'returncode':col.returncode,'args':collect,'unique_nodes':len(set(nodes)),'nodes':nodes},indent=2)+'\n');assert col.returncode==0 and len(nodes)==len(set(nodes))==36
args=base+['--basetemp='+str(p/'selected-fixtures'),'-o','cache_dir='+str(p/'selected-cache'),'--junitxml='+str(p/'selected.xml')]
start=time.time();(p/'selected-command.json').write_text(json.dumps({'args':args,'cwd':str(repo),'started_at':start,'safe_environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','NODE_PATH']},'database':'SQLite only: optional PG URL removed without output'},indent=2)+'\n')
with (p/'selected.stdout').open('w') as o,(p/'selected.stderr').open('w') as e:done=subprocess.run(args,cwd=repo,env=env,stdout=o,stderr=e)
r={'returncode':done.returncode,'started_at':start,'ended_at':time.time(),'wall_seconds':time.time()-start,'args':args};(p/'selected-exit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(done.returncode)

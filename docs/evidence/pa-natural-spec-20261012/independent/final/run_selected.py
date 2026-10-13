from pathlib import Path
import os,subprocess,time,json
root=Path(__file__).resolve().parent;repo=Path('/workspace/Sim2Act-pa-provider')
selected=['tests/test_natural_spec_apps.py','tests/test_text_software_qualification.py','tests/test_pa_spec_apps.py::test_actual_feedback_confirmation_and_transactional_worker[False-False]','tests/test_pa_spec_apps.py::test_cold_unseen_material_preserves_model_recipe_and_no_model','tests/test_text_continuations.py::test_exact_old_db_cold_current_continuation_preserves_and_new_worker','tests/test_pa_natural_spec_ui.py']
args=['/workspace/Sim2Act/.venv/bin/python','-m','pytest',*selected,'-q','--basetemp='+str(root/'selected-fixtures'),'-o','cache_dir='+str(root/'selected-cache'),'--junitxml='+str(root/'selected.xml')]
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None);env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'src')+':'+str(repo/'tests'),NODE_PATH='/workspace/node-tools/node_modules')
start=time.time();(root/'selected-command.json').write_text(json.dumps({'args':args,'cwd':str(repo),'started_at':start,'safe_environment':{k:env[k] for k in ['PYTHONDONTWRITEBYTECODE','PYTHONPATH','NODE_PATH']},'sqlite_only':'SIM2ACT_TEST_DATABASE_URL removed without output'},indent=2)+'\n')
with (root/'selected.stdout').open('w') as out,(root/'selected.stderr').open('w') as err:
 p=subprocess.run(args,cwd=repo,env=env,stdout=out,stderr=err)
result={'returncode':p.returncode,'started_at':start,'ended_at':time.time(),'wall_seconds':time.time()-start,'args':args}
(root/'selected-exit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(p.returncode)

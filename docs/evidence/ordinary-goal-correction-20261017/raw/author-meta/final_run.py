import hashlib,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
root=Path('/workspace/Sim2Act');out=Path('/workspace/ordinary-goal-correction-evidence-20261017');os.chdir(root);g=['git','-c','core.fsmonitor=false']
def git(*args):return subprocess.check_output(g+list(args),text=True).strip()
sha=git('rev-parse','HEAD');assert sha=='d731199a1fd6272e1a79e1c761a1461500fd5227';assert not git('status','--porcelain')
files=sorted(f for f in subprocess.check_output(g+['ls-files','-z','src','tests','schemas','pyproject.toml']).decode().split('\0') if f)
def hashes():return {f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files}
before=hashes();(out/'final-inputs-before.json').write_text(json.dumps(dict(source=sha,files=before),indent=2)+'\n')
commands=[['/workspace/sim2act-venv/bin/ruff','check','src/sim2act/api.py','src/sim2act/contracts.py','src/sim2act/db.py','src/sim2act/goal_applications.py','src/sim2act/goal_runs.py','src/sim2act/ordinary_corrections.py','src/sim2act/ordinary_owner_review.py','src/sim2act/worker.py','tests/test_ordinary_corrections.py','tests/test_ordinary_corrections_ui.py'],['node','--check','src/sim2act/web/ordinary-owner.js'],['node','--check','tests/ordinary_owner_ui.cjs'],g+['diff','--check']];results=[]
for i,cmd in enumerate(commands):
 r=subprocess.run(cmd,capture_output=True,text=True);(out/f'final-static-{i}.log').write_text(r.stdout+r.stderr);results.append(dict(argv=cmd,rc=r.returncode));assert r.returncode==0
api=['tests/test_ordinary_corrections.py']
pages=['tests/test_ordinary_corrections_ui.py','tests/test_goal_card_runs.py::test_unadvertised_write_tool_rejected_without_authority_change','tests/test_ordinary_owner_review.py::test_frozen_goal_same_run_explicit_ordered_declaration_and_history','tests/test_ordinary_owner_ui.py::test_ordinary_owner_full_page_actual_api[revocation]','tests/test_ordinary_goal_md.py::test_explicit_md_contract_actual_artifact_same_run_and_simulated_declaration','tests/test_ordinary_goal_md_ui.py::test_saved_goal_md_actual_page[md-navigation]','tests/test_ordinary_csv_report.py::test_prospective_csv_report','tests/test_ordinary_run_results.py::test_ordinary_goal_results_actual_tools_and_page[workspace-return]']
def run(part):
 name,selectors,expected=part;dest=out/('final-author-'+name);dest.mkdir(exist_ok=False)
 argv=['/workspace/sim2act-venv/bin/python','-m','pytest','-q',*selectors,'--basetemp=/tmp/ordinary-goal-correction-author-final-d731199a-'+name+'-20261017','--junitxml='+str(dest/'junit.xml'),'-p','correction_evidence_plugin']
 env={**os.environ,'NODE_PATH':str(root/'scripts/engineering-ci/node_modules'),'PYTHONPATH':str(out)+os.pathsep+str(root/'src'),'CORRECTION_EVIDENCE_OUTPUT':str(dest)};start=time.time()
 with (dest/'pytest.log').open('w') as log:r=subprocess.run(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
 nodeids=json.loads((dest/'final-collected.json').read_text());suite=next(ET.parse(dest/'junit.xml').iter('testsuite'));entry=dict(name=name,argv=argv,rc=r.returncode,wall_seconds=time.time()-start,junit=dict(suite.attrib),nodes=len(nodeids),expected=expected,collected=nodeids)
 (dest/'execution.json').write_text(json.dumps(entry,indent=2)+'\n');return entry
start=time.time()
with ThreadPoolExecutor(max_workers=2) as pool:parts=list(pool.map(run,[('api',api,23),('pages',pages,14)]))
after=hashes();(out/'final-inputs-after.json').write_text(json.dumps(dict(source=sha,files=after),indent=2)+'\n');nodeids=[node for p in parts for node in p['collected']];(out/'final-collected.json').write_text(json.dumps(nodeids,indent=2)+'\n');clean=not git('status','--porcelain');result=dict(source=sha,input_count=len(files),inputs_unchanged=before==after,clean_worktree=clean,wall_seconds=time.time()-start,commands=results,parallel_shards=parts,unique_nodes=len(set(nodeids)),all_collected=len(nodeids));(out/'final-execution.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('parallel_shards','commands')}));assert before==after and clean and len(set(nodeids))==len(nodeids)==37;assert all(p['rc']==0 and p['nodes']==p['expected'] for p in parts)

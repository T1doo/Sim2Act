import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path('/workspace/Sim2Act-bounded-product-candidate');out=Path('/tmp/natural-activation-root/final-9406');out.mkdir(exist_ok=True)
modules=['test_natural_ui_drain.py','test_natural_activation.py','test_natural_activation_flow.py','test_natural_goal_planning.py','test_natural_goal_confirmation.py','test_natural_goal_ui.py','test_goal_card_runs.py','test_goal_card_run_ui.py','test_goal_cards.py','test_goal_candidates.py','test_foundation.py','test_contract_semantics.py','test_model_identity.py','test_model_faults.py','test_protocol_pool.py','test_protocol_jobs.py']
def sources():
    paths=[]
    for folder in ('src','tests','scripts','.github'):
        paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();before=sources()
(out/'source-before.json').write_text(json.dumps({'head':head,'files':before},indent=2)+'\n')
env=dict(os.environ,PYTHONPATH='src',NODE_PATH='/workspace/browser-tools/node_modules');base=[sys.executable,'-m','pytest'];nodes=['tests/'+m for m in modules]
with (out/'collection.log').open('w') as f:
    result=subprocess.run(base+['--collect-only','-q']+nodes,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
assert result.returncode==0
collection=[l.strip() for l in (out/'collection.log').read_text().splitlines() if l.startswith('tests/') and '::' in l]
assert len(collection)==len(set(collection))
(out/'collection.json').write_text(json.dumps(collection,indent=2)+'\n')
assert sources()==before
with (out/'target.log').open('w') as f:
    result=subprocess.run(base+['-q','--junitxml='+str(out/'junit.xml')]+nodes,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
after=sources();(out/'source-after.json').write_text(json.dumps({'head':head,'files':after,'equal':after==before},indent=2)+'\n')
assert after==before
print(json.dumps({'head':head,'collection_count':len(collection),'source_files':len(before),'source_unchanged':True,'exit_code':result.returncode}))
print('\n'.join((out/'target.log').read_text().splitlines()[-5:]))
sys.exit(result.returncode)

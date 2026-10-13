import hashlib,json,os,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/pa-natural-operations-evidence-20261013/independent')
repo=Path('/workspace/Sim2Act-pa-provider')
source=root/'baseline147-source'
expected=json.loads((root/'baseline147-source-map.json').read_text())
def source_map():
 return {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
assert source_map()==expected['files']
command=['/workspace/Sim2Act/.venv/bin/python','-m','pytest','-q',
 str(root/'baseline-probe-tests/test_natural_spec_callback_reads.py')+'::test_event_authority_change_precedes_private_cell_evaluation[expiry-SPEC_STEP_VERIFIED]',
 str(root/'baseline-probe-tests/test_natural_spec_callback_reads.py')+'::test_event_authority_change_precedes_private_cell_evaluation[expiry-SPEC_COMMITTED]',
 '--basetemp='+str(root/'baseline-expiry-tmp'),'--junitxml='+str(root/'baseline-expiry.xml'),'-o','cache_dir='+str(root/'baseline-expiry-cache')]
env=dict(os.environ);env.pop('SIM2ACT_TEST_DATABASE_URL',None)
safe={'PYTHONPATH':str(source/'src')+':'+str(repo/'tests'),'NODE_PATH':'/workspace/node-tools/node_modules','PYTHONDONTWRITEBYTECODE':'1'};env.update(safe)
(root/'baseline-expiry-command.json').write_text(json.dumps({'argv':command,'cwd':str(repo),'explicit_environment':safe,'baseline_head':expected['head'],'intent':'Expected historical privacy-ordering red; current frozen observer including runtime intent IDs; not current candidate acceptance'},indent=2)+'\n')
start=time.time()
with (root/'baseline-expiry.stdout').open('w') as out,(root/'baseline-expiry.stderr').open('w') as err:
 result=subprocess.run(command,cwd=repo,env=env,stdout=out,stderr=err)
post=source_map(); changes=[n for n in sorted(set(post)|set(expected['files'])) if post.get(n)!=expected['files'].get(n)]
(root/'baseline-expiry-source-after.json').write_text(json.dumps({'head':expected['head'],'files':post},indent=2,sort_keys=True)+'\n')
cases=ET.parse(root/'baseline-expiry.xml').getroot().findall('.//testcase')
proof={'returncode':result.returncode,'wall_seconds':time.time()-start,'started':start,'source_changes':changes,'selected':len(cases),'failed':sum(c.find('failure') is not None for c in cases),'errors':sum(c.find('error') is not None for c in cases),'skipped':sum(c.find('skipped') is not None for c in cases),'xml_sha256':hashlib.sha256((root/'baseline-expiry.xml').read_bytes()).hexdigest(),'expected_historical_red':True}
proof['passed']=proof['selected']-proof['failed']-proof['errors']-proof['skipped']
(root/'baseline-expiry-result.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))
raise SystemExit(result.returncode or bool(changes))

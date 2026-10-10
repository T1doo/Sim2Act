from pathlib import Path
import json,subprocess,hashlib,sys
r=Path('/tmp/sim2act-dag-new-csv-independent-20261010/final-readback-fix');repo=Path('/workspace/Sim2Act');sha='e76ff7545d1c9cb74592e130dcef3d4b81e78c41';old='c9ea689a27308b94c998ced5cd0cb3fd981a5c49';manifest=json.loads(Path('/tmp/sim2act-dag-new-csv-20261010/source-freeze-final-readback.json').read_text());assert manifest['source_sha']==sha;m={x['path']:x['sha256'] for x in manifest['files']};assert len(m)==373 and sum(p.startswith('src/') for p in m)==70
for p,h in m.items():assert hashlib.sha256((repo/p).read_bytes()).hexdigest()==h==hashlib.sha256(subprocess.check_output(['git','show',sha+':'+p],cwd=repo)).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==sha;delta=subprocess.check_output(['git','diff','--name-only',old+'..'+sha],cwd=repo,text=True).splitlines();assert delta==['src/sim2act/web/csv-dag.js']
for p,h in m.items():
 if p!='src/sim2act/web/csv-dag.js':assert hashlib.sha256(subprocess.check_output(['git','show',old+':'+p],cwd=repo)).hexdigest()==h
out={'source_sha':sha,'count':373,'products':70,'Git_worktree_author_match':True,'only_delta_vs_c9':delta,'unchanged_other372_and_src69_backend_all':True,'files':m};(r/('source-'+sys.argv[1]+'.json')).write_text(json.dumps(out,indent=2));print('373/70 exact e76, 372 unchanged c9')

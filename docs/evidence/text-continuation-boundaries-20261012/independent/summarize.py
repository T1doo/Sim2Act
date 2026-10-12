import hashlib,json,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
out=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results={};nodes=[]
for name,count in [('backend',100),('ui',4),('independent',8)]:
    ts=ET.parse(out/(name+'.xml')).findall('.//testcase');assert len(ts)==count
    batch=[]
    for t in ts:
        status=next((s.upper() for s in ['failure','error','skipped'] if t.find(s) is not None),'PASS')
        row={'suite':name,'id':t.attrib['classname']+'::'+t.attrib['name'],'status':status,'seconds':float(t.attrib.get('time',0))}
        batch.append(row)
    assert len({x['id'] for x in batch})==count
    nodes+=batch
    ex=json.loads((out/(name+'-exit.json')).read_text());assert ex['exit_code']==0
    results[name]={'nodes':count,'counts':dict(Counter(x['status'] for x in batch)),'exit_code':ex['exit_code'],'wall_seconds':ex['wall_seconds'],'junit_sha256':sha(out/(name+'.xml')),'log_sha256':sha(out/(name+'.log'))}
assert len({x['id'] for x in nodes})==112 and all(x['status']=='PASS' for x in nodes)
before=json.loads((out/'source-before.json').read_text());after=json.loads((out/'source-after.json').read_text());assert before==after
old=json.loads(Path('/tmp/text-continuation-independent-final-v3-20261012/candidate-freeze.json').read_text())['source_tests']
cur=after['source_tests'];delta={'added':[p for p in cur if p not in old],'changed':[p for p in old if p in cur and old[p]!=cur[p]],'removed':[p for p in old if p not in cur]}
unchanged_test_files=['tests/test_text_continuations.py','tests/test_text_continuation_ui.py','tests/text_continuation_ui.cjs']
assert all(old[p]==cur[p] for p in unchanged_test_files)
ui=[]
web=Path('/workspace/Sim2Act/src/sim2act/web')
for p in sorted((out/'ui').glob('*.json')):
    if p.name.endswith(('-exit.json','-sql.json')):continue
    proof=json.loads(p.read_text());ex=json.loads(p.with_name(p.stem+'-exit.json').read_text());sql=json.loads(p.with_name(p.stem+'-sql.json').read_text())
    assert proof['status']=='PASS' and ex['exit_code']==0 and ex['workers']==1 and not sql['private_evaluations']
    assert len(proof['static_resource_loads'])==20*proof['boots']
    for asset in proof['static_resource_loads']:
        assert asset['sha256']==sha(web/(asset['path'].lstrip('/') or 'index.html'))
    ui.append({'scenario':p.stem,'checks':len(proof['checks']),'boots':proof['boots'],'assets':len(proof['static_resource_loads']),'workers':ex['workers'],'private_cells':len(sql['private_evaluations'])})
prior=json.loads((out/'prior-history-before.json').read_text());active='/workspace/Sim2Act/docs/evidence/text-continuation-boundaries-20261012/regression-final.log'
immutable={p:h for p,h in prior.items() if p!=active}
changes=[p for p,h in immutable.items() if not Path(p).exists() or sha(Path(p))!=h];assert not changes
(out/'history-manifest.json').write_text(json.dumps(immutable,indent=2)+'\n')
old_root=Path('/tmp/text-continuation-independent-final-v3-20261012')
audit=[]
for manifest in ['manifest.json','history-manifest.json']:
    j=json.loads((old_root/manifest).read_text());files=j['files'] if manifest=='manifest.json' else j
    bad=[]
    for path,h in files.items():
        file=Path(path) if Path(path).is_absolute() else old_root/path
        if not file.exists() or sha(file)!=h:bad.append(str(file))
    assert not bad
    audit.append({'manifest':str(old_root/manifest),'sha256':sha(old_root/manifest),'files_verified':len(files),'mismatches':bad})
red=[]
for f in sorted(Path('/workspace/Sim2Act/docs/evidence/text-continuation-boundaries-20261012').glob('red*.xml')):
    ts=ET.parse(f).findall('.//testcase')
    red.append({'file':str(f),'sha256':sha(f),'nodes':len(ts),'counts':{s:sum(t.find(s) is not None for t in ts) for s in ['failure','error','skipped']}})
summary={'classification':'LIMITED_PASS_112_UNIQUE_NODES','suites':results,'unique_nodes':len(nodes),'counts':dict(Counter(n['status'] for n in nodes)),'source':{k:v for k,v in after.items() if k!='source_tests'},'frozen_delta_from_previous_401':delta,'old_assertions_polling_byte_identical':unchanged_test_files,'ui':ui,'ui_totals':{k:sum(x[k] for x in ui) for k in ['checks','boots','assets','workers','private_cells']},'boundary_json_proofs':len(list((out/'boundary-proofs').glob('*.json'))),'independent_json_proofs':len(list((out/'independent-proofs').glob('*.json'))),'history_preservation':{'checked':len(immutable),'mismatches':changes,'active_root_log_excluded':active,'prior_manifests_verified':audit,'old_red_junit':red},'root_291':'NOT independently parsed in this report; running separately, no counts added','not_run':['PG','Windows','native browser/socket','real/paid model','customer oldDB upgrade','human semantic acceptance','complete P-A/P-B','remote CI','cancelled precise old install race/probe'],'limits':['Synthetic persisted corruption only; no real attack or response disclosure assertion','Old known implementation anchors 233/a747 only, original AUTH TTL fixture clocks replayed','Bounded history up to64; no exhaustive all-database mutation proof']}
(out/'final-nodes.json').write_text(json.dumps(nodes,indent=2)+'\n')
(out/'final-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['source','history_preservation']},indent=2))

import hashlib,json,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
out=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
nodes=[];suites={}
for name,expected in [('backend',43),('ui',4),('independent',7),('adversarial-ui',2)]:
    cases=ET.parse(out/(name+'.xml')).findall('.//testcase');assert len(cases)==expected
    batch=[]
    for t in cases:
        status=next((s.upper() for s in ['failure','error','skipped'] if t.find(s) is not None),'PASS')
        batch.append({'suite':name,'id':t.attrib['classname']+'::'+t.attrib['name'],'status':status,'seconds':float(t.attrib.get('time',0))})
    ex=json.loads((out/(name+'-exit.json')).read_text());assert ex['exit_code']==0
    nodes+=batch;suites[name]={'nodes':len(batch),'counts':dict(Counter(n['status'] for n in batch)),'exit_code':ex['exit_code'],'wall_seconds':ex['wall_seconds'],'log_sha256':sha(out/(name+'.log')),'junit_sha256':sha(out/(name+'.xml'))}
assert len(nodes)==len({n['id'] for n in nodes})==56 and all(n['status']=='PASS' for n in nodes)
before=json.loads((out/'source-before.json').read_text());after=json.loads((out/'source-after.json').read_text());assert before==after
history=json.loads((out/'history-before.json').read_text());bad=[f for f,h in history.items() if not Path(f).exists() or sha(Path(f))!=h];assert not bad
(out/'history-manifest.json').write_text(json.dumps(history,indent=2)+'\n')
ui=[];web=Path('/workspace/Sim2Act/src/sim2act/web')
for p in [*sorted((out/'ui').glob('*-page.json')),*sorted(out.glob('*-page.json'))]:
    j=json.loads(p.read_text());assert j['status']=='PASS'
    for a in j['static_resource_loads']:assert a['sha256']==sha(web/(a['path'].lstrip('/') or 'index.html'))
    ui.append({'proof':str(p.relative_to(out)),'checks':len(j['checks']),'assets':len(j['static_resource_loads']),'boots':j['boots'],'status':j['status']})
checks={}
for p in sorted((out/'independent-proofs').glob('*.json')):
    j=json.loads(p.read_text());assert j['database_unchanged']
    if 'protected_cell_evaluations' in j:assert not j['protected_cell_evaluations']
    checks[p.name]={k:v for k,v in j.items() if k in ['status','code','database_unchanged','protected_cell_evaluations','typed_insert_hook_hits','derived_receipts']}
width=json.loads((out/'input-width.json').read_text());assert width['status']==width['source_status']==409 and width['database_unchanged']
header=[n for n in nodes if 'test_exact_independent_accepted_header_rejected_if_changed' in n['id']];assert len(header)==2 and all(n['status']=='PASS' for n in header)
summary={'classification':'LIMITED_PASS_R11_56_UNIQUE_NODES','suites':suites,'unique_nodes':56,'counts':dict(Counter(n['status'] for n in nodes)),'source':{k:v for k,v in after.items() if k!='files'},'r10_r11_bridge':json.loads((out/'r10-r11-file-bridge.json').read_text()),'header_test_nodes_already_in_backend43':header,'no_double_count':'43 backend +4 original UI overlap parent47; separate extra7 backend +2 UI; do not add parent R10 535/old291/CSV199','ui':ui,'ui_totals':{k:sum(r[k] for r in ui) for k in ['checks','assets','boots']},'normal_ui_cold_workers':4,'independent_evidence':checks,'input_width':width,'history_verified_files':len(history),'history_mismatches':bad,'no_active_known_processes':json.loads((out/'no-active-processes.json').read_text()),'not_run':['PG','Windows','native browser/socket','real/paid model','customer oldDB upgrade','human semantic/owner acceptance','complete P-A/P-B','CI','precise cancelled install window PERMANENT_NOT_VERIFIED','late hash identity controlled scenario'],'remaining_core_findings':[],'parent_r10_535':'Parent-provided terminal counts only; not independently parsed here, never presented as R11 full execution'}
(out/'final-summary.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'final-nodes.json').write_text(json.dumps(nodes,indent=2)+'\n');print('56 PASS, header2 within43, history',len(history),'ui',summary['ui_totals'])

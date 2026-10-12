import hashlib,json,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
out=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
suites={};executions=[];final={}
for name in ['backend','ui','independent','adversarial-ui','expiry-corrected']:
    cases=ET.parse(out/(name+'.xml')).findall('.//testcase');rows=[]
    for case in cases:
        status=next((s.upper() for s in ['failure','error','skipped'] if case.find(s) is not None),'PASS')
        r={'suite':name,'id':case.attrib['classname']+'::'+case.attrib['name'],'status':status,'seconds':float(case.attrib.get('time',0))};rows.append(r)
        if r['id'] in final:
            assert name=='expiry-corrected' and final[r['id']]['status']=='FAILURE' and r['status']=='PASS'
            r['supersedes']='Expiry fixture lease timeout/code assertion failure; original log/XML intact'
        final[r['id']]=r
    executions+=rows
    ex=json.loads((out/(name+'-exit.json')).read_text());suites[name]={'nodes':len(rows),'counts':dict(Counter(r['status'] for r in rows)),'exit_code':ex['exit_code'],'wall_seconds':ex['wall_seconds'],'log_sha256':sha(out/(name+'.log')),'junit_sha256':sha(out/(name+'.xml'))}
assert len(final)==54 and all(r['status']=='PASS' for r in final.values()) and len(executions)==55
before=json.loads((out/'source-before.json').read_text());after=json.loads((out/'source-after.json').read_text());assert before==after
history=json.loads((out/'history-before.json').read_text());bad=[p for p,h in history.items() if not Path(p).exists() or sha(Path(p))!=h];assert not bad
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
extra=json.loads((out/'input-width.json').read_text());assert extra['database_unchanged'] and extra['status']==extra['source_status']==409
summary={'classification':'LIMITED_PASS_54_UNIQUE_FINAL_NODES_WITH_ORIGINAL_FIXTURE_FAILURE_RETAINED','suites':suites,'unique_final_nodes':len(final),'final_counts':dict(Counter(r['status'] for r in final.values())),'raw_executions':len(executions),'raw_counts':dict(Counter(r['status'] for r in executions)),'source':{k:v for k,v in after.items() if k!='files'},'exact_overlap_with_parent_selection':'41 backend +4 normal UI defined by same two repository modules; independently executed, never sum with parent45/291/CSV','extra_checks':{'backend':7,'controlled_ui':2},'ui':ui,'ui_totals':{'checks':sum(x['checks'] for x in ui),'assets':sum(x['assets'] for x in ui),'boots':sum(x['boots'] for x in ui)},'normal_ui_cold_workers':4,'private_scope_evidence':checks,'input_width':extra,'history_files_verified':len(history),'history_mismatches':bad,'no_active_known_processes':json.loads((out/'no-active-processes.json').read_text()),'not_run':['PG','Windows','native browser/socket','real/paid models','customer oldDB upgrade','human semantic acceptance','full P-A/P-B acceptance','CI','precise cancelled install window (PERMANENT_NOT_VERIFIED)','late hash identity adversarial (not executed; read-only GET/current-outcome contract statically reviewed)']}
(out/'final-summary.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'final-nodes.json').write_text(json.dumps(list(final.values()),indent=2)+'\n');(out/'all-executions.json').write_text(json.dumps(executions,indent=2)+'\n')
print('final',len(final),'raw',len(executions),'raw counts',summary['raw_counts'],'history',len(history),'ui',summary['ui_totals'])

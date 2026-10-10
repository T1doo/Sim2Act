import json,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
r=Path('/tmp/sim2act-dag-new-csv-20261010');repo=Path('/workspace/Sim2Act')
freeze=json.loads((r/'source-freeze-complete-readback.json').read_text())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==freeze['source_sha']
for f in freeze['files']:
    b=(repo/f['path']).read_bytes();assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['path']
(r/'source-after-final.json').write_text(json.dumps(dict(source_sha=freeze['source_sha'],non_docs=373,src=70,all_Git_worktree_bytes_match=True,all_Python_unchanged=True),indent=2)+'\n')
def suite(name):
    x=ET.parse(r/(name+'.xml')).getroot();s=x.find('testsuite')
    cases=[dict(id=c.attrib['classname']+'::'+c.attrib['name'],seconds=float(c.attrib['time']),passed=not any(c.find(v)is not None for v in ['failure','error','skipped'])) for c in s.findall('testcase')]
    return dict(run=name,tests=int(s.attrib['tests']),failed=int(s.attrib['failures']),errors=int(s.attrib['errors']),skipped=int(s.attrib['skipped']),seconds=float(s.attrib['time']),cases=cases)
final=[suite(n) for n in ['sqlite12-final','pg1-complete-readback','pg2-final']]
assert [x['tests'] for x in final]==[12,1,2]
assert all(x['failed']==x['errors']==x['skipped']==0 and all(c['passed'] for c in x['cases']) for x in final)
ui=[]
for name in ['sqlite12-final','pg1-complete-readback','pg2-final']:
    for p in sorted((r/name).rglob('results.json')):
        d=json.loads(p.read_text());assert d['status']=='PASS'
        ui.append(dict(path=str(p.relative_to(r)),checks=len(d['checks']),pages=d.get('pages'),assets=d.get('assets'),database='PG' if name.startswith('pg') else 'SQLite'))
result=dict(source_sha=freeze['source_sha'],final_source_tests=final,actual_HTTP_UI=ui,backend_byte_bridge=dict(SQLite_unique_cases=22,PostgreSQL_cases=22,source='c9ea689a27308b94c998ced5cd0cb3fd981a5c49',all_Python_identical=True,src69_other_than_JS_identical=True,not_reexecuted_on_final_JS=True),previous_SQLite30='15 passing observations plus corrected remaining15; original harness fail retained',previous_PG30='29PASS1material DOMidle10; unchanged retry failed;392 ande76 failed, final709 specific3 PASS',final_budget=dict(DOM_seconds=10,Node_seconds=90,raised=False),historical_report_idle6='OPEN',historical_PG_resources_history_future10='OPEN',overall='NOT_ACCEPTED',PROJECT='PENDING/BLOCKED_PARTIAL',LIVE=0,real_model_requests=0)
(r/'final-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(source=freeze['source_sha'],tests=[{k:v for k,v in x.items() if k!='cases'} for x in final],UI_artifacts=len(ui),UI_checks=sum(x['checks'] for x in ui))))

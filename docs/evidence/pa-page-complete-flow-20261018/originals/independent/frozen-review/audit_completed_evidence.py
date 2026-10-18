"""Independent raw evidence readback only; no product invocation or test rerun."""
from pathlib import Path
import json,hashlib,re,xml.etree.ElementTree as ET,sqlite3
OUT=Path(__file__).parent;BASE=Path('/workspace/pa-page-complete-evidence-20261018');ROOT=Path('/workspace/Sim2Act')
manifest=json.loads((OUT/'source-manifest.json').read_text());prod=manifest['files'];checks=[]
def load(p):return json.loads(p.read_text())
def check(value,label):
 assert value,label
 checks.append(label)
def sha(b):return hashlib.sha256(b).hexdigest()
result={'classification':'NON_AUTHOR_COMPLETED_RAW_EVIDENCE_RECALCULATION_NOT_AUTHOR_TEST_EXECUTION','freeze':manifest['freeze'],'batches':{}}
for name in ('full-pa','shared'):
 suite=next(ET.parse(BASE/(name+'.xml')).getroot().iter('testsuite'));a=suite.attrib
 check(a['errors']==a['failures']==a['skipped']=='0',name+' XML no failures/errors/skips')
 named=[t.attrib['name'] for t in suite.iter('testcase')];check(len(named)==int(a['tests']),name+' all XML cases named/count exact')
 result['batches'][name]={'completed_tests':int(a['tests']),'seconds':float(a['time']),'names':named}
check(result['batches']['full-pa']['completed_tests']==1 and result['batches']['full-pa']['names']==['test_natural_spec_page_actual_nodes_and_cold_material[valid]'],'exact original full valid parameter completed')
case=BASE/'full-pa/test_natural_spec_page_actual_0';proof=load(case/'results.json');summary=load(case/'progress-summary.json');events=[json.loads(line) for line in (case/'progress.jsonl').read_text().splitlines() if line.strip()]
check(proof['status']=='PASS' and proof['scenario']=='valid' and len(proof['checks'])>=22,'original valid page result PASS with original checks')
check(summary['provider_requests']==3 and summary['runtime_requests']==2 and not summary['watchdog_fired'] and summary['error_count']==0,'3 synthetic generation + 2 runtime requests, no watchdog/error')
check(len(load(case/'model-wire.json'))==3 and len(load(case/'runtime-wire.json'))==2,'actual raw captured synthetic wire lengths')
check(load(case/'errors.json')==[],'observer error archive empty')
end=events[-1];check(end['kind']=='test_end' and end['passed'] and end['node_exit_code']==0,'incremental trace reaches successful test_end and Node0')
workers=[r for r in events if r['kind']=='worker_end'];check([r['command'] for r in workers]==['provider-worker','cold-worker'],'actual two original normal Worker commands finished')
assets=proof['static_resource_loads'];boots=sorted({r['boot'] for r in assets});check(boots==[1,2],'warm and independent cold page boots')
expected_assets={'/','/app.css',*re.findall(r'<script[^>]*src="([^"]+)"',(ROOT/'src/sim2act/web/index.html').read_text())}
for boot in boots:check({r['path'] for r in assets if r['boot']==boot}==expected_assets,'all served assets present for boot '+str(boot))
for asset in assets:
 path='src/sim2act/web/'+(asset['path'].lstrip('/') or 'index.html');check(asset['status']==200 and asset['sha256']==prod[path]['sha256'],'exact frozen served asset '+asset['path'])
for name,value in proof['loaded_source_sha256'].items():check(value==prod['src/sim2act/web/'+name]['sha256'],'page loaded_source freeze '+name)
http=[]
for p in sorted((case/'http').glob('*-metadata.json')):
 d=load(p);body=(case/d['response_file']).read_bytes();check(sha(body)==d['response_sha256'] and len(body)==d['response_bytes'],'original HTTP body hash '+p.name);http.append((d,body))
check(len(http)==summary['http_responses'],'all raw HTTP responses present')
requests=proof['requests'];check(sum(r['method']=='POST' and r['path'].endswith('/application-runs') for r in requests)==1,'one generation submission')
check(sum(r['method']=='POST' and r['path'].endswith('/bindings') for r in requests)==1,'one material binding submission')
check(sum(r['method']=='POST' and re.fullmatch(r'/api/internal/instances/[^/]+/runs',r['path']) is not None for r in requests)==1,'one runtime submission')
artifacts=[json.loads(body) for d,body in http if d['path'].endswith('/spec-artifact') and d['status']==200]
check(len(artifacts)==3,'explicit view JSON Markdown each obtain fresh authorized artifact')
for value in artifacts:
 resource=value['resource'];check(sha(resource['content'].encode())==resource['hash'] and value['owner_acceptance']=='PENDING' and value['semantic_status']=='UNKNOWN' and value['new_model_requests']==value['project_writes']==0,'real artifact content/hash and unchanged semantic/effect boundary')
check(all(a==artifacts[0] for a in artifacts),'same exact original saved artifact in all three reads')
check(len(proof['downloads'])==2,'two actual download byte captures')
for d in proof['downloads']:
 check('garden sensor' in d['content'] and 'desk lamp' not in d['content'],'download uses cold material bytes '+d['name'])
 if d['name'].endswith('.json'):check(d['content']==artifacts[0]['resource']['content'] and json.loads(d['content'])['owner_acceptance']=='PENDING','JSON actual download exact saved resource bytes')
 else:check(d['name'].endswith('.md') and d['content']==artifacts[0]['markdown_view'],'Markdown actual download exact saved view bytes')
# Read finished synthetic fixture metadata without running product or mutating DB.
db=case/'fixture.db';before=sha(db.read_bytes());c=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True);c.row_factory=sqlite3.Row
runs=[dict(r) for r in c.execute("select id,status,json_extract(context,'$.requests') requests,json_extract(context,'$.spec_family') family from runs")];i=[dict(r) for r in c.execute('select id,data_version from internal_instances')];c.close()
check(sha(db.read_bytes())==before,'finished fixture read-only bytes unchanged')
check(len(runs)==2 and sorted(r['status'] for r in runs)==['PARTIAL','SUCCEEDED'] and len(i)==1 and i[0]['data_version']==1,'fresh original generated candidate plus successful single cold business Run')
check(all(r['id'] not in {'run_dc5bdcd639164c6fbb66cac021b2a9c5','run_1358a115f9164ca6a05533cf7f2247d2'} for r in runs),'fresh fixture uses independent Run identities from interrupted case')
record_case=BASE/'shared/test_local_record_page_explici0';nav=load(record_case/'run-summary.json');page=load(record_case/'page-result.json');check(nav['status']=='PASS' and nav['page_worker_calls']==0 and nav['fixture_worker_calls']==1 and nav['real_model_requests']==0,'shared record navigation is actual HTTP fixture Worker1/pageWorker0/model0')
check(load(record_case/'source-changes.json')=={},'shared navigation source before/after unchanged')
result.update(status='PASS',assertions=len(checks),original_page_checks=len(proof['checks']),page_requests=len(requests),served_assets=len(assets),page_http_responses=len(http),worker_commands=[r['command'] for r in workers],synthetic_provider_requests=3,synthetic_runtime_requests=2,real_models='NOT_RUN_MOCK_TRANSPORT_ONLY',fresh_fixture_sha256=before,source_production_count=132,source_test_input_count=7,shared_navigation_checks=len(page['checks']),checks=checks)
(OUT/'completed-evidence-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))

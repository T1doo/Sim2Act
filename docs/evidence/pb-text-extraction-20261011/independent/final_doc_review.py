from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET,re,datetime,subprocess
root=Path('/workspace/Sim2Act');base=root/'docs/evidence/pb-text-extraction-20261011';out=Path('/tmp/pb-text-extraction-review-20261011')
freeze=json.loads((base/'candidate3-source-freeze.json').read_text())['sha256']
first=ET.parse(base/'candidate3.xml').findall('.//testcase');retry=ET.parse(base/'candidate3-pa-corrected.xml').findall('.//testcase')
key=lambda t:(t.attrib['classname'],t.attrib['name'])
first_failed={key(t) for t in first if t.find('failure') is not None};first_pass={key(t) for t in first if all(t.find(k) is None for k in ['failure','error','skipped'])};retry_pass={key(t) for t in retry if all(t.find(k) is None for k in ['failure','error','skipped'])};skips=[t for t in first if t.find('skipped') is not None]
assert len(first)==462 and len(first_failed)==34 and len(first_pass)==418 and len(retry)==34 and first_failed==retry_pass and not (retry_pass&first_pass) and len(skips)==10
assert len({key(t) for t in first})==462 and all('PostgreSQL' in t.find('skipped').attrib['message'] for t in skips)
proof=json.loads((base/'candidate3-two-run-coverage-proof.json').read_text());assert proof['nodes']['repaired']==sorted([list(k) for k in retry_pass]);assert proof['same_source_two_run_unique_coverage']=={'pass':452,'skip':10,'deselected':1,'selected':462}
cmd=json.loads((base/'candidate3-pa-corrected-command.json').read_text());assert cmd['NODE_PATH']=='/workspace/node-tools/node_modules' and cmd['jsdom_resolved']=='/workspace/node-tools/node_modules/jsdom/lib/api.js';expected={a.replace('tests/test_goal_text_ui.py::','tests.test_goal_text_ui::') for a in cmd['failed_nodes']};assert expected=={'::'.join(k) for k in first_failed}
for n in ['candidate3-author-source-after-full.json','candidate3-author-source-after-correction.json']:
 d=json.loads((base/n).read_text());assert d['source_count']==365 and not d['differences'] and d['sha256']==freeze
current_source_changes=[p for p,h in freeze.items() if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h];assert not current_source_changes
asset_errors=[];actual=[];controls=[];mime_counts={}
for p in sorted((base/'candidate3-pa-corrected-pages').glob('*.json')):
 d=json.loads(p.read_text());assert d['status']=='PASS'
 if d.get('classification')=='CONTROLLED_LOCAL_SOURCE_JSDOM_MICROTASK':
  assert d['source_sha256']==freeze['src/sim2act/web/owner-review.js'];assert d['http']=='NOT_RUN' and d['worker']=='NOT_RUN';controls.append({'file':p.name,'checks':len(d['checks'])});continue
 loads=d['static_resource_loads'];actions=[a for a in d['user_actions'] if a.get('event')=='native DOM dispatch'];assert all(a['visible'] and a['enabled'] for a in actions)
 for r in loads:
  name='index.html' if r['path']=='/' else r['path'].lstrip('/');f='src/sim2act/web/'+name;mime='text/html' if name.endswith('.html') else 'text/css' if name.endswith('.css') else 'text/javascript';mime_counts[r['content_type']]=mime_counts.get(r['content_type'],0)+1
  if r['status']!=200 or r['content_type'].split(';')[0]!=mime or r['bytes']!=len((root/f).read_bytes()) or r['sha256']!=freeze[f]:asset_errors.append({'file':p.name,'path':r['path']})
 boots={r['boot'] for r in loads};assert all(sum(r['boot']==b for r in loads)==19 for b in boots);actual.append({'file':p.name,'checks':len(d['checks']),'gestures':len(actions),'boots':len(boots),'assets':len(loads),'diagnostic_summary_count':len(d['user_actions'])-len(actions)})
assert len(actual)==29 and len(controls)==5 and not asset_errors
totals={k:sum(r[k] for r in actual) for k in ['checks','gestures','boots','assets','diagnostic_summary_count']};assert totals=={'checks':1307,'gestures':1261,'boots':59,'assets':1121,'diagnostic_summary_count':2};assert sum(r['checks'] for r in controls)==30
reported=json.loads((base/'candidate3-pa-corrected-metrics.json').read_text());assert reported['totals']['gestures']==1261 and reported['mime_verified'] is True
archive=json.loads((out/'archive-manifest.json').read_text());a_changes=[r['path'] for r in archive['files'] if hashlib.sha256((out/r['path']).read_bytes()).hexdigest()!=r['sha256']];repo_changes=[r['path'] for r in archive['files'] if not (base/'independent'/r['path']).exists() or hashlib.sha256((base/'independent'/r['path']).read_bytes()).hexdigest()!=r['sha256']];assert not a_changes and not repo_changes
paths=[root/'docs/F2/PBTextExtraction20261011.md',root/'docs/F2/DeliveryRemainingChecklist.md',base/'README.md'];docs=[];missing=[]
for p in paths:
 text=p.read_text();scoped=text if p.name!='DeliveryRemainingChecklist.md' else text.split('2026-10-11 接续 F2-T03 / AT-10 的')[-1]
 for target in re.findall(r'\]\(([^)]+)\)',scoped):
  if '://' in target or target.startswith('#'):continue
  if not (p.parent/target.split('#')[0]).resolve().exists():missing.append({'document':str(p.relative_to(root)),'target':target})
 docs.append({'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert not missing
readme=(base/'README.md').read_text();assert '1261' in readme and '2条' in readme or ('1261' in readme and '2个' in readme)
ps=subprocess.check_output(['ps','-eo','pid=,args='],text=True)
active=[]
for line in ps.splitlines():
 if re.search(r'/python(?:\d(?:\.\d+)?)? -m pytest(?: |$)',line) or re.search(r' node (?:\S*/)?(?:goal_text_ui|registered_text_ui|owner_read_order_errors)\.cjs(?: |$)',line):
  active.append(line.strip())
record={'reviewed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','classification':'READ_ONLY_FINAL_DOCUMENT_AND_EXISTING_EVIDENCE_REVIEW_NOT_TEST_EXECUTION','documents':docs,'first_round':{'passed':418,'failed':34,'skipped':10,'errors':0,'all_failed_missing_jsdom':True},'corrected_round':{'passed':34,'failed':0,'errors':0,'skipped':0,'NODE_PATH':cmd['NODE_PATH'],'jsdom_resolved':cmd['jsdom_resolved'],'same_exact_failed_node_set':True,'no_overlap_original_passes':True},'same_source_two_actual_runs':{'unique_passed':452,'skipped_pg':10,'deselected':1,'collected':463,'selected':462,'one_whole_green_run_claimed':False},'page_evidence':{'actual_http_jsdom_pages':29,'totals':totals,'controlled_local_source_microtasks':5,'controlled_checks':30,'asset_mime_counts':mime_counts,'asset_status_mime_bytes_sha_errors':asset_errors,'every_boot_exactly19_assets':True},'source':{'count':365,'author_after_full_map_matches':True,'author_after_correction_map_matches':True,'current_source_changes':current_source_changes},'archive224':{'original_changes':a_changes,'repo_copy_changes':repo_changes,'manifest_sha256':hashlib.sha256((out/'archive-manifest.json').read_bytes()).hexdigest()},'missing_local_links':missing,'scope_verified':['Technical PASS stays separate from actual human semantic acceptance; LIVE0, ownerPENDING/unsupported newtask entry, UNKNOWN and pubfalse preserved.','Original full GoalCard remains provenance and original authorization/evidence audit remains required; no source retirement/fullPB claim.','All original module-path errors, failed product probes, withdrawn candidates and fixture failures retained and correctly bounded.','Actual29 HTTP/JSDOM pages and5local-source controls separated; native DOM dispatch refers to JSDOM and not nativeOS/browser.','The1263 combined array length has been corrected to1261 actual gestures plus2diagnostic summaries. Initial document metric assertion discrepancy preserved in doc-review-first-metric-error.json.','Real model/paid API, PG, Windows, nativebrowser, realowner semantics, oldsource upgrade, fullPA/PB/AT10 and exactSHA remoteCI remain NOT_RUN.'],'new_document_blockers':[],'no_tests_rerun':True,'outside_original224_seal':True,'active_related_pytest_or_node_drivers':active,'pending_delivery_scope':'Commit/push/ref and old-evidence Git tree checks remain parent delivery steps, not operations performed by this reviewer.'}
assert not active,active
p=out/'doc-review.json';assert not p.exists();p.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','documents':docs,'doc_review_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'actual_metrics':totals,'asset_mime_counts':mime_counts,'source_changes':current_source_changes,'archive_original_changes':a_changes,'archive_repo_changes':repo_changes,'active_related_test_processes':active},indent=2))

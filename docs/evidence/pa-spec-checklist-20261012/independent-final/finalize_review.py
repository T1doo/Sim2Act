from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
from collections import Counter
root=Path(__file__).resolve().parent
prior=Path('/tmp/pa-spec-checklist-independent-20261012/dynamic-final-a396-20261012')
repo=Path('/workspace/Sim2Act-pa-provider')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def result(path):
 tree=ET.parse(path);tests=tree.findall('.//testcase');cases=[]
 for t in tests:
  assert t.get('name') and t.get('classname'), 'Unnamed interrupted XML placeholder must not count'
  state='FAIL' if t.find('failure') is not None else 'ERROR' if t.find('error') is not None else 'SKIP' if t.find('skipped') is not None else 'PASS'
  cases.append({'id':t.get('classname')+'::'+t.get('name'),'state':state,'seconds':float(t.get('time','0'))})
 assert len({x['id'] for x in cases})==len(cases)
 return {'xml':str(path),'xml_sha256':sha(path),'counts':dict(Counter(x['state'] for x in cases)),'named_unique':len(cases),'cases':cases,'suite_metadata':[dict(x.attrib) for x in tree.findall('.//testsuite')]}
selected=result(root/'selected.xml');extra=result(prior/'extra.xml')
exitmeta=json.loads((root/'selected-exit.json').read_text())
assert exitmeta['returncode']==0
assert selected['named_unique']==63 and selected['counts']=={'PASS':63}
assert extra['named_unique']==16 and extra['counts']=={'PASS':16}
assert not {x['id'] for x in selected['cases']} & {x['id'] for x in extra['cases']}
before=json.loads((root/'source-before.json').read_text())
names=subprocess.check_output(['git','ls-files','--','src','tests','pyproject.toml'],cwd=repo,text=True).splitlines()
after={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=repo,text=True).strip(),'files':{n:sha(repo/n) for n in names if (repo/n).is_file()}}
diff=[k for k in set(after['files'])|set(before['files']) if after['files'].get(k)!=before['files'].get(k)]
assert len(after['files'])==429 and not diff
assert after['head']==before['head']=='a396acb7fbfcb7393ae8cbcd4aa42a53b8d8e3a8'
(root/'source-after.json').write_text(json.dumps(after,indent=2,sort_keys=True)+'\n')
ui=[]
for p in sorted((root/'selected-fixtures').glob('test_spec_page*/results.json')):
 if p.parent.is_symlink():continue
 d=json.loads(p.read_text());wire=json.loads((p.parent/'model-wire.json').read_text())
 checks=d['checks'];loaded=d['loaded_source_sha256']
 assert d['status']=='PASS' and len(loaded)==20 and len(wire)==3
 mismatches=[k for k,v in loaded.items() if sha(repo/'src/sim2act/web'/k)!=v]
 assert not mismatches
 ui.append({'fixture':str(p.parent),'status':d['status'],'checks_count':len(checks),'checks':checks,'loaded_unique_assets':len(loaded),'loaded_source_sha256':loaded,'source_hash_mismatches':mismatches,'synthetic_provider_messages':len(wire),'result_sha256':sha(p),'wire_sha256':sha(p.parent/'model-wire.json'),'driver_log_sha256':sha(p.parent/'driver.log'),'raw_extra_fields':{k:v for k,v in d.items() if k not in ['checks','loaded_source_sha256']}})
assert len(ui)==3
(root/'ui-result-summary.json').write_text(json.dumps(ui,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
reuse=json.loads((root/'reused-extra-files.json').read_text());reused_diff=[]
for name,e in reuse['files_and_links'].items():
 p=prior/name
 a={'type':'symlink','target':str(p.readlink())} if p.is_symlink() else {'type':'file','bytes':p.stat().st_size,'sha256':sha(p)}
 if a!=e:reused_diff.append(name)
assert not reused_diff
proc=subprocess.check_output(['ps','-eo','pid,ppid,args'],text=True).splitlines()
active=[x for x in proc if ('pytest' in x or 'node tests/pa_spec_ui.cjs' in x) and ('dynamic-final-a396-r2-20261012' in x or 'selected-fixtures/test_spec_page' in x) and 'finalize_review.py' not in x and 'python - <<' not in x]
assert not active,active
out={'conclusion':'LIMITED PASS','head':after['head'],'source_entries':429,'source_before_sha256':sha(root/'source-before.json'),'source_after_sha256':sha(root/'source-after.json'),'source_differences':diff,'selected':selected,'selected_process':exitmeta,'extra':extra,'extra_process':json.loads((root/'history-a396-enospc-and-extra-bridge.json').read_text())['completed_extra'],'combined_unique':79,'combined_counts':{'PASS':79,'FAIL':0,'ERROR':0,'SKIP':0},'combined_is_single_process':False,'selected_extra_node_overlap':0,'selected_overlaps_author_same_modules':63,'extra_unique_test_identifiers_separate_from_author':16,'ui':ui,'reused_extra_entry_count':reuse['entries'],'reused_extra_differences':reused_diff,'active_own_test_processes':active,'not_run':['real model/provider/network/paid API','PG','Windows','native browser','real business semantic/gold acceptance','full product suite','packaged wheel/install qualification (previous setuptools unavailable)','old cancelled exact installation race (permanent NOT_VERIFIED)','CI','source-deleted/content-free reuse']}
(root/'review-result.json').write_text(json.dumps(out,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
print(json.dumps({'head':out['head'],'selected_counts':selected['counts'],'extra_counts':extra['counts'],'combined_unique':79,'source_entries':429,'source_differences':diff,'ui_checks':[x['checks_count'] for x in ui],'own_active':active,'selected_wall_seconds':exitmeta['wall_seconds']}))

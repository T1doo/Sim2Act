"""Whitelisted tar member read in memory; no filesystem extraction, DB access or product imports."""
from pathlib import Path
import ast, hashlib, json, tarfile, xml.etree.ElementTree as ET
repo=Path('/workspace/Sim2Act');out=Path('/workspace/correction-chain-reuse-review-20261018')
archive=repo/'docs/evidence/natural-spec-correction-20261013/natural-spec-correction-evidence-20261013.tar.gz'
prefix='natural-spec-correction-evidence-20261013/'
metadata=['SUMMARY.json','MANIFEST.json','source-final.json','author/final-matrix-source-before.json',
 'author/formatted-final-matrix-source-before.json','author/formatted-final-matrix-source-after.json',
 'author/formatted-final-matrix-command.json','author/formatted-final-matrix-result.json',
 'author/formatted-final-matrix.xml','independent-final-r2/FINAL_SUMMARY.json','independent-test-format-bridge/BRIDGE.json',
 'independent-ui/final-2e21/controlled-final.xml','independent-ui/final-2e21/controlled-lost-rerun.xml',
 'independent-ui/final-2e21/controlled-final-source-before.json','independent-ui/final-2e21/controlled-final-source-after.json',
 'independent-ui/final-2e21/controlled-lost-rerun-source-before.json','independent-ui/final-2e21/controlled-lost-rerun-source-after.json',
 'independent-ui/final-2e21/controlled-final-tmp/test_actual_correction_control0/proof.json',
 'independent-ui/final-2e21/controlled-final-tmp/test_actual_correction_control2/proof.json',
 'independent-ui/final-2e21/controlled-lost-rerun-tmp/test_actual_correction_control0/proof.json']
paths=['src/sim2act/natural_spec_corrections.py','src/sim2act/natural_spec_runtime.py','src/sim2act/owner_acceptance.py',
 'src/sim2act/pa_spec_apps.py','src/sim2act/app_jobs.py','src/sim2act/worker.py',
 'src/sim2act/web/owner-review.js','tests/natural_spec_corrections_ui.cjs',
 'tests/test_natural_spec_corrections.py','tests/test_natural_spec_corrections_ui.py']
selected=metadata+['source-final/'+p for p in paths]+['independent-ui/final-2e21/test_controlled_final.py','independent-ui/final-2e21/correction-controlled.cjs','author/seeded_cases.py']
raw={}
with tarfile.open(archive,'r:gz') as t:
 for relative in selected:
  assert not any(x in relative.lower() for x in ('private','holdout','.db','.sqlite'))
  member=t.getmember(prefix+relative);assert member.isfile() and not member.issym() and not member.islnk()
  raw[relative]=t.extractfile(member).read()
manifest=json.loads(raw['MANIFEST.json']);entries={e['path']:e for e in manifest['files']};member_evidence={}
for n,b in raw.items():
 if n=='MANIFEST.json':continue
 entry=entries[n];assert len(b)==entry['size'] and hashlib.sha256(b).hexdigest()==entry['sha256'],n
 member_evidence[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'matches_archive_manifest':True}
summary=json.loads(raw['SUMMARY.json']);before=json.loads(raw['author/formatted-final-matrix-source-before.json']);after=json.loads(raw['author/formatted-final-matrix-source-after.json'])
assert before==after and len(before['files'])==456 and before['head']==summary['test_only_head']=='357264c20c42fa5bc3ddf6afc1d8d4f4a2c70fe7'
prior=json.loads(raw['author/final-matrix-source-before.json'])
product=[p for p in before['files'] if p.startswith('src/')]
assert len(product)==99 and all(prior['files'][p]==before['files'][p] for p in product)
source_final=json.loads(raw['source-final.json']);assert source_final==after
comparison=[]
for p in paths:
 old=raw['source-final/'+p];new=(repo/p).read_bytes()
 assert hashlib.sha256(old).hexdigest()==before['files'][p]
 item={'path':p,'archive_source_member':'source-final/'+p,'old_sha256':hashlib.sha256(old).hexdigest(),
       'current_sha256':hashlib.sha256(new).hexdigest(),'bytes_equal':old==new}
 if p.endswith('.py'):
  def funcs(data):
   found={}
   def collect(body,prefix=''):
    for node in body:
     if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
      found[prefix+node.name]=node
     elif isinstance(node,ast.ClassDef):
      collect(node.body,prefix+node.name+'.')
   collect(ast.parse(data).body)
   return found
  a,b=funcs(old),funcs(new)
  item['unchanged_functions']=[k for k in sorted(set(a)&set(b)) if ast.dump(a[k],include_attributes=False)==ast.dump(b[k],include_attributes=False)]
  item['changed_functions']=[k for k in sorted(set(a)&set(b)) if k not in item['unchanged_functions']]
  item['new_functions']=sorted(set(b)-set(a));item['removed_functions']=sorted(set(a)-set(b))
 comparison.append(item)
xmls={}
for name in ('author/formatted-final-matrix.xml','independent-ui/final-2e21/controlled-final.xml','independent-ui/final-2e21/controlled-lost-rerun.xml'):
 cases=[]
 for x in ET.fromstring(raw[name]).iter('testcase'):
  cases.append({'node_id':x.get('classname')+'::'+x.get('name'),'name':x.get('name'),'seconds':x.get('time'),
                'status':'FAIL' if x.find('failure') is not None else 'ERROR' if x.find('error') is not None else 'PASS'})
 xmls[name]={'sha256':hashlib.sha256(raw[name]).hexdigest(),'cases':cases}
assert len(xmls['author/formatted-final-matrix.xml']['cases'])==17 and all(x['status']=='PASS' for x in xmls['author/formatted-final-matrix.xml']['cases'])
controlled_maps={}
for stem in ('controlled-final','controlled-lost-rerun'):
 a=json.loads(raw['independent-ui/final-2e21/'+stem+'-source-before.json']);b=json.loads(raw['independent-ui/final-2e21/'+stem+'-source-after.json'])
 assert a==b and len(a['files'])==456
 controlled_maps[stem]={'head':a['head'],'files':456,'zero_drift':True}
proofs={k:json.loads(v) for k,v in raw.items() if k.endswith('/proof.json')}
old_js=raw['source-final/src/sim2act/web/owner-review.js'].decode();current_js=(repo/'src/sim2act/web/owner-review.js').read_text()
def between(text,start,end):return text[text.index(start):text.index(end,text.index(start))]
js_bridge={}
for start,end in [('async function correctionValidate(', 'function correctionRender('),
                 ('$("correction-prepare").onclick=', '$("correction-submit").onclick='),
                 ('$("correction-submit").onclick=', '$("correction-recover").onclick='),
                 ('$("correction-recover").onclick=', '$("correction-reset").onclick=')]:
 a,b=between(old_js,start,end),between(current_js,start,end)
 js_bridge[start]={'old_sha256':hashlib.sha256(a.encode()).hexdigest(),'current_sha256':hashlib.sha256(b.encode()).hexdigest(),'bytes_equal':a==b}

result={'kind':'SELECTED_ARCHIVE_MEMBERS_AND_CURRENT_SOURCE_READ_ONLY_REVIEW','archive':str(archive),'archive_bytes':archive.stat().st_size,
 'archive_manifest_sha256':hashlib.sha256(raw['MANIFEST.json']).hexdigest(),'member_reads':member_evidence,
 'executed_test_head':before['head'],'product_frozen_head':summary['product_frozen_head'],'product_core':summary['product_core'],
 'input_map_count':456,'before_after_equal':True,'product_metadata_99_equal_across_2e21_to_357':True,
 'JUnit':xmls,'controlled_UI_inputs':controlled_maps,'controlled_UI_proofs':proofs,'current_source_comparison':comparison,'selected_JS_function_handler_bridge':js_bridge,
 'limits':['Only explicitly whitelisted metadata/XML/source members read in memory; no filesystem extraction or DB/holdout member content access',
 'Historical results remain historical; changed current controller/source bytes are not requalified by this archive',
 'No Git/authentication, network, product, pytest, model, DB or SQL execution by reviewer',
 'Current new-button actual HTTP/Worker chain still requires the planned single fresh test; controlled UI probes are not full HTTP/Worker chains']}
(out/'archive-reuse-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'selected_manifest_verified':len(member_evidence),'input_head':before['head'],'old_actual_nodes':17,'current_functions':[{k:x[k] for k in ('path','bytes_equal','changed_functions') if k in x} for x in comparison],'controlled_proofs':proofs},ensure_ascii=False,indent=2))

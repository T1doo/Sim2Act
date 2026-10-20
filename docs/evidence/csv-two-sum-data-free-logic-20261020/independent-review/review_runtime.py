from pathlib import Path
import json,gzip,hashlib,xml.etree.ElementTree as E,csv,io
from fractions import Fraction
b=Path('/workspace/Sim2Act/docs/evidence/csv-two-sum-data-free-logic-20261020');repo=Path('/workspace/Sim2Act');out=Path(__file__).parent
dec=lambda p:gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
jl=lambda p:json.loads(dec(p));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freeze=jl(b/'quality/source-freeze.json');assert all(sha(repo/p)==h and sha(b/'frozen-source'/p)==h for p,h in freeze.items())
q=jl(b/'quality/checks.json');assert len(q)==7 and all(v['exit_code']==0 for v in q)
pd=b/'originals/sim2act-dual-logic-backend-final-20261020/test_authority_retired_source_0';p=jl(pd/'proof.json.gz');read=p['target']['steps'][0]['data'];rows=list(csv.DictReader(io.StringIO(read['content'])));h=hashlib.sha256(read['content'].encode()).hexdigest();assert h==read['hash'];expected={c:sum((Fraction(r[c]) for r in rows),Fraction()) for c in ('net','units')}
def verify(v,rid):
 assert v['resource_id']==rid and v['source_hash']==h and v['count']==len(rows) and Fraction(v['sum'])==expected[v['column']]
for v in p['target']['result']['output_by_step'].values():verify(v,read['resource_id'])
for v in p['cold_instance']['data'][0]['data']['result'].values():verify(v,read['resource_id'])
assert p['original_history_preserved'] is True and p['source_resource_selects']==p['source_run_body_or_operations_selects']==p['model_requests']==0
ids=jl(b/'inspection/source-identities.json');audit=ids['private_source_audit'];oldrid=ids['old_resource_id'];oldrun=audit['run_id'];sql=[json.loads(line) for line in dec(pd/'source-selects.jsonl.gz').decode().splitlines()];br=[];bb=[];ident=0;aud=0
for n,row in enumerate(sql):
 s=row['statement'].lower();params=str(row['parameters'])
 if 'resources' in s and oldrid in params:br.append(n)
 if oldrun in params:
  ident+=1
  if any(v in s for v in ('runs.result','runs.context','operations.')):bb.append(n)
 if audit['release_id'] in params or audit['approval_id'] in params:aud+=1
assert not br and not bb
uis=[];assets=0
for d in sorted((b/'originals/sim2act-dual-logic-ui-final-20261020').iterdir()):
 r=jl(d/'results.json.gz');i=jl(d/'info.json.gz');assert r['status']=='PASS' and r['pages']==2 and json.loads((d/'driver.log').read_text())['status']=='PASS'
 for a in r['assets']:
  for n,digest in a['loaded_source_sha256'].items():assert sha(repo/'src/sim2act/web'/n)==digest;assets+=1
 posts=[v for v in r['requests'] if v['method']=='POST' and v['path'].endswith('/material-plans')];assert len(posts)==(1 if i['lost'] in ['mint-post','identity-late'] else 2);assert all(v['body']==posts[0]['body'] for v in posts)
 public=json.dumps(r['logic']);assert all(v not in public for v in [i['resource'],i['release'],'"amount"','"quantity"','private_audit'])
 if i['dual']:assert [n['step_id'] for n in r['logic']['recipe']['nodes']]==['read','total_a','total_b']
 vals=r['instance']['data'][0]['data']['result'];vals=list(vals.values()) if i['dual'] else [vals]
 for v in vals:verify(v,r['plan']['binding']['target']['resource_id'])
 uis.append({'case':d.name,'dual':i['dual'],'mode':i['lost'],'status':r['status'],'checks':len(r['checks']),'material_posts':len(posts),'result_uncompressed_sha256':hashlib.sha256(dec(d/'results.json.gz')).hexdigest()})
assert len(uis)==9 and assets==468
suites=[]
for n in ['sim2act-dual-logic-backend-final-20261020.xml','sim2act-dual-logic-ui-final-20261020.xml','sim2act-dual-logic-regressions-20261020.xml','sim2act-dual-logic-ui-regressions-20261020.xml','sim2act-dual-logic-ui-seal-red-20261020.xml.gz','sim2act-dual-logic-backend-v1-20261020.xml.gz']:
 path=b/'originals'/n;s=next(E.fromstring(dec(path)).iter('testsuite'));suites.append({'file':str(path),'sha256':sha(path),'suite':s.attrib,'failures':[t.attrib['name'] for t in s.findall('testcase') if t.find('failure') is not None],'skips':[t.attrib['name'] for t in s.findall('testcase') if t.find('skipped') is not None]})
summary={'decision':'FROZEN_LOCAL_SYNTHETIC_RUNTIME_ACK','open_p1':0,'open_p2':0,'reviewer_executions':dict.fromkeys(['tests','Worker','database_opens','models','PB','G0','product_imports'],0),'source_freeze':{'sha256':sha(b/'quality/source-freeze.json'),'matched_current_and_frozen_files':len(freeze),'files':freeze},'quality_exit0':len(q),'suites':suites,'ui':uis,'loaded_asset_sha_matches':assets,'independent_arithmetic':{'input_sha256':h,'rows':len(rows),'net':str(expected['net']),'units':str(expected['units']),'target':'total_a net=8.75, total_b units=13','cold':'total_a units=13, total_b net=8.75'},'sql':{'archived_selects':len(sql),'old_resource_exact_parameter_selects':len(br),'old_run_body_or_operations_exact_parameter_selects':len(bb),'old_run_identity_exact_parameter_selects':ident,'old_release_or_approval_parameter_selects':aud,'scope':'Exact-ID parameter predicates match runtime observer. Broad table snapshot SELECTs from fixture oracle also appear without scope tags. This is not a claim of zero old body values in all recorded SQL or zero old JSON access; immutable Release/approval audit is intentionally allowed.'},'post_test_identity_projection':{'sha256':sha(b/'inspection/source-identities.json'),'status':'parent identifier-only post-test read-only auxiliary inspection, not runtime observer; reviewer did not open DB'},'proof_uncompressed_sha256':hashlib.sha256(dec(pd/'proof.json.gz')).hexdigest(),'limits':['Local synthetic SQLite/ASGI/JSDOM final selected cases only.','Earlier backend67P2skip and UI14P ran before P2 fixes; not final-frozen blanket regression qualification. Three selected scalar paths were rerun in final UI9.','Red2F5.497s and initial backend26P1F fixture error remain failures, not passes.','No PG/native Windows/CI/full PB/G0/real model/publication/old authority migration qualification.','SQL wide fixture snapshots are visible and not runtime scope-tagged; exact-ID observer predicates and static product projections support only the stated limited boundary.']}
(out/'RUNTIME-ACK.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:summary[k] for k in ['decision','loaded_asset_sha_matches','independent_arithmetic','sql','ui']},ensure_ascii=False,indent=2))

import pathlib,json,hashlib,subprocess,re,collections
R=pathlib.Path('/tmp/sim2act-native-final-publication-audit-20261010');REPO=pathlib.Path('/workspace/Sim2Act');OBS=REPO/'docs/evidence/native-interruption-diagnostics-20261010';PRE=REPO/'docs/evidence/native-engineering-prerequisites-20261010';D=pathlib.Path('/tmp/sim2act-native-diagnostics-20261010');P=pathlib.Path('/tmp/sim2act-native-prerequisites-20261010');SHA='9002bf958f79972e576e831ebdf5e0d90fc44ea5'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def manifest(root,count):
 m=json.loads((root/'PUBLISHED_MANIFEST.json').read_text());actual={str(p.relative_to(root)):h(p) for p in root.rglob('*') if p.is_file() and p!=root/'PUBLISHED_MANIFEST.json'};assert len(actual)==m['count']==len(m['files'])==count and actual==m['files'];return {'count':count,'all_hashes_match':True,'excludes_only_own_root_manifest':True,'manifest_sha256':h(root/'PUBLISHED_MANIFEST.json')}
manifests={'observer':manifest(OBS,219),'prerequisites':manifest(PRE,248)}
sealed={}
for public,private,count in [(OBS/'author',D,143),(OBS/'independent-d8-blocked',pathlib.Path('/tmp/sim2act-native-diagnostics-independent-20261010'),39),(OBS/'independent-88cb',pathlib.Path('/tmp/sim2act-native-diagnostics-independent-88cb-20261010'),19),(PRE/'author',P,189),(PRE/'independent',pathlib.Path('/tmp/sim2act-native-prerequisites-independent-20261010'),45)]:
 w=json.loads((public/'COPY_WHITELIST.json').read_text());assert (public/'COPY_WHITELIST.json').read_bytes()==(private/'COPY_WHITELIST.json').read_bytes();entries=w['files'] if isinstance(w['files'],dict) else {r['path']:r['sha256'] for r in w['files']};excluded={'ci-6eb-full.log'} if public==OBS/'author' else set();assert len(entries)-len(excluded)==count
 for name,v in entries.items():
  assert h(private/name)==v
  if name not in excluded:assert h(public/name)==v
  else:assert not (public/name).exists()
 actual={str(p.relative_to(public)) for p in public.rglob('*') if p.is_file()};assert actual==(set(entries)-excluded)|{'COPY_WHITELIST.json'};sealed[str(public.relative_to(REPO))]={'copied_entries':count,'exact':True,'no_unlisted_files':True,'excluded':sorted(excluded)}
prov=json.loads((OBS/'log-byte-provenance.json').read_text());byte_proofs={}
for name in ['ci-88','ci-6eb']:
 normalized=D/(name+'-full.log');raw=D/(name+'-full.raw.log');b=raw.read_bytes();n=normalized.read_bytes();row=prov[name];assert h(normalized)==row['normalized_private_sha256'] and h(raw)==row['transport_private_sha256'] and len(b)==row['transport_bytes'] and len(b.decode('utf-8'))==row['transport_chars'];assert b'\r\n' in b and b'\r\n' not in n;assert b.replace(b'\r\n',b'\n')==n
 byte_proofs[name]={'normalized_sha256':h(normalized),'transport_sha256':h(raw),'normalized_bytes':len(n),'transport_bytes':len(b),'exact_CRLF_to_LF_equivalence':True}
oldci=json.loads((OBS/'author/ci-6eb-result.json').read_text());assert oldci['log_sha256']==byte_proofs['ci-6eb']['normalized_sha256'];v88=json.loads((OBS/'native-88/verification.json').read_text());assert v88['normalized_private_log_sha256']==byte_proofs['ci-88']['normalized_sha256'] and v88['full_transport_private_sha256']==byte_proofs['ci-88']['transport_sha256']
initial=OBS/'initial-207/PUBLISHED_MANIFEST.json';oldreceipt=json.loads((OBS/'publication-review/PUBLICATION_RECEIPT.json').read_text());assert h(initial)==oldreceipt['published_manifest_sha256'];assert json.loads(initial.read_text())['count']==207
# Independent reader of original connector transport. Do not invoke the author's parser.
def read_native(path):
 starts=[];records=[];summary=None;active=None
 for line in path.read_bytes().decode('utf-8').splitlines():
  t=re.sub(r'^\d{4}-\d{2}-\d{2}T\S+ ', '',line)
  marker='SIM2ACT_CI_DIAGNOSTIC '
  if marker in t:
   d=json.loads(t.split(marker,1)[1]);records.append(d)
   if d['event']=='node_start':
    starts.append({'nodeid':d['nodeid'],'utc':d['utc'],'symbols':[]});active=starts[-1]
   elif d['event'] in ['interrupted','session_finish']:active=None
  elif t.startswith('Engineering diagnostics: '):summary=json.loads(t[len('Engineering diagnostics: '):])
  elif active is not None:
   m=re.fullmatch(r'([.sFE]+)(?:\s+\[\s*\d+%\])?',t.strip())
   if m:active['symbols'].extend(m.group(1))
 assert summary is not None
 failures=[d for d in records if d['event']=='collection_failed' or d['event']=='node_report' and d['outcome']=='failed'];counts=collections.Counter(''.join(''.join(s['symbols']) for s in starts));return {'summary':summary,'starts':starts,'records':records,'failures':failures,'counts':dict(counts)}
x=read_native(P/'ci-9002-full.log');native=json.loads((PRE/'native-9002/result.json').read_text());assert h(P/'ci-9002-full.log')==native['full_log_private_sha256']=='0bd574e394dacaa693b3311fe878e38f653195b5be7af909b136faa8cce249ed';assert x['summary']==native['summary'];assert len(x['records'])==native['visible_records']==596 and len(x['starts'])==native['segments_count']==592 and not x['failures'];assert x['counts']=={'.':589,'s':2};assert sum(not s['symbols'] for s in x['starts'])==1
assert native['summary']['collected']==2234 and native['summary']['started']==592 and native['summary']['finished']==591 and native['summary']['not_started_count']==1642 and native['summary']['suite_complete'] is False and native['summary']['exitstatuses']==[2]
byid={s['nodeid']:s for s in x['starts']};actualtargets=[]
for t in native['target_results']:
 s=byid.get(t['nodeid']);status='NOT_RUN' if s is None else ('PASS: actual pytest progress dot' if s['symbols']==['.'] else 'INCOMPLETE_OR_NOT_RECORDED');assert status==t['status'] and (s['symbols'] if s else None)==t['progress'];actualtargets.append({'nodeid':t['nodeid'],'status':status,'utc':s['utc'] if s else None,'progress':s['symbols'] if s else None})
assert len(actualtargets)==26 and sum(t['status'].startswith('PASS') for t in actualtargets)==15 and sum(t['status']=='NOT_RUN' for t in actualtargets)==10 and sum(t['status']=='INCOMPLETE_OR_NOT_RECORDED' for t in actualtargets)==1
assert byid[native['summary']['active_nodes'][0]]['utc'].startswith('2026-10-10T05:59:48.721')
(R/'independent-targets.json').write_text(json.dumps(actualtargets,indent=2))
y=read_native(D/'ci-88-full.raw.log');orig=json.loads((OBS/'native-88/result.json').read_text());assert y['summary']==orig['diagnostics'];assert len(y['starts'])==856 and len(y['failures'])==26;assert sum("Cannot find module 'jsdom'" in f['failure'] for f in y['failures'])==25;assert len(y['summary']['junit'])==1 and y['summary']['junit'][0]['tests']=='855' and y['summary']['junit'][0]['failures']=='26' and y['summary']['junit'][0]['skipped']=='38';assert y['summary']['suite_complete'] is False
f=json.loads((PRE/'author/source-freeze.json').read_text());assert f['source_sha']==SHA and len(f['files'])==362 and subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==SHA
for p,v in f['files'].items():assert h(REPO/p)==v and hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest()==v
src={p:v for p,v in f['files'].items() if p.startswith('src/')};assert len(src)==69
for p,v in src.items():assert hashlib.sha256(subprocess.check_output(['git','show','47388f573746daa27f8d5790ca358eef91378ad5:'+p],cwd=REPO)).hexdigest()==v
for name in ['NativeEngineeringPrerequisites20261010.md','NativeInterruptionDiagnostics20261010.md']:
 text=(REPO/'docs/F2'/name).read_text();assert 'OPEN' in text and 'NOT_ACCEPTED' in text and ('NOT_RECORDED' in text or '未完成' in text)
doc=(REPO/'docs/F2/NativeEngineeringPrerequisites20261010.md').read_text();assert '15 actual native PASS' in doc and '10 are NOT_RUN' in doc and 'suite_complete=false' in doc and '589PASS/0FAIL/2SKIP/0ERROR' in doc and 'NOT_ACCEPTED' in doc and 'LIMITED_PASS' in doc
attributes=(PRE/'.gitattributes').read_text().splitlines();assert len(attributes)==4 and set(attributes)=={'author/new-crlf/fixtures/column-binding.csv -text','author/old-crlf/fixtures/column-binding.csv -text','independent/crlf/material.csv -text','independent/harness-first-run/crlf/material.csv -text'}
assert (REPO/'.gitattributes').read_bytes()==subprocess.check_output(['git','show',SHA+':.gitattributes'],cwd=REPO)
staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=REPO).decode().split('\0');staged=[p for p in staged if p];assert staged and all(p.startswith('docs/') for p in staged)
for path in staged:assert hashlib.sha256(subprocess.check_output(['git','show',':'+path],cwd=REPO)).hexdigest()==h(REPO/path)
for line in attributes:
 path=line.split(' ')[0];b=(PRE/path).read_bytes();assert b'\r\n' in b
assert manifests=={'observer':manifest(OBS,219),'prerequisites':manifest(PRE,248)}
result={'staged_index':{'paths':len(staged),'all_docs_only':True,'all_blob_worktree_hashes_match':True,'scoped_four_CSV_minus_text':True,'root_gitattributes_unchanged':True},'verdict':'FINAL_PUBLICATION_EXACT_MATCH','source_sha':SHA,'manifests':manifests,'sealed_exports':sealed,'byte_provenance':byte_proofs,'initial_207_manifest_exact_original':True,'native9002':{'transport_sha256':h(P/'ci-9002-full.log'),'counts':x['counts'],'collected':2234,'started':592,'finished':591,'active':1,'unstarted':1642,'failure_reports':0,'visible_records':596,'target_pass':15,'target_interrupted':1,'target_not_run':10,'suite_complete':False},'native88':{'started':856,'finished':855,'failure_reports':26,'missing_jsdom':25,'CSV_hash':1,'suite_complete':False},'freeze362_and_products69_same473':True,'doc_scope_consistent':True,'actual_tests_or_CI_or_PG_operations':0,'repo_or_ref_writes':0,'no_acceptance_inferred':True}
(R/'FINAL_PUBLICATION_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

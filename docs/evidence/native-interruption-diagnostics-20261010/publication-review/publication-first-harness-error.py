import pathlib,json,hashlib,subprocess,xml.etree.ElementTree as ET
PUB=pathlib.Path('/workspace/Sim2Act/docs/evidence/native-interruption-diagnostics-20261010');PRIV=pathlib.Path('/tmp/sim2act-native-diagnostics-20261010');OUT=pathlib.Path('/tmp/sim2act-native-diagnostics-independent-88cb-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='88cb3c64b5dcbaf3df7183ebbf72773547585e15'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((PUB/'PUBLISHED_MANIFEST.json').read_text());actual={str(p.relative_to(PUB)):sha(p) for p in PUB.rglob('*') if p.is_file() and p.name!='PUBLISHED_MANIFEST.json'};assert m['count']==len(m['files'])==len(actual)==207 and m['files']==actual
checks={'published_manifest_207_exact':True};copies={}
for name,private,count in [('independent-d8-blocked',pathlib.Path('/tmp/sim2act-native-diagnostics-independent-20261010'),39),('independent-88cb',OUT,19)]:
 w=json.loads((PUB/name/'COPY_WHITELIST.json').read_text());original=json.loads((private/'COPY_WHITELIST.json').read_text());assert w==original and len(w['files'])==w['count']==count
 for f in w['files']:assert sha(PUB/name/f['path'])==sha(private/f['path'])==f['sha256']
 copied={str(p.relative_to(PUB/name)) for p in (PUB/name).rglob('*') if p.is_file()};assert copied=={f['path'] for f in w['files']}|{'COPY_WHITELIST.json'};copies[name]={'whitelisted_files':count,'with_whitelist_file':len(copied),'all_exact':True}
a=json.loads((PUB/'author/COPY_WHITELIST.json').read_text());assert a==json.loads((PRIV/'COPY_WHITELIST.json').read_text());excluded='ci-6eb-full.log';assert excluded in a['files'] and not (PUB/'author'/excluded).exists()
for name,h in a['files'].items():
 assert sha(PRIV/name)==h
 if name!=excluded:assert sha(PUB/'author'/name)==h
actual_author={str(p.relative_to(PUB/'author')) for p in (PUB/'author').rglob('*') if p.is_file()};assert actual_author==(set(a['files'])-{excluded})|{'COPY_WHITELIST.json'};assert len(a['files'])==144 and len(actual_author)==144
ci=json.loads((PUB/'author/ci-6eb-result.json').read_text());assert ci['log_sha256']==a['files'][excluded] and ci['artifacts']==[] and ci['failed_nodes']=='NOT_RECORDED' and ci['conclusion']=='cancelled';copies['author']={'whitelisted_files':144,'copied_whitelisted_files':143,'with_whitelist_file':144,'excluded':excluded,'excluded_private_hash_match':True,'all_exact':True}
f=json.loads((PUB/'author/source-freeze.json').read_text());assert f['source_sha']==SHA and len(f['files'])==f['source_count']==360 and len(f['products'])==f['product_count']==69 and f['product_bytes_equal_to_473']
for p,h in f['files'].items():assert sha(REPO/p)==h and hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest()==h
for p,h in f['products'].items():assert h==f['files'][p] and hashlib.sha256(subprocess.check_output(['git','show','47388f573746daa27f8d5790ca358eef91378ad5:'+p],cwd=REPO)).hexdigest()==h
checks['source_360_git_worktree_exact']=True;checks['product_69_same473']=True
old=json.loads((PUB/'independent-d8-blocked/FINAL_REVIEW.json').read_text());new=json.loads((PUB/'independent-88cb/FINAL_REVIEW.json').read_text());assert old['verdict']=='BLOCK' and old['checks_in_passed_scenarios']==15 and new['verdict']=='LIMITED_PASS' and new['total_checks']==27
raw=json.loads((PUB/'independent-d8-blocked/results.json').read_text());assert raw[0]['status']=='FAIL';assert sum(len(r['checks']) for r in raw if r['status']=='PASS')==15
xmls={}
for name in ['probe.xml','corrected.xml','redaction-fixed.xml','redaction-final.xml','outer88.xml']:
 path=PUB/'author'/name
 if path.exists():
  suites=list(ET.parse(path).getroot().iter('testsuite'));xmls[name]=[{k:s.attrib.get(k) for k in ['tests','failures','errors','skipped']} for s in suites]
assert sum(int(r.get('failures') or 0) for r in xmls['corrected.xml'])==2;assert sum(int(r.get('failures') or 0) for r in xmls['redaction-fixed.xml'])==2;assert sum(int(r.get('failures') or 0) for r in xmls['redaction-final.xml'])==0
checks['old_FAIL_and_BLOCK_preserved_exact']=True
readme=(PUB/'README.md').read_text();ledger=(PUB/'FailureLedger.md').read_text();doc=(REPO/'docs/F2/NativeInterruptionDiagnostics20261010.md').read_text();assert 'LIMITED_PASS' in doc and 'BLOCK' in doc and 'OPEN' in doc and 'NOT_ACCEPTED' in doc and '待最终证据' in doc;assert 'IN_PROGRESS' in ledger and 'prior15 checks not rerun/reassigned' in ledger;checks['scope_and_pending_native_status_consistent']=True
receipt={'verdict':'PUBLICATION_EXACT_MATCH','source_sha':SHA,'published_manifest':{'count':207,'all_hashes_match':True,'manifest_excludes_itself':True},'copies':copies,'checks':checks,'preserved_author_xml_results':xmls,'public_F2_doc_sha256':sha(REPO/'docs/F2/NativeInterruptionDiagnostics20261010.md'),'published_manifest_sha256':sha(PUB/'PUBLISHED_MANIFEST.json'),'no_tests_or_CI_run':True,'no_repository_or_ref_write':True,'scope':'publication integrity only; existing LIMITED_PASS/BLOCK boundaries retained'}
(OUT/'PUBLICATION_RECEIPT.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))

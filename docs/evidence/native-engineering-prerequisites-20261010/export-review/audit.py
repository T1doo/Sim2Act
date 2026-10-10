import pathlib,json,hashlib,subprocess
ROOT=pathlib.Path('/tmp/sim2act-native-prerequisites-publication-audit-20261010');PUB=pathlib.Path('/workspace/Sim2Act/docs/evidence/native-engineering-prerequisites-20261010');REPO=pathlib.Path('/workspace/Sim2Act');SHA='9002bf958f79972e576e831ebdf5e0d90fc44ea5'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks={};exports={}
for name,private,expected in [('author',pathlib.Path('/tmp/sim2act-native-prerequisites-20261010'),189),('independent',pathlib.Path('/tmp/sim2act-native-prerequisites-independent-20261010'),45)]:
 pubwhite=PUB/name/'COPY_WHITELIST.json';privwhite=private/'COPY_WHITELIST.json';assert pubwhite.read_bytes()==privwhite.read_bytes();w=json.loads(pubwhite.read_text());entries=w['files'] if isinstance(w['files'],dict) else {x['path']:x['sha256'] for x in w['files']};assert w['count']==expected==len(entries)
 for p,hash_value in entries.items():assert h(PUB/name/p)==h(private/p)==hash_value
 actual={str(p.relative_to(PUB/name)) for p in (PUB/name).rglob('*') if p.is_file()};assert actual==set(entries)|{'COPY_WHITELIST.json'}
 exports[name]={'whitelisted_count':expected,'actual_files_including_whitelist':len(actual),'all_public_private_whitelist_bytes_equal':True,'unlisted_files':[],'whitelist_sha256':h(pubwhite)}
f=json.loads((PUB/'author/source-freeze.json').read_text());assert f==json.loads(pathlib.Path('/tmp/sim2act-native-prerequisites-20261010/source-freeze.json').read_text());assert f['source_sha']==SHA and len(f['files'])==362;assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==SHA
for p,hash_value in f['files'].items():assert h(REPO/p)==hash_value and hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+p],cwd=REPO)).hexdigest()==hash_value
src={p:v for p,v in f['files'].items() if p.startswith('src/')};assert len(src)==69
for p,hash_value in src.items():assert hashlib.sha256(subprocess.check_output(['git','show','47388f573746daa27f8d5790ca358eef91378ad5:'+p],cwd=REPO)).hexdigest()==hash_value
checks['current_362_Git_worktree_manifest_equal']=True;checks['69_product_files_all_same473']=True
review=json.loads((PUB/'independent/FINAL_REVIEW.json').read_text());assert review['verdict']=='LIMITED_PASS' and review['independent_harness_checks']==42 and review['existing_UI_nodes']==6 and review['existing_driver_checks']==234;checks['independent_LIMITED_PASS_scope_preserved']=True
assert (PUB/'independent/crlf/old/failure.log').is_file() and (PUB/'independent/missing-node-negative.log').is_file() and (PUB/'independent/harness-first-run/probe.log').is_file();checks['independent_negative_and_harness_failures_retained_exact']=True
ledger=(PUB/'FailureLedger.md').read_text();readme=(PUB/'README.md').read_text();assert 'IN_PROGRESS' in ledger and 'inference' in readme and 'NOT_RECORDED' in readme and 'OPEN' in ledger and 'not all25' in ledger;checks['pending_native_and_historical_boundaries_preserved']=True
result={'verdict':'EXPORT_EXACT_MATCH','source_sha':SHA,'exports':exports,'checks':checks,'scope':'author/independent exports and freeze only; final native/docs audit deferred','native_9002_run':'38028553382 IN_PROGRESS as provided; not operated or independently polled','executed_tests':0,'CI_or_PG_operations':0,'repository_writes':0,'public_docs_hashes':{n:h(PUB/n) for n in ['README.md','FailureLedger.md']}}
(ROOT/'EXPORT_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

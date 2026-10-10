from pathlib import Path
import json,hashlib,subprocess,xml.etree.ElementTree as ET
R=Path('/tmp/sim2act-report-dag-publication-independent-20261010');REPO=Path('/workspace/Sim2Act');P=REPO/'docs/evidence/csv-report-dag-reuse-20261010';SHA='50b10417a99a070f6bcd614471cc00ec102b7836'
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
counts={};rows=[]
for w in sorted(P.rglob('COPY_WHITELIST.json')):
 if w.parent.name=='native-final':continue
 d=read(w);src=Path(d['artifact_root']);assert d['count']==len(d['files']);counts[w.parent.name]=d['count'];expected={x['path'] for x in d['files']}|{'COPY_WHITELIST.json'};actual={str(x.relative_to(w.parent)) for x in w.parent.rglob('*') if x.is_file()};assert actual==expected
 if w.parent.name in ['design-independent','independent','type-block-5588','type-fix-independent']:assert w.read_bytes()==(src/'COPY_WHITELIST.json').read_bytes()
 for x in d['files']:
  f=w.parent/x['path'];s=src/x.get('private_source_path',x['path']);assert f.read_bytes()==s.read_bytes(),str(f);assert len(f.read_bytes())==x['bytes'] and digest(f)==x['sha256'];rows.append({'path':str(f.relative_to(P)),'bytes':x['bytes'],'sha256':x['sha256']})
 assert d.get('source_sha',SHA)==('5588a94faeb90abb2052a8ae5327810b8d27c287' if w.parent.name in ['author','independent','type-block-5588','native-5588'] else SHA)
assert counts=={'author':128,'design-independent':3,'independent':61,'native-5588':14,'type-block-5588':12,'type-fix-author':49,'type-fix-independent':22} and sum(counts.values())==289
(R/'audited-subtree-snapshot.json').write_text(json.dumps({'counts':counts,'files':rows},indent=2))
f=read(P/'type-fix-author/source-freeze.json');assert f['source_sha']==SHA and len(f['files'])==365
for path,h in f['files'].items():assert digest(REPO/path)==h and hashlib.sha256(subprocess.check_output(['git','show',SHA+':'+path],cwd=REPO)).hexdigest()==h
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==SHA
add=read(P/'type-fix-author/source-manifest-addendum.json');assert add['original_manifest_sha256']==digest(P/'type-fix-author/source-freeze.json')
for base,key in [(add['base_5588'],'actual_changed_from_5588'),(add['feature_base_f13'],'actual_changed_from_f13')]:assert subprocess.check_output(['git','diff','--name-only',base+'..'+SHA],cwd=REPO,text=True).splitlines()==add[key]
src={p:h for p,h in f['files'].items() if p.startswith('src/')};changed=[p for p,h in src.items() if hashlib.sha256(subprocess.check_output(['git','show',add['product_473_baseline']+':'+p],cwd=REPO)).hexdigest()!=h];assert len(src)==69 and changed==add['actual_product_changed_from_473'] and len(changed)==3
assert f['base']==add['base_5588'] and f['changed']==add['actual_changed_from_f13'] and f['product_changed']==changed and f['delta_from_5588']==add['actual_changed_from_5588']
assert read(P/'type-block-5588/FINAL_REVIEW.json')['verdict']=='BLOCK';assert read(P/'independent/FINAL_REVIEW.json')['source_sha']=='5588a94faeb90abb2052a8ae5327810b8d27c287';ind=read(P/'type-fix-independent/FINAL_REVIEW.json');assert ind['verdict']=='LIMITED_PASS' and ind['scenario_count']==6 and ind['checks']==38 and ind['source_sha']==SHA
result=read(P/'type-fix-author/test-result.json');assert result['source_sha']==SHA
for db,sec in [('sqlite',108.655),('pg',190.927)]:
 suites=list(ET.parse(P/f'type-fix-author/{db}.xml').getroot().iter('testsuite'));assert len(suites)==1;s=suites[0];assert s.attrib['tests']=='12' and all(s.attrib[k]=='0' for k in ['errors','failures','skipped']) and float(s.attrib['time'])==sec;assert result[db]['passed']==12 and result[db]['pytest_seconds']==sec and len(result[db]['nodeids'])==12
cleanup=read(P/'type-fix-author/pg-cleanup.json');assert cleanup['counts']=='0|0|0' and cleanup['network']=='none' and cleanup['published_ports']==0 and cleanup['container_absent'] and all(cleanup['owned_anonymous_volumes_removed'].values())
oldnative=read(P/'native-5588/native-5588-result.json');oldsummary=read(P/'native-5588/native-5588-summary.json');assert oldnative['source_sha']=='5588a94faeb90abb2052a8ae5327810b8d27c287' and oldnative['full_engineering_acceptance']=='NOT_ACCEPTED' and oldnative['passed']==11 and oldnative['full_collection']==2266 and oldnative['deselected']==2255 and oldnative['node_reports']==33 and oldnative['new_report_feature_nodes_not_in_fixed11']
# Contents completed now; native-final and eventual rootmanifest explicitly outside this receipt.
for name in ['README.md']:(R/name).write_bytes((P/name).read_bytes())
for name in ['CsvReportDagInternalReuse20261010.md','CsvDagInternalReuse.md']:(R/name).write_bytes((REPO/'docs/F2'/name).read_bytes())
doc=(P/'README.md').read_text();assert '不能把不同 source 的结果合并为一次通过' in doc and '不能作为其 base5588 字段的差异清单' in doc and '6个公开 GET 全返回200' in doc and 'Operation未改、全库零写' in doc
assert '最终完整原生最小耗时及未测尾部为 UNKNOWN' in doc and '大于900秒' in doc and 'OPEN' in doc and '尚未启动分片' in doc and 'LIVE=0' in doc
out={'verdict':'LIMITED_PASS_COMPLETED_CONTENT_ONLY','source_sha':SHA,'completed_subdirectories':counts,'private_exact_files':289,'plus7whites_and_README':297,'source365_Git_worktree_match':True,'product69_ofwhich66_same473':True,'metadata_original_inherited_baseline_inconsistency_explicitly_corrected_by_addendum':True,'base5588_actual_delta2':add['actual_changed_from_5588'],'old5588BLOCK_kept_and_not_merged_into_new_pass':True,'author_sqlite12_seconds':108.655,'author_pg12_seconds':190.927,'PG_cleanup0and_owned_absent_readonly_verified':True,'independent_delta6_checks38':True,'old_native5588_11_scope_only':True,'native_final_status':'PENDING_excluded_until_actualterminal_review','rootmanifest':'notyetsealed_excluded','full900sufficient_minimum':'UNKNOWN_historicaloldserial_lowerbound_gt900_only','historical_timeouts':'OPEN','tests_PG_CI_repo_ref_operations':0};(R/'AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

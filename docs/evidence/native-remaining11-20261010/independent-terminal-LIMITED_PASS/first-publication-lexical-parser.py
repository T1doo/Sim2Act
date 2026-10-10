import json,hashlib,pathlib,subprocess
R=pathlib.Path('/tmp/sim2act-native-remaining11-terminal-independent-20261010');REPO=pathlib.Path('/workspace/Sim2Act');P=REPO/'docs/evidence/native-remaining11-20261010'
def read(p):return json.loads(p.read_text())
def hashbytes(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=read(P/'PUBLISHED_MANIFEST.json');(R/'audited-267-PUBLISHED_MANIFEST.json').write_bytes((P/'PUBLISHED_MANIFEST.json').read_bytes())
assert m['count']==len(m['files'])==267
actual={str(p.relative_to(P)) for p in P.rglob('*') if p.is_file()}-{'PUBLISHED_MANIFEST.json'}
assert actual=={v['path'] for v in m['files']}
for v in m['files']:
 p=P/v['path'];assert len(p.read_bytes())==v['bytes'] and hashbytes(p)==v['sha256'],v['path']
copy_checks=[]
for f in sorted(P.rglob('COPY_WHITELIST.json')):
 d=read(f);src=pathlib.Path(d['artifact_root']);assert d['count']==len(d['files'])
 if f.parent.name.startswith('independent'):
  assert f.read_bytes()==(src/'COPY_WHITELIST.json').read_bytes()
 if f.parent.name=='historical-pg':assert f.read_bytes()==(src/'PUBLIC_COPY_WHITELIST.json').read_bytes()
 expected={v['path'] for v in d['files']}|{'COPY_WHITELIST.json'}
 assert expected=={str(p.relative_to(f.parent)) for p in f.parent.rglob('*') if p.is_file()}
 for v in d['files']:
  pub=f.parent/v['path'];private=src/v.get('private_source_path',v['path'])
  assert pub.read_bytes()==private.read_bytes(),str(pub)
  assert len(pub.read_bytes())==v['bytes'] and hashbytes(pub)==v['sha256']
 copy_checks.append({'public_dir':str(f.parent.relative_to(P)),'count':d['count'],'private_exact':True})
assert {c['public_dir']:c['count'] for c in copy_checks}=={'author':21,'historical-pg':14,'independent-180a-LIMITED_PASS':83,'independent-5385-BLOCK':64,'independent-d49-BLOCK':55,'native':23}
assert not any('transport' in x or 'full.log' in x for x in actual)
page=read(P/'historical-pg/actual-page-results.json');assert page['status']=='PASS' and len(page['checks'])==10 and len(page['requests'])==28
locks=read(P/'historical-pg/actual-lock-receipt.json');assert len(locks['sql'])==402 and locks['statuses']=={'resources':200,'graph':200} and not locks['sql_errors'] and locks['project_first_observed'] and not locks['old_cycle_observed']
for name in ['resources','graph']:
 events=[e for e in locks['sql'] if e['request']==name];assert events[0]['kind']=='project'
span=max(e['time'] for e in locks['sql'])-min(e['time'] for e in locks['sql']);assert abs(span-1.6475573989955592)<1e-9
b=read(P/'native/browser-emitted/browser-results.json');scopes=read(P/'native/ci-final-browser-check-scopes.json')
for row in scopes:
 obj=b
 for key in row['path'].split('.')[1:]:obj=obj[key]
 assert len(obj['checks'])==row['checks'] and obj['status']==row['status']=='PASS'
 assert all(c.get('status')=='PASS' for c in obj['checks'])
 assert obj.get('visualReview')==row['visualReview']
vis=read(P/'native/ci-author-limited-visual-review.json');assert len(vis['files'])==6 and vis['reviewer']=='author root' and vis['full_acceptance']=='NOT_ACCEPTED'
for path,digest in vis['files'].items():assert hashbytes(P/'native/browser-emitted'/path)==digest
assert b['win11']=='NOT_RUN' and b['agent']['visualReview']==b['protocol']['visualReview']=='NOT_REVIEWED'
base=read(P/'native/capacity-baseline.json');old=pathlib.Path('/tmp/sim2act-native-prerequisites-20261010/ci-9002-full.log');assert hashbytes(old)==base['decoded_job_log_utf8_bytes_sha256'] and len(old.read_bytes())==base['decoded_job_log_utf8_bytes']
assert (base['collected'],base['finished'],base['passed'],base['skipped'],base['failed'],base['active'],base['not_started'])==(2234,591,589,2,0,1,1642)
assert base['lower_bound_strict'] and base['measured_required_budget_lower_bound_seconds']==900 and base['sufficient_minimum_budget_seconds']=='UNKNOWN' and base['remaining_tail_cost']=='UNKNOWN'
# Exact reviewed wording snapshots, with historical plan clearly marked.
for name in ['NativeRemaining11Execution20261010.md','NativeNextVerification20261010.md']:
 src=REPO/'docs/F2'/name;(R/name).write_bytes(src.read_bytes())
doc=(REPO/'docs/F2/NativeRemaining11Execution20261010.md').read_text()
for phrase in ['2239明确deselected/未执行','不能把这些数相加','不是单run26','全套容量仍BLOCKED','Report GET idle6和PG resources-history Future10继续OPEN','Windows900/Edge240/Node150 NOT_ACCEPTED','visualReview NOT_REVIEWED','所需预算下界严格超过900秒','无法给出能完成全套的最小预算']:
 assert phrase in doc,phrase
plan=(REPO/'docs/F2/NativeNextVerification20261010.md').read_text();assert '本页保留b5发布时的历史计划' in plan and '历史分片设想未实施' in plan
# Record exact source freeze again, not stale after-run derived output.
freeze=read(pathlib.Path('/tmp/sim2act-native-remaining11-20261010/source-freeze.json'));sha='180a4710405b9c06d1e7cc7213b3ffd073d05567'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()==sha
assert len(freeze['files'])==363
for path,digest in freeze['files'].items():assert hashbytes(REPO/path)==digest and hashlib.sha256(subprocess.check_output(['git','show',sha+':'+path],cwd=REPO)).hexdigest()==digest
(R/'source-final-after.json').write_text(json.dumps({'source_sha':sha,'files':freeze['files'],'count':363,'worktree_git_freeze_match':True,'same_before_terminal_audit':True,'product_count':69,'product69_same473':True},indent=2))
out={'verdict':'LIMITED_PASS','audited_manifest_count':267,'audited_manifest_sha256':hashbytes(P/'PUBLISHED_MANIFEST.json'),'all_public_bytes_exact':True,'copy_whitelists':copy_checks,'source363_match':True,'product69_same473':True,'author_PG_page_checks':10,'author_PG_HTTP_requests':28,'author_PG_lock_records':402,'author_PG_lock_span_seconds':span,'layered_browser_checks':[{'scope':r['path'],'checks':r['checks']} for r in scopes],'no_aggregate_disjoint_count_claim':True,'visual_checklist_author_only':True,'old_budget_lower_bound_strictly_gt900_current_full_minimum_UNKNOWN':True,'historical_OPEN_retained':True,'tests_CI_PG_operations':0,'repo_ref_writes':0}
(R/'PUBLICATION_AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

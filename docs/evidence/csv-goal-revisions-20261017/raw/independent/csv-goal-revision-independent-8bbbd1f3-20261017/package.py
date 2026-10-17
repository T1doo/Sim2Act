import collections,hashlib,json,os,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parent
P=Path('/tmp/csv-goal-revision-independent-b1b1b215-20261017')
OLD='b1b1b2159b850ac0a058e2a6cc1e86b275579f79';SHA='8bbbd1f3b6d2d9ee6671aca4729883385087da1f'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):(R/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
x=ET.parse(R/'junit.xml').getroot();s=x if x.tag=='testsuite' else x.find('testsuite');cases=list(x.iter('testcase'))
counts={k:int(s.get(k,'0')) for k in ('tests','failures','errors','skipped')};counts['passed']=counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
assert counts==dict(tests=1,failures=0,errors=0,skipped=0,passed=1),counts
terminal=json.loads((R/'terminal.json').read_text());assert terminal['returncode']==0
save('collected.json',[dict(classname=c.get('classname'),name=c.get('name'),seconds=float(c.get('time','0')),outcome='PASS') for c in cases])
before=json.loads((R/'source-before.json').read_text());after=json.loads((R/'source-after.json').read_text());shared=json.loads((R/'shared-source-after.json').read_text());delta=json.loads((R/'delta.json').read_text())
assert before['inputs']==after['inputs'] and after['equal_to_before'] and after['all_match_git']
assert delta['changed_inputs']==['tests/csv_goal_revision.cjs'] and delta['all126_production_src_byte_identical'] and delta['unchanged_inputs']==605
page_path=next((R/'data').rglob('page-result.json'));page=json.loads(page_path.read_text());info=json.loads((page_path.parent/'info.json').read_text());audit=page['directoryAudit'];requests=page['requests'];checks=page['checks']
assert page['status']=='PASS' and info['case']=='deliver'
assert info['instance'] in audit['visible_instance_ids'] and info['instance2'] in audit['visible_instance_ids'] and audit['check_instance_id'] not in audit['visible_instance_ids']
check=next(i for i in audit['server_items'] if i['id']==audit['check_instance_id']);assert 'csv_goal_check' in check['switch_policy']['roles']
response_matches=[q for q in requests if q['method']=='GET' and q['path']==f"/api/internal/apps/{info['app']}/instances" and q.get('status')==200 and q['response']['items']==audit['server_items']]
assert response_matches
check_post=next(q for q in requests if q['method']=='POST' and q['path'].endswith('/csv-goal-revisions/checks') and q.get('status')==202)
assert requests.index(check_post)<requests.index(response_matches[-1])
assert check_post['response']['check_instance_id']==audit['check_instance_id']
assert all(isinstance(q.get('status'),int) for q in requests)
assert any('explicit original business selection' in c for c in checks)
assets=[]
for a in page['assets']:
 p=R/'snapshot/src/sim2act/web'/(a['path'].lstrip('/') or 'index.html')
 assets.append(dict(path=a['path'],sha256=a['sha256'],matches_frozen_input=digest(p)==a['sha256']))
assert all(a['matches_frozen_input'] for a in assets)
save('directory-proof.json',dict(actual_page=page_path.relative_to(R).as_posix(),audit=audit,matching_actual_list_reply_indices=[requests.index(q) for q in response_matches],accepted_check_post_index=requests.index(check_post),fresh_response_after_accepted_check=True,server_check_role=check['switch_policy']['roles'],both_business_instances_visible=True,check_instance_excluded_from_visible_business_directory=True,explicit_original_selection_check=next(c for c in checks if 'explicit original business selection' in c),complete_original_checked_chain_follows=True))
save('asset-proof.json',assets)
dbs=[]
for p in sorted((R/'data').rglob('*.db')):
 if p.is_symlink():continue
 c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
 try:
  names=[row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  dbs.append(dict(path=p.relative_to(R).as_posix(),tables={n:c.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in names},run_statuses=dict(c.execute('SELECT status,count(*) FROM runs GROUP BY status'))))
 finally:c.close()
save('database-summary.json',dbs)
expected={'review.json':'19b88fc6a6f00ff87bb4a82ff63a1d052acebed201f29e1b1cfb302784d4f8dd','proof.json':'e4eab8ba387fa45510377c5a94b11b46e5dfe8c606c04f92bc708eff9a379b52','raw-manifest.json':'a31db21735a382e5f375d400f23782f05712534e349349e8b012d4c91fbe758a','SHA256SUMS':'8e04ef5b3b9a0f3132804fd0cda95dea33f6d12c13be832c385872e71495cb1f','source-after.json':'eb3f593d2b4520f6bcc9ea4fac5b3fe7a98060828e99ededc8319d5ae3276a54','junit.xml':'fa76c8c9344a2e4d3432e4eb60e14b7081c2dd32aff9e635d9ca6d9909f8ac1b'}
prior=[]
for n,h in expected.items():
 assert digest(P/n)==h
 prior.append(dict(path=n,bytes=(P/n).stat().st_size,sha256=h))
save('prior-sealed-evidence.json',dict(root=str(P),source_sha=OLD,original_execution=dict(passed=16,failed=0,errors=0,skipped=0,junit_seconds=413.679),files=prior,original_sealed_key_files_unchanged=True,old_directory_not_written=True))
junit=float(s.get('time','0'))
summary=dict(source_sha=SHA,production_source_sha=OLD,counts=counts,junit_seconds=junit,terminal=terminal,input_count=before['count'],input_breakdown=dict(collections.Counter(i['path'].split('/')[0] for i in before['inputs'])),page_checks=len(checks),api_issued=len(requests),actual_replies=len(requests),http_status_counts=dict(collections.Counter(str(q['status']) for q in requests)),assets=len(assets),database_files=len(dbs),directory_proof='directory-proof.json',actual_delivery=[p.relative_to(R).as_posix() for p in (R/'data').rglob('actual-browser-delivery.json')])
save('summary.json',summary)
proof=dict(source_sha=SHA,production_source_sha=OLD,returncode=0,junit_seconds=junit,automatic_retries=0,actual_current_nodes=1,original_sealed_nodes=16,independent_execution_count=17,effective_unique_nodes=16,effective_attribution=[dict(source_sha=OLD,passed_nodes_used=15),dict(source_sha=SHA,passed_nodes_used=1,node='test_visible_same_goal_revision_check_release_adopt_and_new_run[deliver]')],additional_unique_over_author=0,all606_snapshot_inputs_equal_git_before_after=True,shared_source_after_head=shared['head'],shared_source_after_equals_frozen=shared['equal_to_frozen'],production_src126_unchanged_from_b1=True,other605_inputs_unchanged_from_b1=True,changed_input='tests/csv_goal_revision.cjs',extra_input='docs/evidence/bounded-agent-offline-20261006/independent-gold.json',original_stale_list_gap_replaced_by_fresh_actual_list_and_explicit_original_selection=True,original_sealed_files_unchanged=True,not_claiming_full16_rerun_on_8bbb=True)
save('proof.json',proof)
review=dict(verdict='PASS_BOUNDED',production_source_sha=OLD,test_only_source_sha=SHA,current_execution=counts,junit_seconds=junit,effective_scope='16 unique / 17 independent executions: b1 original16 passed; effective15 original nodes + targeted8bbb deliver replacement. No full16 rerun at8bbb.',static_review='No remaining production blocker found in the finite same-app Goal v2/explicit column/isolated CHECK/new Release/original-instance CAS adoption path. The sole changed test driver closes the stale-directory oracle gap and leaves all126 production files plus other605 inputs identical.',dynamic_resolution='After actual accepted and executed CHECK, visible project navigation requests a new actual instance list containing that CHECK with csv_goal_check role. Both business instances are visible while CHECK is excluded. Explicit original-instance selection then resumes the original checked intent and completes Release approval, original-instance adoption, new quantity result and independent human PENDING; old amount result and provenance remain.',directory_proof='directory-proof.json',semantic_scope='One finite same-material next Goal version and explicit column definition. Registered deterministic sum PASS is separate from general goal semantic UNKNOWN, human PENDING and unpublished status. No generalized natural-language interpretation or retroactive human acceptance.',authority_scope='Same original app/runtime and original candidate/generation retained; no new executor/runtime/Grant type or revision-created Grant rows. Existing synthetic fixture policies remain. New Store objects reuse SQLite; this is not independent process restart.',not_run=['real provider/model','PG','native browser','Windows','CI','deployment','process restart','real human semantic acceptance','cross-platform-cap history','extra failure/recovery matrix'],evidence_root=str(R),prior_original_root=str(P),original_b1_directory_remains_sealed=True,artifact_note='This slice produces structured result/delivery JSON, not a new artifact save or Blob download; no Blob claim.',sql_note='Original two API SQL ordering assertions were executed in b1 tests; no additional SQL trace test or sidecar was created by this targeted page repeat.')
save('review.json',review)
entries=[]
for folder,dirs,files in os.walk(R,followlinks=False):
 dirs[:]=[n for n in dirs if n not in ('snapshot','pytest-cache','__pycache__') and not (Path(folder)/n).is_symlink()]
 for n in files:
  p=Path(folder)/n
  if p.is_symlink() or p.suffix=='.pyc' or n in ('raw-manifest.json','SHA256SUMS'):continue
  rel=p.relative_to(R).as_posix();entries.append(dict(path=rel,bytes=p.stat().st_size,sha256=digest(p),classification='original-test-output' if rel.startswith('data/') or n in ('pytest.log','junit.xml','terminal.json') else 'original-independent-provenance-or-review'))
entries.sort(key=lambda e:e['path'])
save('raw-manifest.json',dict(source_sha=SHA,count=len(entries),excluded=['reconstructible Git snapshot','pytest-cache','pycache','dependency symlinks','manifest/sums self-reference'],files=entries))
(R/'SHA256SUMS').write_text(''.join(e['sha256']+'  '+e['path']+'\n' for e in entries))
assert all((R/e['path']).stat().st_size==e['bytes'] and digest(R/e['path'])==e['sha256'] for e in entries)
print(json.dumps(dict(ready=True,root=str(R),verdict='PASS_BOUNDED',counts=counts,junit_seconds=junit,manifest_entries=len(entries),summary=summary,hashes={n:digest(R/n) for n in ('review.json','proof.json','raw-manifest.json','SHA256SUMS','source-after.json','junit.xml','delta.json','directory-proof.json','prior-sealed-evidence.json')}),ensure_ascii=False,indent=2))

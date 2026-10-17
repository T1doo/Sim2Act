import pathlib,json,hashlib,sqlite3,xml.etree.ElementTree as ET,stat
root=pathlib.Path(__file__).parent
before=json.loads((root/'inputs-before.json').read_text())
snap=root/'snapshot'
files=[];differences=[]
for prior in before['files']:
 p=snap/prior['path'];raw=p.read_bytes()
 actual={'path':prior['path'],'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
 files.append(actual)
 if any(actual[k]!=prior[k] for k in ('git_blob','sha256','bytes')):differences.append(prior['path'])
expected={v['path']for v in before['files']}
extra=[str(p.relative_to(snap))for p in snap.rglob('*')if p.is_file() and str(p.relative_to(snap))not in expected]
after={'git_commit':before['git_commit'],'files':files,'changed_inputs':differences,'unexpected_files':extra,'all_git_objects_equal':not differences and not extra}
(root/'inputs-after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n')
execution=json.loads((root/'execution-result.json').read_text())
tree=ET.parse(root/'junit.xml'); cases=[]
for case in tree.iter('testcase'):
 cases.append({'classname':case.attrib.get('classname'),'name':case.attrib.get('name'),'seconds':float(case.attrib.get('time',0)),'outcome':'FAIL'if case.find('failure')is not None or case.find('error')is not None else 'SKIP'if case.find('skipped')is not None else 'PASS'})
observations=[]
for d in sorted((root/'data').iterdir()):
 if d.is_symlink()or not d.is_dir()or not(d/'fixture.db').is_file():continue
 db=d/'fixture.db';connection=sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True)
 connection.row_factory=sqlite3.Row
 try:
  tables=[row[0]for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
  counts={name:connection.execute('SELECT COUNT(*) FROM "'+name+'"').fetchone()[0]for name in tables}
  runs=[dict(row)for row in connection.execute('SELECT id,status,error,goal,request_key,fence,worker_id,lease_until FROM runs ORDER BY id')]
  claims=[dict(row)for row in connection.execute("SELECT run_id,COUNT(*) AS claims FROM events WHERE kind='CLAIMED' GROUP BY run_id")]
  instances=[dict(row)for row in connection.execute('SELECT id,release_id,revision,data_version FROM internal_instances ORDER BY id')]
 finally:connection.close()
 observation={'case_dir':d.name,'sqlite_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),'tables':counts,'runs':runs,'instances':instances,'claimed_events':claims}
 pos=d/'actual-successive-delivery.json';neg=d/'actual-successive-negative.json'
 if pos.exists():
  value=json.loads(pos.read_text());observation.update(kind='positive',goal_mode=value['goal_mode'],spec_revision=value['proposal']['spec_revision'],goal_version=value['proposal']['context']['goal']['version'],new_result=value['new_run']['result'],new_result_version=value['new_run']['result_version'],owner_acceptance=value['pending']['owner_acceptance'])
  observation['positive_receipt_checks']=value['proposal']['spec_revision']==3 and value['new_run']['result']['sum']=='30'and value['new_run']['result_version']==3 and value['pending']['owner_acceptance']=='PENDING'
 if neg.exists():
  value=json.loads(neg.read_text());rejections={label:{'status':v['status'],'same_database':v['before_database_fingerprint']==v['after_database_fingerprint']}for label,v in value.items()if isinstance(v,dict)and'before_database_fingerprint'in v}
  observation.update(kind='negative',fault=value['fault'],rejections=rejections,old_raw_rows_preserved=value.get('old_raw_rows_preserved'),model_attempt_count=value.get('model_attempt_count'))
 observations.append(observation)
(root/'sqlite-observations.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2)+'\n')
summary={'reviewed_commit':before['git_commit'],'execution':execution,'junit_cases':cases,'passed':sum(v['outcome']=='PASS'for v in cases),'failed':sum(v['outcome']=='FAIL'for v in cases),'skipped':sum(v['outcome']=='SKIP'for v in cases),'unique_cases':len(cases),'input_files':len(files),'all_inputs_git_identical':after['all_git_objects_equal'],'sqlite_fixtures':len(observations),'all_sqlite_model_attempts_zero':all(v['tables'].get('attempts')==0 for v in observations),'scope':'Only 2 requested API positives + 5 requested API negatives. No UI Worker case, v3-to-v4/spec8 chain, PG, Windows, real model, remote CI, or deployment.','upgrade_boundary':'d74 currentRelease UI skips required derive for saved prior-software v2; root separately preparing exact-key GET recovery correction. These 7 d74 tests do not verify that later patch.'}
(root/'result-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k]for k in ['reviewed_commit','passed','failed','skipped','unique_cases','input_files','all_inputs_git_identical','sqlite_fixtures','all_sqlite_model_attempts_zero']},indent=2))

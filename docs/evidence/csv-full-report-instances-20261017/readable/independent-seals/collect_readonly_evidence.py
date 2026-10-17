import hashlib, json, pathlib, sqlite3, xml.etree.ElementTree as ET
out=pathlib.Path('/tmp/f2-csv-full-report-d2bacd5c-seals-independent')
meta=json.loads((out/'inputs-before.json').read_text())
snapshot=out/'snapshot'
after={}
for name,expected in meta['files'].items():
 p=snapshot/name
 raw=p.read_bytes()
 digest=hashlib.sha256(raw).hexdigest()
 blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 after[name]={'sha256':digest,'git_blob':blob,'mode':oct(p.stat().st_mode & 0o777)}
 assert digest==expected['sha256'] and blob==expected['git_blob'] and after[name]['mode']=='0o444',name
actual={str(p.relative_to(snapshot)) for p in snapshot.rglob('*') if p.is_file()}
assert actual==set(meta['files'])
(out/'inputs-after.json').write_text(json.dumps({'input_count':len(after),'sha256_and_git_blob_match_before':True,'no_extra_files':True,'files':after},indent=2)+'\n')
dbs=[]
for p in sorted((out/'pytest').glob('*/fixture.db')):
 if p.parent.is_symlink():
  continue  # pytest's *current aliases are not additional fixtures or tests.
 digest_before=hashlib.sha256(p.read_bytes()).hexdigest()
 con=sqlite3.connect(p.as_uri()+'?mode=ro&immutable=1',uri=True)
 con.row_factory=sqlite3.Row
 tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
 rows={}
 for table in tables:
  rows[table]=[dict(r) for r in con.execute('SELECT * FROM "'+table.replace('"','""')+'"')]
  rows[table].sort(key=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,default=str))
 names=['runs','attempts','reservations','operations','internal_app_runs','internal_instances','internal_instance_data','internal_releases']
 observations={'db_path':str(p),'db_sha256_before_read':digest_before,'table_count':len(tables),'row_counts':{k:len(v) for k,v in rows.items()},'runs':[{'id':r['id'],'status':r['status'],'fence':r['fence'],'worker_id':r['worker_id'],'request_key':r['request_key']} for r in rows['runs']],'claims':[{'run_id':r['run_id'],'data':json.loads(r['data'])} for r in rows['events'] if r['kind']=='CLAIMED']}
 con.close()
 digest_after=hashlib.sha256(p.read_bytes()).hexdigest()
 assert digest_before==digest_after
 observations.update(db_sha256_after_read=digest_after,read_only_inspection_preserved_db=True,real_model_calls='NoModel raises on call; attempts and reservations are empty',known_synthetic_mutations='This is the post-counterexample DB: intentional re-signing is retained; it is not a successful unchanged application database.')
 assert observations['row_counts']['attempts']==observations['row_counts']['reservations']==0
 rowsfile=out/(p.parent.name+'-sqlite-rows.json')
 rowsfile.write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str)+'\n')
 observations['rows_path']=str(rowsfile)
 observations['rows_sha256']=hashlib.sha256(rowsfile.read_bytes()).hexdigest()
 http=json.loads((p.parent/'actual-http.json').read_text())
 observations['http_count']=len(http)
 observations['http_last']=http[-1]
 observations['http_status_counts']={str(code):sum(r['status']==code for r in http) for code in sorted(set(r['status'] for r in http))}
 evidencefile=next(p.parent.glob('resigned-*.json'))
 evidence=json.loads(evidencefile.read_text())
 assert evidence['status']==409 and evidence['before_fp']==evidence['after_fp']
 observations['counterexample_file']=str(evidencefile)
 observations['rejected_read_status']=evidence['status']
 observations['before_after_all_table_fingerprint_equal']=True
 dbs.append(observations)
(out/'database-readonly-proof.json').write_text(json.dumps(dbs,ensure_ascii=False,indent=2)+'\n')
root=ET.parse(out/'junit.xml').getroot()
cases=[]
for c in root.iter('testcase'):
 cases.append({'classname':c.attrib.get('classname'),'name':c.attrib['name'],'seconds':c.attrib.get('time'),'outcome':'FAIL' if c.find('failure') is not None or c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS'})
assert len(cases)==2 and all(c['outcome']=='PASS' for c in cases)
print(json.dumps({'source_input_count':len(after),'source_before_after_equal':True,'cases':cases,'databases':[{'path':v['db_path'],'tables':v['table_count'],'http_count':v['http_count'],'runs':v['runs'],'claims':v['claims'],'rejected_status':v['rejected_read_status']} for v in dbs]},indent=2))

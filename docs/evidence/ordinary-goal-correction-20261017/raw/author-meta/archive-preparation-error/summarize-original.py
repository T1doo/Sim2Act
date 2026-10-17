import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
out=Path('/workspace/ordinary-goal-correction-evidence-20261017');tested='d731199a1fd6272e1a79e1c761a1461500fd5227';execution=json.loads((out/'final-execution.json').read_text());assert execution['source']==tested and execution['unique_nodes']==execution['all_collected']==37 and execution['inputs_unchanged'] and execution['clean_worktree']
seals=[]
for label,source,verdict,path in [('independent-superseded-7378','7378b97ec0d85f821c9830290d5075e831270e33','BLOCK','/tmp/ordinary-corrections-independent-7378b97e-20261017'),('independent-final',tested,'PASS','/tmp/ordinary-corrections-independent-d731199a-20261017')]:
 p=Path(path);manifest=json.loads((p/'raw-manifest.json').read_text());review=json.loads((p/'review.json').read_text());assert manifest['source_sha']==source and review['verdict']==verdict and review['source_sha']==source
 for item in manifest['files']:
  f=p/item['path'];assert f.stat().st_size==item['size'] and hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256']
 seals.append(dict(directory=path,label=label,source=source,verdict=verdict,manifest_entries=len(manifest['files']),original_outputs_including_manifest_and_sums=len(manifest['files'])+2,sha256={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['review.json','proof.json','raw-manifest.json','raw-sha256sums.txt']}))
(out/'independent-seals-verified.json').write_text(json.dumps(dict(seals=seals),indent=2)+'\n')
rows=[];data=Path('/tmp/ordinary-goal-correction-author-final-d731199a-pages-20261017')
for f in sorted(data.glob('test_visible_explicit_ordinary*/result.json')):
 if 'current' in f.parent.name:continue
 v=json.loads(f.read_text());assert v['status']=='PASS';requests=v['requests'];downloads=[]
 for item in v['downloads']:
  original=f.parent/item['original'];raw=original.read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'] and item['revoked'];downloads.append({**item,'path':str(original)})
 boundary=json.loads((f.parent/'model-boundary.json').read_text());assert boundary['real_model_requests']==0
 rows.append(dict(case=v['case'],checks=len(v['checks']),recorded_api_attempts=len(requests),actual_replies=sum(isinstance(r.get('status'),int) for r in requests),synthetic_not_sent=sum(r.get('synthetic_phase')=='NOT_SENT' for r in requests),assets=len(v['assets']),downloads=downloads,actual_worker_objects=boundary['actual_worker_objects'],child_synthetic_requests=sum(boundary['child_synthetic_requests']),path=str(f)))
assert len(rows)==6
totals={k:sum(r[k] for r in rows) for k in ['checks','recorded_api_attempts','actual_replies','synthetic_not_sent','assets','actual_worker_objects','child_synthetic_requests']};assert totals==dict(checks=225,recorded_api_attempts=410,actual_replies=409,synthetic_not_sent=1,assets=138,actual_worker_objects=11,child_synthetic_requests=14)
models=[]
for part in execution['parallel_shards']:
 p=out/('final-author-'+part['name']);v=json.loads((p/'final-correction-models.json').read_text());models.extend(v['calls']);assert part['rc']==0
summary=dict(source=tested,author_input_count=execution['input_count'],author_unique_nodes=37,author_wall_seconds=execution['wall_seconds'],author_shards=[{k:p[k] for k in ('name','nodes','rc','wall_seconds','junit')} for p in execution['parallel_shards']],new_page_cases=rows,new_page_totals=totals,new_page_actual_blob_originals=sum(len(r['downloads']) for r in rows),instrumented_CorrectionModel_requests=len(models),model_count_excludes_parent_and_legacy=True,child_page_14_included_in_model_count=True,real_model_requests=0,real_human_signoff='NOT_RUN',semantic_acceptance='NOT_RUN',separate_process_restart='NOT_RUN',pg='NOT_RUN',native_browser='NOT_RUN',Windows='NOT_RUN',remote_CI='NOT_RUN',author_additive_SQLite_migration=json.loads((out/'migration-proof.json').read_text()),independent_migration_probe='NOT_RUN')
assert summary['new_page_actual_blob_originals']==4 and len(models)==30
(out/'final-scope-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:summary[k] for k in ['source','author_input_count','author_unique_nodes','author_wall_seconds','new_page_totals','instrumented_CorrectionModel_requests']},ensure_ascii=False))

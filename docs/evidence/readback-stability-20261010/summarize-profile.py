import json,hashlib
from pathlib import Path
r=Path('/tmp/sim2act-read-stability-20261010');out=[]
for folder in ['baseline-sqlite-profile','baseline-pg-profile','probe-sqlite-profile','sqlite-profile','pg-profile']:
 for p in sorted((r/folder).glob('*.json')):
  d=json.loads(p.read_text());records=[]
  for rec in d['records']:
   value={k:v for k,v in rec.items() if k not in ['sql','cpu_start','thread']}
   value['sql_trace_records']=len(rec['sql']);value['calls']=rec['calls']
   records.append(value)
  out.append(dict(file=p.relative_to(r).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),node=d['node'],source_sha=d['source_sha'],records=records))
result=dict(records=out,baseline_profiler='v1; history roots only, no CPU recording',final_profiler='v2; adds app/history and thread CPU, final selected 2 original nodes only',comparison='SQL/call counts are diagnostic; wall times from differing profile/load contexts are not a benchmark',raw_sql_parameters_recorded=False,timeout_changes=False,baseline_historical_timeouts_reproduced=False,Report_GET_IDLE_6='OPEN',PG_resources_history_Future_10='OPEN',host_cpu_cgroup='400000 100000',final_concurrent_runs=['author SQLite','author PG','independent SQLite/pages'])
(r/'profile-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('Saved',len(out),'raw profile summaries')

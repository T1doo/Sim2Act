from pathlib import Path
p=Path('/tmp/project-column-versions-independent/backend.py')
s=p.read_text();exec(compile(s[:s.index("if not os.environ.get('INDEPENDENT_ONLY_COLD'):")],str(p),'exec'))
from sqlalchemy import update
from sim2act.db import grants
out={'source_sha256':hashes,'checks':[]}
with env() as e:
 vals,p,base,pv,cf,group=create(e)
 entry=group['entries'][0];path='/api/internal/releases/'+entry['release_id']+'/project-column-origin'
 with e[0].tx() as c:c.execute(update(grants).where(grants.c.resource_id==vals[5]).values(expires_at=0))
 before=snapshot(e)
 for endpoint in ('/api/internal/releases/'+entry['release_id'],path):
  with statements(e[0]) as seen:r=e[2].get(endpoint)
  item=dict(path=endpoint,http_status=r.status_code,body=r.json(),zero_writes=snapshot(e)==before,statements=seen)
  try:
   assert r.status_code==403,r.text;assert_no_ledger_read(seen);assert item['zero_writes'];item['status']='PASS'
  except Exception:item.update(status='FAIL',error=traceback.format_exc())
  out['checks'].append(item)
 out['status']='PASS' if all(v['status']=='PASS' for v in out['checks']) else 'FAIL'
 out['source_sha256_after']={f:hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in hashes}
 assert out['source_sha256_after']==hashes
 (ROOT/'peer-source-grant-probe-fixed.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items() if k not in ['source_sha256','source_sha256_after','statements']},ensure_ascii=False,indent=2),flush=True)
 raise SystemExit(out['status']!='PASS')

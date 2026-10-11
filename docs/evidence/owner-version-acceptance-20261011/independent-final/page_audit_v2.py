"""Read-only aggregation of actual JSDOM IPC/HTTP receipts and visible gestures."""
import collections
import hashlib
import json
from pathlib import Path

OUT=Path('/tmp/owner-version-acceptance-review-20261011')
WEB=Path('/workspace/Sim2Act/src/sim2act/web')
summary={'status':'PASS','scenarios':[],'checks':0,'visible_dom_gestures':0,'summary_records':0,
         'actual_resource_gets':0,'boots':0,'resource_mismatches':[],
         'transport':'actual IPC/in-process HTTP into JSDOM',
         'live_models':0,'human_choices':'SIMULATED','native_browser':'NOT_RUN'}
pages=sorted((OUT/'sealed2-pages').glob('*.json'))
assert len(pages)==25
for p in pages:
    d=json.loads(p.read_text())
    assert d['status']=='PASS',p
    actions=d['user_actions']
    gestures=[a for a in actions if a.get('event')=='native DOM dispatch']
    assert all(a['visible'] and a['enabled'] for a in gestures),p
    receipts=d['static_resource_loads']
    row={'scenario':p.stem,'status':d['status'],'checks':len(d['checks']),
         'visible_dom_gestures':len(gestures),'summary_records':len(actions)-len(gestures),
         'actual_resource_gets':len(receipts),'boots':len({x['boot'] for x in receipts}),
         'loaded_asset_count':len(d['loaded_source_sha256']),
         'script_count':sum(x.endswith('.js') for x in d['loaded_source_sha256']),
         'owner_commands':dict(collections.Counter(x['body']['command'] for x in d['requests']
                 if x['method']=='POST' and x['path'].endswith('/owner-review-requests')))}
    assert row['loaded_asset_count']==19 and row['script_count']==17,row
    summary['scenarios'].append(row)
    for field in ['checks','visible_dom_gestures','summary_records','actual_resource_gets','boots']:
        summary[field]+=row[field]
    for a in receipts:
        name='index.html' if a['path']=='/' else a['path'].lstrip('/')
        raw=(WEB/name).read_bytes()
        ctype='text/html' if name=='index.html' else 'text/css' if name.endswith('.css') else 'text/javascript'
        assert a['status']==200 and a['content_type'].startswith(ctype),a
        assert a['bytes']==len(raw) and a['sha256']==hashlib.sha256(raw).hexdigest(),a
    for name,sha in d['loaded_source_sha256'].items():
        assert hashlib.sha256((WEB/name).read_bytes()).hexdigest()==sha,name
    for ending in ['/application-runs','/confirm-application-candidate']:
        assert len([x for x in d['requests'] if x['method']=='POST' and x['path'].endswith(ending)])==1,(p,ending)
summary['scenario_count']=len(pages)
assert summary['actual_resource_gets']==summary['boots']*19
with (OUT/'sealed2-page-proofs.json').open('x') as f:
    json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in summary.items() if k!='scenarios'},indent=2))

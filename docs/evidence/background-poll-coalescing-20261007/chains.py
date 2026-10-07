import json,re,statistics
from pathlib import Path
root=Path('/tmp/report-poll-overlap-review');a=json.loads((root/'analysis.json').read_text());ev=[json.loads(x)for x in Path(a['trace']).read_text().splitlines()];S={e['index']:e for e in ev if e['event']=='http_start'};E={e['index']:e for e in ev if e['event']=='http_response'};health=[s for s in S.values()if s['path']=='/health'];chains=[]
patterns=[r'/api/projects/[^/]+/resources$',r'/api/projects/[^/]+/goal-cards$',r'/api/apps$',r'/api/apps/app_[a-f0-9]{32}$',r'/api/projects/[^/]+/conditional-apps$']
for h in health:
 ids=[h['index']];reason=''
 for p in patterns:
  e=E.get(ids[-1])
  if not e:reason='pending';break
  candidates=[s for s in S.values()if re.fullmatch(p,s['path']) and e['elapsed_ms']<=s['elapsed_ms']<=e['elapsed_ms']+30]
  if len(candidates)!=1:reason=f'match_count_{len(candidates)}';break
  ids.append(candidates[0]['index'])
 end=E.get(ids[-1],S[ids[-1]])['elapsed_ms'];ticks=[t['index']for t in health if h['elapsed_ms']<t['elapsed_ms']<end]
 chains.append({'health_id':h['index'],'ids':ids,'paths':[S[i]['path']for i in ids],'span_ms':end-h['elapsed_ms'],'start_ms':h['elapsed_ms'],'end_ms':end,'next_tick_ids':ticks,'stop':reason or 'conditional_list_response','attribution':'inferred source-required sequence; each continuation uniquely within30ms; lacks actual caller labels'})
a['inferred_30ms_mandatory_chains']=chains;a['inferred_overlap_30ms']=[c for c in chains if c['next_tick_ids']];a['inferred_full_refresh_prefixes']=len([c for c in chains if len(c['ids'])==6]);
(root/'analysis.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'full_prefixes':a['inferred_full_refresh_prefixes'],'overlap_count':len(a['inferred_overlap_30ms']),'examples':a['inferred_overlap_30ms']},indent=2))

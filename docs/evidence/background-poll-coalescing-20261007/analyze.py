import json,re,statistics
from pathlib import Path
src=Path('/workspace/Sim2Act-delivery-graph-combined-regression/docs/evidence/delivery-graph-combined-regression-20261007/8c106e9-final/report-driver-progress.jsonl')
ev=[json.loads(l) for l in src.read_text().splitlines()];starts={x['index']:x for x in ev if x['event']=='http_start'};ends={x['index']:x for x in ev if x['event']=='http_response'}
def norm(p):return re.sub(r'(?:proj|app|run|res|grant|goal|check|extract)_[a-f0-9]{32}',':id',p)
def stats(values):
 v=sorted(values);return {'n':len(v),'min':min(v),'median':statistics.median(v),'p90':v[min(len(v)-1,int(.9*len(v)))],'p95':v[min(len(v)-1,int(.95*len(v)))],'max':max(v),'mean':round(statistics.mean(v),2)} if v else {'n':0}
groups={}
for i,s in starts.items():
 key=s['method']+' '+norm(s['path']);g=groups.setdefault(key,{'starts':0,'responses':0,'durations':[],'pending':[]});g['starts']+=1
 if i in ends:g['responses']+=1;g['durations'].append(ends[i]['duration_ms'])
 else:g['pending'].append(i)
for g in groups.values():g['latency_ms']=stats(g.pop('durations'))
inflight=set();peak=0;peaks=[]
for x in ev:
 if x['event']=='http_start':inflight.add(x['index'])
 elif x['event']=='http_response':inflight.discard(x['index'])
 if len(inflight)>peak:peak=len(inflight);peaks.append({'at_ms':x['elapsed_ms'],'concurrent_requests':peak,'ids':sorted(inflight)})
health=[s for s in starts.values() if s['path']=='/health'];followers=[]
for h in health:
 e=ends.get(h['index']); candidates=[s for s in starts.values() if e and e['elapsed_ms']<=s['elapsed_ms']<=e['elapsed_ms']+5 and s['path'].endswith('/resources')]
 followers.append({'health_id':h['index'],'start_ms':h['elapsed_ms'],'resource_ids':[s['index'] for s in candidates]})
# Conservatively assign only immediate response-to-next-request chain; ambiguity stops attribution.
expected=['/resources','/goal-cards','/api/apps','/conditional-apps','/protocol/contracts','/runs','/grants']
chains=[]
for h in health:
 chain=[h['index']];last=h['index'];reason='';
 for _ in range(20):
  e=ends.get(last)
  if not e:reason='pending_response';break
  nxt=[s for s in starts.values() if e['elapsed_ms']<=s['elapsed_ms']<=e['elapsed_ms']+5 and s['method']=='GET' and (s['path'].endswith(('/resources','/goal-cards','/conditional-apps','/runs','/grants')) or s['path']=='/api/apps' or '/protocol/' in s['path'])]
  if len(nxt)!=1:reason='ambiguous_or_unobserved_continuation';break
  n=nxt[0];
  if n['index'] in chain:reason='loop';break
  chain.append(n['index']);last=n['index']
  if n['path'].endswith('/grants'):reason='terminal_grants';break
 endpoint=ends.get(last,starts[last]);next_ticks=[t['index'] for t in health if h['elapsed_ms']<t['elapsed_ms']<endpoint['elapsed_ms']]
 chains.append({'health_id':h['index'],'ids':chain,'paths':[norm(starts[i]['path']) for i in chain],'start_ms':h['elapsed_ms'],'last_observed_ms':endpoint['elapsed_ms'],'observed_span_ms':endpoint['elapsed_ms']-h['elapsed_ms'],'next_health_starts_before_last_response':next_ticks,'attribution':'inferred immediate <=5ms continuation; not caller instrumentation','stop_reason':reason})
result={'trace':str(src),'rows':len(ev),'http_starts':len(starts),'http_responses':len(ends),'health_ticks':len(health),'health_spacing_ms':stats([b['elapsed_ms']-a['elapsed_ms'] for a,b in zip(health,health[1:])]),'by_path':groups,'max_network_inflight':peak,'peak_changes':peaks,'pending_at_cutoff':sorted(inflight),'health_resource_followers':followers,'inferred_chains':chains,'overlap_chains':[c for c in chains if c['next_health_starts_before_last_response']],'checks':[x for x in ev if x['event']=='check'],'fault_targets':len([x for x in ev if x['event']=='fault_target']),'causation':'UNKNOWN: no timer start/end/caller labels; network duration excludes held JSON fault wait'}
Path('/tmp/report-poll-overlap-review/analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['rows','http_starts','http_responses','health_ticks','health_spacing_ms','max_network_inflight','pending_at_cutoff','fault_targets']}));print(json.dumps(result['overlap_chains'],indent=2));print(json.dumps(result['by_path'],indent=2))

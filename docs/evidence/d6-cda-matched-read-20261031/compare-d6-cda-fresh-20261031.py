from pathlib import Path
import json
scratch=Path('/workspace/scratch');pair=json.loads((scratch/'d6-cda-fresh-matched-20261031.json').read_text());assert pair['status']=='COMPLETED'
outputs=[]
for run in pair['runs']:
 prefix=Path(run['case_path']).parent;files={p.resolve().parent for p in prefix.glob('*/use-effective-profile.json')};assert len(files)==1;case=files.pop()
 profile=json.loads((case/'use-effective-profile.json').read_text());snap=json.loads((case/'snapshot-writer-timings.json').read_text());assert not profile['errors'] and profile['open_timed_stack']==0
 shapes=[];stages=[]
 for epoch in (3,4):
  for phase in ('G0','G1'):
   for selector in ('select','select_frontier'):
    rows=[r for r in profile['shapes'] if r['epoch']==epoch and r['phase']==phase and r['selector']==selector]
    shapes.append(dict(cold=epoch-2,phase=phase,selector=selector,successful_capsule_comparisons=sum(r['calls'] for r in rows),nodes_visited=sum(r['calls']*r['shape']['nodes'] for r in rows),edges_visited=sum(r['calls']*r['shape']['edges'] for r in rows),observed_scope_shape_records=len(rows),max_nodes=max((r['shape']['nodes'] for r in rows),default=0),max_inventory_objects=max((r['shape']['inventory_objects'] for r in rows),default=0)))
   interval=next(r for r in profile['phase_intervals'] if r['epoch']==epoch and r['phase']==phase)['elapsed'];rows=[r for r in profile['coarse'] if r['epoch']==epoch and r['phase']==phase];total=sum(r['exclusive_wall_ns'] for r in rows)
   assert total<=interval['wall_ns']
   stages.append(dict(cold=epoch-2,phase=phase,interval_wall_seconds=interval['wall_ns']/1e9,interval_thread_seconds=interval['thread_ns']/1e9,exclusive_coarse=[dict(function=r['function'],seconds=r['exclusive_wall_ns']/1e9) for r in rows],uncovered_seconds=(interval['wall_ns']-total)/1e9))
 outputs.append(dict(source_commit=run['source_commit'],label=run['label'],runtime_module=profile['runtime_module'],binaries=profile['binaries'],records=snap['records'],counts=profile['counts'],shapes=shapes,stages=stages,effective_candidate_transfers=profile['effective_candidate_transfers'],shape_metadata_read_ns=profile['shape_metadata_read_ns']))
assert len(outputs)==2;before,after=outputs;deltas=[]
for i,(b,a) in enumerate(zip(before['records'],after['records'],strict=True),1):
 deltas.append(dict(cold=i,g0_read_delta_seconds=a['g0_read_seconds']-b['g0_read_seconds'],writer_delta_seconds=a['writer_seconds']-b['writer_seconds'],total_delta_seconds=a['seconds']-b['seconds']))
result=dict(baseline_source=before['source_commit'],candidate_source=after['source_commit'],versions=outputs,deltas=deltas,limits='Fresh sequential exact d6/cda exports, same interpreter/native binaries/observer and synthetic input recipe; no parallel measurements, no intermediate run; UUID/clocks differ, all observer overhead retained.  Weighted nodes/edges count ONLY True selectors with an actual capsule; None/calibration/mismatch not counted as zero work. Immutable inventory sizes are retained metadata, not per-comparison traversed nodes and are not multiplied as work. Coarse exclusive stages are nonoverlap; uncovered residual is not attributed to IO/SQL/fsync. Phase boundaries differ slightly from Store snapshot; headline times use Store records. No SLA/live/PG/Windows claim.')
path=scratch/'d6-cda-fresh-matched-comparison-20261031.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(comparison=str(path),deltas=deltas),indent=2))

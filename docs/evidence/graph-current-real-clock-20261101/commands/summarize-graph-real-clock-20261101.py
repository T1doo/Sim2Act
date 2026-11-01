from pathlib import Path
import json
base=Path('/workspace/scratch');rows=[]
for label,stem in [('ownership-baseline','graph-owned-explicit120-27619e9c-20261101'),('fused-current','graph-resolve-explicit120-35eaa941-20261101')]:
 meta=base/(stem+'-run.json')
 if not meta.exists():continue
 m=json.loads(meta.read_text())
 if m['status']!='COMPLETED':continue
 cases=list((base/stem).glob('*0/graph-version-real-clock-profile.json'))
 if len(cases)!=1:continue
 p=cases[0];profile=json.loads(p.read_text());snap=json.loads((p.parent/'snapshot-writer-timings.json').read_text())
 for i,(e,r) in enumerate(zip(profile['epochs'],snap['records'],strict=True),1):
  d=dict(label=label,source=m['source_commit'],ordinal=i,contract='EXPLICIT_SIGNED_SQLITE120_NOT_ORDINARY30',
   g0_read_until_promotion_seconds=r['g0_read_seconds'],snapshot_writer_window_seconds=r['writer_seconds'],snapshot_total_seconds=r['seconds'],outcome=r['outcome'],
   postproof_entered=e['g1_postproof_entered'],first_dml_completed='first_dml_completed_mono' in e)
  if all(k in e for k in ('commit_started_mono','commit_completed_mono','first_dml_attempt_mono','first_dml_completed_mono')):
   d['observed_sqlite_write_lock_lower_seconds']=e['commit_started_mono']-e['first_dml_completed_mono']
   d['observed_sqlite_write_lock_upper_seconds']=e['commit_completed_mono']-e['first_dml_attempt_mono']
  rows.append(d)
report=dict(rows=rows,limits='Same passive observer; wall times include instrumentation and real quota waits before Cold. Snapshot G0+writer/total boundaries differ from Epoch by fractions of a millisecond. SQLite lock bounds are bounds, not exact acquisition instants. SQL timed rows overlap Python exclusives; never add SQL again to their sum. Ordinary30 negative cases are deliberately not in this signed120 table.')
(base/'graph-real-clock-paired-summary-20261101.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

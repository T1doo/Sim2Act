import json,re,sys
from pathlib import Path
prefix=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/workspace/scratch/cold-detailed-profile-20261030')
roots=sorted({p.resolve() for p in prefix.glob('*/passive-profile.json')})
assert len(roots)==1,roots
profile=json.loads(roots[0].read_text());fsync=[];unparsed=[]
pattern=re.compile(r'^\d+\s+(\d+\.\d+)\s+(fsync|fdatasync)\(\d+<([^>]+)>\)\s+=\s+(-?\d+)\s+<(\d+\.\d+)>$')
for line in Path(str(prefix)+'.trace').read_text().splitlines():
 match=pattern.match(line)
 if match:
  wall,call,path,result,seconds=match.groups()
  fsync.append(dict(wall=float(wall),call=call,path=path,result=int(result),seconds=float(seconds)))
 elif 'fsync(' in line or 'fdatasync(' in line or 'resumed>' in line:unparsed.append(line)
assert not unparsed,unparsed[:3]
report=dict(source=json.loads(Path(str(prefix)+'-run.json').read_text()),classification='INSTRUMENTED_ORIGINAL_LARGE_FIXED_MOCK_NOT_PG_NOT_LIVE',phase_records=profile['records'],pending_frames=profile['pending_frames'],pending_sql=profile['pending_sql'],epochs=[])
for epoch in profile['epochs']:
 start,end=epoch.get('first_dml_wall'),epoch.get('commit_end_wall')
 complete=start is not None and end is not None
 selected=None if not complete else [r for r in fsync if start<=r['wall']<=end and r['path'] in {str(roots[0].parent),*(str(roots[0].parent/'fixture.db')+suffix for suffix in ('','-wal','-journal'))}]
 report['epochs'].append(dict(**epoch,first_dml_to_commit_end_seconds=end-start if complete else None,
  writer_fsync_count=None if selected is None else len(selected),writer_fsync_seconds=None if selected is None else sum(r['seconds'] for r in selected),
  writer_fsync_max_seconds=None if selected is None else max([r['seconds'] for r in selected],default=0),writer_fsync_syscalls=selected))
report['limitations']='Profile callbacks/strace overhead included. Phase table aggregates all observed intervals; per-epoch records distinguish completed intervals; overlapping inclusive costs cannot be added. SQL execute excludes fetch/materialization. Complete native comparison includes reducers. Only actual trace-matched writer syscalls classified as fsync; commit is not equated with fsync. firstDML boundary is issued-before-execute upper bound, not VFS lock callback.'
Path(str(prefix)+'-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
for phase,rows in profile['records'].items():
 print(phase)
 for name in ('graph.check','structure.select','structure.frontier','native.compare','native.capture','graph.serialize','pickle.dump','graph.input_bytes','typed.storage','typed.values','graph.typed_parameters','sql.execute.SELECT','sql.execute.UPDATE','sql.execute.INSERT','sql.commit','sqlite.commit'):
  row=rows.get(name)
  if row:print(name,row)
print('epochs',report['epochs'])

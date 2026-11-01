"""Frozen old/new native binaries, one CPU-bound process at a time. Component only."""
import hashlib,importlib.util,json,statistics,subprocess,sys,time
from pathlib import Path
if len(sys.argv)>1:
 from sim2act import natural_spec_runtime as r
 from sqlalchemy.engine import RowMapping
 from sqlalchemy.sql.elements import quoted_name
 from sim2act.contracts import Limits
 path=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('_cold_graph_structure',path)
 native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
 leaves=[dict(id='synthetic-'+str(i),value=i,kind='synthetic fixture',active=True) for i in range(2000)]
 root=dict(inputs=dict(history=leaves),binding=dict(contract=dict(run_seconds=300)))
 scope=(object(),object(),'component-only',0,'pre')
 capsule=native.snapshot(root,RowMapping,Limits,quoted_name,r._cold_graph_row_storage,r._cold_graph_limit_values,scope,r._SOURCE_VIEW_TYPE,r._SOURCE_OWNER_TYPE,root['inputs'])
 assert capsule is not native.UNSUPPORTED
 for _ in range(20):assert native.matches_fast(capsule,root,scope) is True
 before=native.read_structure_counts()['pre'];start=time.thread_time_ns();wall=time.monotonic_ns()
 for _ in range(1200):assert native.matches_fast(capsule,root,scope) is True
 wall=time.monotonic_ns()-wall;elapsed=time.thread_time_ns()-start;after=native.read_structure_counts()['pre']
 print(json.dumps(dict(binary=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cpu_ns=elapsed,wall_ns=wall,calls=1200,delta={k:after[k]-v for k,v in before.items()})))
else:
 root=Path('/workspace/Sim2Act');base='/workspace/scratch/affb-full-comparison-attribution.so';candidate=str(next((root/'src/sim2act').glob('_cold_graph_structure.*.so')))
 rows=[]
 for pair in range(3):
  for label,path in ([('baseline',base),('candidate',candidate)] if pair%2==0 else [('candidate',candidate),('baseline',base)]):
   result=json.loads(subprocess.check_output([sys.executable,__file__,path],text=True));result.update(pair=pair,label=label);rows.append(result)
 output=dict(classification='EXACT_FROZEN_NATIVE_BINARY_COMPONENT_ONLY_NOT_BUSINESS_OR_SLA',rows=rows,median_cpu_ns={label:statistics.median(r['cpu_ns'] for r in rows if r['label']==label) for label in ('baseline','candidate')})
 Path('/workspace/scratch/graph-original-edge-binary-paired-20261101.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output))

"""Same live scope, real perf_counter, complete current Python/C predicates.

This is only a qualifier comparison; it is NOT a Cold/SLA measurement.
"""
import hashlib, json, subprocess, sys, time
from pathlib import Path
from test_cold_accounted_sqlite import sql_facts
from test_cold_use_manifest_owned import graph_scope
from sim2act import _cold_graph_structure_guard as g

root=Path('/workspace/Sim2Act')
out=Path('/workspace/scratch/graph-metadata-qualifier-paired-20261101.json')
assert not out.exists()
data_dir=Path('/workspace/scratch/graph-metadata-qualifier-paired-20261101')
data_dir.mkdir(exist_ok=False)
fixture=sql_facts.__wrapped__(data_dir); f=next(fixture)
rows=[]
try:
    with graph_scope(f) as (graph,limits):
        for pair in range(3):
            for name,fn in [('python_complete',g._qualified_legacy),('native_complete',g._qualified)]:
                a=time.perf_counter()
                for _ in range(1000):
                    assert fn(graph) is True
                rows.append(dict(pair=pair,implementation=name,calls=1000,seconds=time.perf_counter()-a))
finally:
    try:next(fixture)
    except StopIteration:pass
output=dict(classification='QUALIFIER_ONLY_REAL_CLOCK_NOT_COLD_OR_SLA',
    source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).splitlines(),
    rows=rows,real_model_requests=0,
    limits='Same scope and original captured metadata, sequential measurement. Full Cold checks are still required.')
out.write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output))

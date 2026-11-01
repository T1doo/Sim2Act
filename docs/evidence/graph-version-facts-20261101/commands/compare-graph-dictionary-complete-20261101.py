"""Paired complete C content checks; same backend, index ineligible vs eligible.

Not an exact previous binary, not a Cold/lease/SLA or model-flow result.
"""
import json,statistics,time,subprocess
from pathlib import Path
from sim2act import _cold_graph_structure as native,natural_spec_runtime as r
from test_cold_dictionary_versions import capture,scope,counters

output=Path('/workspace/scratch/graph-dictionary-paired-component-20261101.json')
assert not output.exists()
identity=scope()
value=[{'id':i,'payload':'synthetic original payload '+str(i),'number':i+1,'option':None}
       for i in range(2000)]
unreachable=object()
before=counters()
baseline=capture(value,identity,unreachable)
mid=counters()
candidate=capture(value,identity,value)
after=counters()
assert baseline is not native.UNSUPPORTED and candidate is not native.UNSUPPORTED
assert mid['armed_dictionary_versions']==before['armed_dictionary_versions']
assert after['armed_dictionary_versions']-mid['armed_dictionary_versions']==2000
rows=[]
for pair in range(3):
    order=[('ineligible_full_walk',baseline),('eligible_version_facts',candidate)]
    if pair%2:order.reverse()
    for name,saved in order:
        counts_before=counters();begin=time.perf_counter()
        for _ in range(100):assert native.matches_fast(saved,value,identity) is True
        rows.append(dict(pair=pair,mode=name,calls=100,seconds=time.perf_counter()-begin,
            counter_delta={key:counters()[key]-number for key,number in counts_before.items()}))
result=dict(classification='COMPLETE_CONTENT_COMPONENT_ONLY_NOT_COLD_OR_ORIGINAL_BINARY',
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    dirty=subprocess.check_output(['git','status','--porcelain'],text=True).splitlines(),
    rows=rows, medians={name:statistics.median(x['seconds'] for x in rows if x['mode']==name)
        for name in ('ineligible_full_walk','eligible_version_facts')},
    real_model_requests=0,
    limits='2000 persistent synthetic flat raw dicts, identical complete data, sequential pairs. Does not predict real graph coverage or net end-to-end gains.')
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

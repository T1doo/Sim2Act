import copy,json
from fixed_pure_probe import candidate,m,versions,ids,ctx,ROOT
from sim2act.delivery_graph import derive_manifest_graph
from sim2act.contracts import Limits
from sim2act.errors import DomainError
results=[]
for value in [True,1.0]:
 bad=copy.deepcopy(versions);bad[next(iter(bad))]['revision']=value
 try:
  derive_manifest_graph(m,candidate['actions'],bad,ids,ctx,Limits(**m['runtime_limits']))
  result={'raw_revision':value,'type':type(value).__name__,'result':'ACCEPTED_NON_STRICT_SOURCE_VERSION'}
 except DomainError as e:result={'type':type(value).__name__,'result':'REJECTED','code':e.code}
 results.append(result)
(ROOT/'fixed-source-version-result.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))

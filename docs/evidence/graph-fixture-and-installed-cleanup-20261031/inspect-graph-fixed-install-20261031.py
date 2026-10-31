import hashlib,importlib,json,subprocess,sys
from pathlib import Path
expected=sys.argv[1]
repo=Path('/workspace/Sim2Act')
root=Path(sys.prefix)/'lib/python3.12/site-packages'
assert not any('/workspace/Sim2Act/src' in p for p in sys.path)
modules={}
for name in ['api','worker','model','exact_read','synthetic_workspace','contracts','db','natural_spec_runtime','model_settlement','_cold_accounted_receipts']:
 p=Path(importlib.import_module('sim2act.'+name).__file__).resolve()
 raw=subprocess.check_output(['git','show',expected+':src/sim2act/'+name+'.py'],cwd=repo)
 assert p==root/'sim2act'/(name+'.py') and p.read_bytes()==raw
 modules[name]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest()}
native={}
for name in ['_raw_snapshot','_cold_graph_structure','_cold_typed_cohort','_cold_source_owned_impl']:
 m=importlib.import_module('sim2act.'+name)
 native[name]={'file':m.__file__,'source':m.SOURCE_SHA256}
from sim2act import _cold_source_packet
_cold_source_packet.current()
print(json.dumps({'candidate_source':expected,'app':str(root/'sim2act/__init__.py'),'api':modules['api']['path'],'sys_path':sys.path,'modules':modules,'native':native,'original_source_current':True},indent=2))

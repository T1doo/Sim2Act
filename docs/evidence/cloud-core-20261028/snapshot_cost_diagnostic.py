import ast,time,json,statistics,subprocess
from pathlib import Path
from sqlalchemy import select
from sim2act.db import Store,attempts,events
from sim2act import natural_live_admission as gate
source=subprocess.check_output(['git','show','6e46f871:src/sim2act/natural_live_admission.py'],text=True)
tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_trial_pure_data');ns=dict(vars(gate));exec(compile(ast.Module(body=[node],type_ignores=[]),'<frozen-baseline>','exec'),ns);old=ns['_trial_pure_data']
store=Store('sqlite:////workspace/scratch/pb-frozen-20261028/test_pb_production_original_so0/fixture.db',test_only=True)
with store.engine.connect() as c:values=[gate._trial_pure_mapping(r) for r in c.execute(select(attempts)).mappings().all()]+[gate._trial_pure_mapping(r) for r in c.execute(select(events)).mappings().all()]
samples=[]
for i in range(4):
 row={}
 for name,fn in ([('old',old),('current',gate._trial_pure_data)] if i%2==0 else [('current',gate._trial_pure_data),('old',old)]):
  start=time.thread_time()
  for j in range(100):result=fn(values)
  row[name]=time.thread_time()-start
 samples.append(row)
a,b=old(values),gate._trial_pure_data(values)
assert gate._trial_typed_equal(a,b)
out=dict(scope='READ_ONLY_CAPTURED_ORIGINAL_FAILED_DB_ROWS_NOT_A_G0_RUN',samples=samples,medians={name:statistics.median(r[name] for r in samples) for name in ('old','current')},rows=len(values),strict_equal=True,network_requests=0)
Path('docs/evidence/cloud-core-20261028/snapshot-native-cost.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));store.engine.dispose()

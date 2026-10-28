import subprocess,ast,types,time,json,statistics
from pathlib import Path
from conftest import env as env
from test_cold_accounted_sqlite import forbid_execution as forbid_execution,sql_facts as sql_facts
from test_cold_legacy_base_segment import legacy
from sim2act import natural_live_admission as gate

def test_cost(sql_facts):
 raw=subprocess.check_output(['git','show','8e0a42e:src/sim2act/natural_live_admission.py'],text=True)
 tree=ast.parse(raw);definition=next(n for n in tree.body if type(n)is ast.FunctionDef and n.name=='_trial_pure_mapping')
 module=ast.Module(body=[definition],type_ignores=[]);compiled=compile(module,'frozen-8e0-mapping-reference','exec')
 old=next(x for x in compiled.co_consts if type(x)is types.CodeType)
 current=gate._trial_pure_mapping.__code__
 rows=[]
 try:
  with legacy(sql_facts,True) as(t,s):
   for _ in range(3):t._base()
   for turn in range(9):
    row={}
    for name in (('old','candidate') if turn%2==0 else ('candidate','old')):
     gate._trial_pure_mapping.__code__=old if name=='old' else current
     start=time.thread_time()
     for _ in range(60):t._base()
     row[name]=time.thread_time()-start
    rows.append(row)
 finally:gate._trial_pure_mapping.__code__=current
 result=dict(classification='INVOCATION_LOCAL_SYNTHETIC_BASE_COST_ALTERNATING_FROZEN_MAPPING_CODE_NOT_ACCEPTANCE',iterations_per_batch=60,batches=rows,median={k:statistics.median(row[k] for row in rows) for k in ('old','candidate')})
 Path('/workspace/scratch/base-cost-round8-pair.json').write_text(json.dumps(result,indent=2))

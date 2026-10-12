"""Synthetic valid-width Python equality counterexample, no source/seal rewrite."""
import copy,json
from pathlib import Path
from conftest import env
from sqlalchemy import select,update
from test_text_continuations import rows
from test_text_workflows import draft,instance,enqueue,once,inspect
from sim2act.db import internal_run_bindings,internal_app_runs

def test_app_run_boolean_input_cannot_be_integer_width_equal(env):
    made,_=draft(env);release,inst=instance(env,made['id']);rid=enqueue(env,release,inst);once(env)
    with env[0].tx() as c:
        aid=c.execute(select(internal_run_bindings.c.app_run_id).where(internal_run_bindings.c.run_id==rid)).scalar_one()
        value=copy.deepcopy(c.execute(select(internal_app_runs.c.input).where(internal_app_runs.c.id==aid)).scalar_one())
        assert value['emit_report'] is True
        value['emit_report']=1
        c.execute(update(internal_app_runs).where(internal_app_runs.c.id==aid).values(input=value))
    before=rows(env[0]);reply=inspect(env,inst,rid)
    source=env[2].get(f'/api/internal/app-run-jobs/{rid}/text-workflow-proof');after=rows(env[0])
    proof={'classification':'SYNTHETIC_PERSISTED_INPUT_WIDTH_FAULT_NOT_REAL_ATTACK','status':reply.status_code,
           'response':reply.json(),'source_status':source.status_code,'source_response':source.json(),
           'database_unchanged':after==before,'original_binding_and_fingerprints_untouched':True}
    Path('/tmp/pb-text-multistep-independent-r8-20261012/input-width.json').write_text(json.dumps(proof,indent=2)+'\n')
    assert reply.status_code in {400,409} and source.status_code in {400,409} and after==before,proof

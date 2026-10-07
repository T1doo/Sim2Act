import json
from pathlib import Path

import pytest
from sqlalchemy import update

from test_independent_binding import actual_source, env
import test_conditional_run_bindings as plumbing
from sim2act.db import protocol_jobs, runs


@pytest.mark.parametrize('mutation',['run_result_none','job_result_fingerprint'])
def test_actual_result_one_row_mutation(env,tmp_path,mutation):
    rid,result,record,wires,request=actual_source(env,tmp_path)
    with env[0].tx() as c:
        if mutation=='run_result_none':
            c.execute(update(runs).where(runs.c.id==rid).values(result=None))
        else:
            c.execute(update(protocol_jobs).where(protocol_jobs.c.run_id==rid).values(result_fingerprint='0'*64))
    checked=env[2].post(plumbing.base(env)+'/'+rid+'/checks',json={**request,'request_key':'after-one-row-mutation'})
    extracted=env[2].post(plumbing.base(env)+'/extract',json=plumbing.extract_body(rid,result,record,request_key='after-mutation-extract'))
    data={'source_commit':'9dc833ab68e56075a4e76927001c728a4d73c8e8','mutation':mutation,
        'checks_http':checked.status_code,'checks_body':checked.json(),
        'extract_http':extracted.status_code,'extract_body':extracted.json(),
        'actual_mock_calls':len(wires),'only_one_persisted_row_changed':True}
    Path('/tmp/bounded-product-independent-review/'+mutation+'-reproduction.json').write_text(json.dumps(data,indent=2)+'\n')
    assert checked.status_code in (400,409),data
    assert extracted.status_code in (400,409),data

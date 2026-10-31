"""Read-only-repository diagnostic: original writer, synthetic SQLite row only.

It isolates commit time enforcement, not full Cold authorization or throughput.
No production functions are replaced. Original app modules remain unmodified.
"""
import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import event, insert, select, update
from sim2act.db import Store, runs
from sim2act.natural_spec_runtime import _model_writer_connection
from sim2act._sqlite_model_snapshot import promote

root = Path(__file__).parent
database = root / 'synthetic.db'
assert not database.exists(), 'Do not repeat an unknown prior run'
store = Store('sqlite:///' + str(database) + '?timeout=1', test_only=True,
              local_model_snapshots=True)
worker = SimpleNamespace(store=store, stop=threading.Event())
run_id = 'run_' + 'a' * 32
observed = {}
try:
    with store.tx() as c:
        runs.create(c)
        c.execute(insert(runs).values(id=run_id, principal_id='user_'+'b'*32,
            project_id='proj_'+'c'*32, runtime_id='runtime_'+'d'*32,
            status='RUNNING', created_at=time.time(), lease_until=time.time()+.3,
            worker_id='worker_'+'e'*32, version=1, fence=1, context={},
            result=None, error=None, resource_refs=[]))
    with _model_writer_connection(worker, None, None) as (c, plan):
        assert plan is None and not hasattr(worker, '_settlement_interval')
        original = dict(c.execute(select(runs).where(runs.c.id==run_id)).mappings().one())
        assert time.time() < original['lease_until']
        promote(c)
        lease = original['lease_until']
        c.execute(update(runs).where(runs.c.id==run_id).values(
            result={'synthetic_observation': 'commit-tail-only'}))
        assert time.time() < lease
        def consume_original_deadline(connection):
            observed['callback_entered_before_expiry'] = time.time() < lease
            threading.Event().wait(max(0, lease-time.time())+.04)
            observed['callback_returned_after_expiry'] = time.time() > lease
        event.listen(c, 'commit', consume_original_deadline)
    with store.engine.connect() as c:
        saved = dict(c.execute(select(runs).where(runs.c.id==run_id)).mappings().one())
    observed.update(source_sha=subprocess.check_output(['git','rev-parse','HEAD'],
        cwd='/workspace/Sim2Act',text=True).strip(),
        app_functions_replaced=False, model_requests=0,
        actual_writer='_model_writer_connection(worker,None,None)',
        settlement_interval=None, persisted_lease_until=saved['lease_until'],
        verified_observation=saved['result']=={'synthetic_observation':'commit-tail-only'},
        expired_at_return=time.time()>saved['lease_until'],
        snapshot_outcome=store._local_model_snapshot_records[-1]['outcome'],
        scope='Only original writer commit tail; no full Cold/authority acceptance claim')
finally:
    store.engine.dispose()
observed['db_sha256'] = hashlib.sha256(database.read_bytes()).hexdigest()
(root/'result.json').write_text(json.dumps(observed,indent=2,sort_keys=True)+'\n')
print(json.dumps(observed,sort_keys=True))

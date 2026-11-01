import time,threading
import pytest
from sim2act import model_settlement, natural_spec_runtime as rt, _cold_source_packet as source
from sim2act.db import Store
from sim2act._sqlite_run_control import Registry
from types import SimpleNamespace

def test_original_thirty_large_goal_or_safe_budget_refusal(tmp_path):
    store=Store('sqlite:///'+str(tmp_path/'probe.db'),test_only=True,local_model_snapshots=True)
    store._local_model_control=Registry(store)
    worker=SimpleNamespace(store=store,stop=threading.Event())
    job={name:'synthetic-'+name for name in ('id','principal_id','project_id','runtime_id','worker_id')}
    job.update(fence=1,version=1,lease_until=time.time()+30)
    try:
        with store._local_model_control.settlement(worker,job,time.time()+30) as epoch:
            source.current()
            assert rt._cold_graph_bytes({'synthetic':[1,2]})
            worker._settlement_interval=(time.monotonic()-1,time.time()-1)
            with pytest.raises(model_settlement.DomainError):model_settlement.checkpoint(worker)
            del worker._settlement_interval
            epoch.postwrite()
            with store.engine.begin() as c:
                c.exec_driver_sql('CREATE TABLE probe (value INTEGER)')
                c.exec_driver_sql('INSERT INTO probe VALUES (1)')
    finally:store.engine.dispose()

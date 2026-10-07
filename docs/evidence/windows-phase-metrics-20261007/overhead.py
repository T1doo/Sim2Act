import json,time,statistics
from sim2act.db import Store
from windows_phase_metrics import Metrics

def once():
    store=Store('sqlite:///:memory:',test_only=True)
    try: store.initialize()
    finally: store.engine.dispose()
once() # Warm imports/compiler first, not a measured sample.
rows=[]
for active in [False,True,True,False,False,True]:
    collector=Metrics() if active else None
    if collector:collector.install(Store)
    try:
        start=time.perf_counter()
        for _ in range(4):once()
        seconds=time.perf_counter()-start
        row={'enabled':active,'initializations':4,'elapsed_seconds':seconds}
        if collector:row['metrics']=collector.report(0,0)
        rows.append(row)
    finally:
        if collector:collector.uninstall()
off=[r['elapsed_seconds'] for r in rows if not r['enabled']]
on=[r['elapsed_seconds'] for r in rows if r['enabled']]
print(json.dumps({'kind':'linux_sqlite_in_process_observer_overhead','sequence':'OFF ON ON OFF OFF ON',
 'rows':rows,'median_off_seconds':statistics.median(off),'median_on_seconds':statistics.median(on),
 'median_delta_seconds_per_four_initializations':statistics.median(on)-statistics.median(off),
 'limits':'small warm samples, not fixture/PG/Windows/whole-suite cost or a speedup claim'},indent=2))

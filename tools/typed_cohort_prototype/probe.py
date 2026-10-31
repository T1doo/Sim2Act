"""Finite real SQLite-derived cohort differential, with no G0/G1 inference."""
import hashlib
import gc
import json
import os
import statistics
import time
from pathlib import Path

from test_cold_accounted_native import native_segment
from test_cold_accounted_sqlite import forbid_execution as forbid_execution
from test_cold_accounted_sqlite import sql_facts as sql_facts
from test_cold_binding_fact_leaves import local_origin as local_origin
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport

from sim2act import natural_live_admission as gate
from sim2act import _cold_cohort_backend as guarded
from tools.typed_cohort_prototype.backend import CohortBackend


def test_whole_sqlite_cohort(sql_facts, tmp_path):
    assert guarded._READY and guarded.native.current() is True
    backend = CohortBackend()
    f = sql_facts
    with f.store.tx() as c, native_segment(f, c) as s:
        models = []
        gate._graph_trial_journal_models(s.graph, f.store, c, models, s.state, s.cursor)
        gate._graph_trial_stage_models_from_raw(models, s.stage, s.graph.inputs, _owned=s.mode)
        for value in (f.contract, f.requirements, f.approval, f.phase, f.phase.authority,
                      f.frozen, f.frozen.limits, f.extraction[1]):
            gate._trial_typed_hold(models, type(value), value, value.model_dump())
        prior = gc.isenabled()
        gc.disable()  # Explicit test-only domain, applied equally to both arms.
        try:
            gate._trial_typed_values(models)
            backend(models)
            records = []
            for pair in range(4):
                arms = [('original', gate._trial_typed_values), ('candidate', backend)]
                if pair % 2:
                    arms.reverse()
                for name, run in arms:
                    start, cpu = time.monotonic_ns(), time.thread_time_ns()
                    for _ in range(100):
                        run(models)
                    records.append(dict(pair=pair, name=name,
                        wall_ns=time.monotonic_ns()-start, cpu_ns=time.thread_time_ns()-cpu))
        finally:
            if prior:
                gc.enable()
        pairs = []
        for pair in range(4):
            old = next(x for x in records if x['pair']==pair and x['name']=='original')
            new = next(x for x in records if x['pair']==pair and x['name']=='candidate')
            pairs.append(dict(pair=pair, wall_ratio=new['wall_ns']/old['wall_ns'],
                cpu_ratio=new['cpu_ns']/old['cpu_ns'],
                saved_ns_per_call=(old['wall_ns']-new['wall_ns'])/100))
        report = dict(classification='OFFLINE_COMPLETE_SQLITE_TYPED_COHORT_ONLY',
            models=len(models), schemas=[kind.__name__ for kind,_,_ in models],
            raw_json_bytes=sum(len(json.dumps(raw,ensure_ascii=True)) for _,_,raw in models),
            records=records, pairs=pairs,
            median_wall_ratio=statistics.median(x['wall_ratio'] for x in pairs),
            median_cpu_ratio=statistics.median(x['cpu_ratio'] for x in pairs),
            counts=backend.counts(),
            binary_sha256=hashlib.sha256(Path(guarded.native.__file__).read_bytes()).hexdigest(),
            runtime_enabled=False, synthetic_seeded_upstream_attempts=5,
            mock_requests=0, real_model_requests=0,
            g0_runs=0, g1_runs=0)
        report['both_arms_gc_policy'] = 'EXPLICIT_ALREADY_DISABLED_TEST_DOMAIN_ONLY'
        (tmp_path/'cohort-cost.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,sort_keys=True))

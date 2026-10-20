"""Actual pure scans only. Never a graph producer, business fixture or G0."""
import base64
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import socket
import sys
import time
from unittest.mock import patch

REPO = Path('/workspace/Sim2Act')
sys.path.insert(0, str(REPO / 'src'))
import httpx
from sqlalchemy.engine import RowMapping
from sqlalchemy.engine.result import SimpleResultMetaData
from sim2act import natural_live_admission as gate
from sim2act import natural_spec_runtime as runtime
from sim2act.contracts import Limits
from sim2act.db import Store
from sim2act.model import InternModel
from sim2act.spec_production import ProductionTrialBinding, VERSION
from sim2act.worker import Worker

OUT = Path('/tmp/sim2act-cold-scan-profile-20261020')
tripwires = []
def deny(*args, **kwargs):
    tripwires.append('prohibited call')
    raise AssertionError('offline pure-scan boundary')

with patch.object(Store, '__init__', deny), patch.object(Store, 'tx', deny), \
     patch.object(Worker, '__init__', deny), patch.object(Worker, 'once', deny), \
     patch.object(InternModel, '__init__', deny), patch.object(socket, 'getaddrinfo', deny), \
     patch.object(socket.socket, 'connect', deny), \
     patch.object(httpx.HTTPTransport, 'handle_request', deny), \
     patch.object(httpx.AsyncHTTPTransport, 'handle_async_request', deny), \
     patch.object(httpx.MockTransport, 'handle_request', deny), \
     patch.object(httpx.MockTransport, 'handle_async_request', deny):
    source = REPO / 'docs/evidence/g0-monitored-second-20261020/RUN'
    prefix = json.loads((source / 'prefix-proof.json').read_text())
    wire = [json.loads(line) for line in (source / 'mock-exchanges.jsonl').read_text().splitlines()]
    contract = gate.PBTrialContract.model_validate(prefix['contract'])
    caps = Limits(max_requests=4, max_tools=4, max_repairs=1,
                  max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)
    binding = object.__new__(ProductionTrialBinding)  # NO __post_init__ or authority.
    for name, value in dict(contract=contract, approval_key=prefix['approval_key'],
        account_id='OFFLINE-NO-AUTHORITY', version=VERSION,
        contract_fingerprint='0' * 64).items():
        object.__setattr__(binding, name, value)
    payloads = [(base64.b64decode(r['request_b64']), base64.b64decode(r['response_b64'])) for r in wire]
    rows = [RowMapping(SimpleResultMetaData(['id', 'context']), None, {'id': 0, 'context': 1},
        (f'synthetic-{i}', {'wire': payloads[i % 6], 'contract': prefix['contract']},
         {'hidden_unused_position': ['complete', i]})) for i in range(40)]
    guard = object.__new__(runtime._ColdGraphRead)  # Only pure input_* methods.
    guard.binding = binding
    guard.inputs = {'raw_contract': prefix['contract'], 'payloads': payloads, 'rows': rows,
                    'row_aliases': [rows[0], rows[0]]}
    guard.role_limits = {name: caps for name in ('source','generate','platform','trial','per_use')}
    guard.phase = 'pre'
    guard._diagnostic_counts = [0, 0]
    raw = gate.PBTrialContract.model_dump(contract, warnings=False)
    cohort = [(gate.PBTrialContract, contract, raw), (Limits, caps, caps.model_dump())]
    tasks = {
        'actual_input_key_full_bytes_sha': lambda: guard.input_key(),
        'actual_typed_storage_contract': lambda: gate._trial_typed_storage(gate.PBTrialContract, contract),
        'actual_pure_data_contract': lambda: gate._trial_pure_data(raw),
        'actual_typed_cohort_full': lambda: gate._trial_typed_values(cohort),
        'actual_initial_validator': lambda: runtime._cold_graph_validate_inputs(guard.inputs),
    }
    results = {}
    for name, task in tasks.items():
        task()
        start = time.perf_counter(); cpu = time.process_time()
        for _ in range(100): task()
        plain = dict(iterations=100, wall_seconds=time.perf_counter()-start,
                     cpu_seconds=time.process_time()-cpu)
        profiler = cProfile.Profile()
        profiler.enable()
        for _ in range(100): task()
        profiler.disable()
        profiler.dump_stats(str(OUT / (name + '.pstats')))
        stats = pstats.Stats(profiler)
        rows_stats = []
        for (filename, line, function), (primitive, calls, own, cumulative, _) in stats.stats.items():
            rows_stats.append(dict(file=filename, line=line, function=function,
                calls=calls, primitive_calls=primitive, self_seconds=own, cumulative_seconds=cumulative))
        results[name] = dict(plain=plain, profile_total_seconds=stats.total_tt,
            top_self=sorted(rows_stats,key=lambda x:x['self_seconds'],reverse=True)[:18],
            top_cumulative=sorted(rows_stats,key=lambda x:x['cumulative_seconds'],reverse=True)[:18])
    result = dict(scope='ACTUAL_PURE_FUNCTIONS_ON_STORED_JSON_AND_SYNTHETIC_ROWS_NOT_FULL_G0',
        python=sys.version, input_bytes=len(guard.input_bytes()), input_key=guard.input_key(),
        shell='uninitialized exact-class objects, input_* only; no authority or graph check',
        row_count=len(rows), contract=hashlib.sha256((source/'prefix-proof.json').read_bytes()).hexdigest(),
        transport_or_business_calls=len(tripwires), fixtures_imported=[k for k in sys.modules if k.startswith('test_')],
        results=results)
    assert not tripwires and not result['fixtures_imported']
    (OUT/'PROFILE.json').write_text(json.dumps(result,indent=2)+'\n')
    for name, result in results.items():
        print(name, json.dumps(result['plain']))
        for row in result['top_self'][:6]: print(' ',row['function'],row['calls'],round(row['self_seconds'],5))

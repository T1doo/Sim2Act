#!/usr/bin/env python3
"""Re-read a preserved ordinary PB prefix; never execute a Run or grant authority.

This is an outside-repository diagnostic, not a new G3/Source2 acceptance test.
Capture a source lock after the writer freezes its files, then run against that
lock. Every explicit repetition gets a fresh byte-identical DB copy and bounded
subprocess. No source tree, bundle, artifact directory or old environment is copied.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import contextlib
import copy
import faulthandler
import functools
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import traceback


DEFAULT_DB = Path('/workspace/pb-cold-graph-integration-20261019/first-binding-v2-tmp/'
                  'test_plain_pb_first_binding_pr0/plain-prefix.db')
SCOPE = ('Existing current-environment ordinary synthetic G3/Source2 facts reused; '
         'dormant _cold_first_binding read only; no new G3/Source2, Cold execution, '
         'model call, trial approval, account authority, journal allowance or settlement.')


class PassiveCodecCostTap:
    """Tap original calls/returns only. Never compute a product codec/hash/query.

    Each original executes once. HASH/bytes objects and original exceptions are
    returned unchanged. Constructor input bytes are counted only while a tapped
    product function is active; harness evidence/manifest hashes are excluded.
    """
    def __init__(self, phase):
        self.phase = phase
        self.local = threading.local()
        self.report = dict(
            scope='Read-only reused-prefix codec cost, not full-PB performance',
            labels=[], metrics={}, metrics_by_phase={}, returned_bytes={}, hash_inputs={},
            secondary_errors=[],
            definition='Inclusive wall/thread CPU; exclusive subtracts immediate tapped child bodies only. Existing/new observer overhead remains.',
            hash_coverage='Original hashlib.sha256 constructor only; original HASH object returned, no update/hexdigest proxy. Complete input_key includes original digest.',
            byte_coverage='len of exact original returned bytes only. Nested codec/input_bytes volumes overlap; do not sum as unique bytes.')

    def stack(self):
        if not hasattr(self.local, 'stack'):
            self.local.stack = []
        return self.local.stack

    @staticmethod
    def add_metric(table, key, elapsed, cpu, frame, returned):
        m = table.setdefault(key, dict(count=0, returned=0, exceptions=0,
            wall_inclusive=0.0, cpu_inclusive=0.0,
            wall_instrumented_child_exclusive=0.0, cpu_instrumented_child_exclusive=0.0))
        m['count'] += 1
        m['returned'] += int(returned)
        m['exceptions'] += int(not returned)
        m['wall_inclusive'] += elapsed
        m['cpu_inclusive'] += cpu
        m['wall_instrumented_child_exclusive'] += elapsed - frame['child_wall']
        m['cpu_instrumented_child_exclusive'] += cpu - frame['child_cpu']

    def wrapper(self, original, label, *, byte_return=False, hash_input=False, only_nested=False):
        self.report['labels'].append(label)
        @functools.wraps(original)
        def call(*args, **kwargs):
            stack = self.stack()
            if only_nested and not stack:
                return original(*args, **kwargs)
            phase = self.phase()
            parent = stack[-1] if stack else None
            frame = dict(label=label, child_wall=0.0, child_cpu=0.0)
            stack.append(frame)
            returned, did_return = None, False
            started, cpu = time.monotonic(), time.thread_time()
            try:
                returned = original(*args, **kwargs)
                did_return = True
                return returned
            finally:
                elapsed, elapsed_cpu = time.monotonic() - started, time.thread_time() - cpu
                try:
                    stack.pop()
                    if parent is not None:
                        parent['child_wall'] += elapsed
                        parent['child_cpu'] += elapsed_cpu
                    self.add_metric(self.report['metrics'], label, elapsed, elapsed_cpu, frame, did_return)
                    self.add_metric(self.report['metrics_by_phase'], phase + '::' + label,
                                    elapsed, elapsed_cpu, frame, did_return)
                    if byte_return and did_return:
                        m = self.report['returned_bytes'].setdefault(phase + '::' + label,
                            dict(calls=0, bytes=0, non_bytes=0))
                        m['calls'] += 1
                        if type(returned) is bytes:
                            m['bytes'] += len(returned)  # Do not copy, serialize or hash.
                        else:
                            m['non_bytes'] += 1
                    if hash_input:
                        data = args[0] if args else kwargs.get('string', kwargs.get('data', b''))
                        category = next((f['label'] for f in reversed(stack) if f['label'] in {
                            'CGR.input_key', 'validator', 'model_inputs', 'codec.inputs'}), 'other_product')
                        key = phase + '::' + category
                        m = self.report['hash_inputs'].setdefault(key, dict(
                            calls=0, bytes=0, unknown_buffer_calls=0,
                            wall_inclusive=0.0, cpu_inclusive=0.0,
                            wall_instrumented_child_exclusive=0.0, cpu_instrumented_child_exclusive=0.0))
                        m['calls'] += 1
                        m['wall_inclusive'] += elapsed
                        m['cpu_inclusive'] += elapsed_cpu
                        m['wall_instrumented_child_exclusive'] += elapsed - frame['child_wall']
                        m['cpu_instrumented_child_exclusive'] += elapsed_cpu - frame['child_cpu']
                        if type(data) in (bytes, bytearray):
                            m['bytes'] += len(data)
                        elif type(data) is memoryview:
                            m['bytes'] += data.nbytes
                        else:
                            m['unknown_buffer_calls'] += 1
                except BaseException as failure:
                    # Observation must not mask the original callee exception or
                    # replace its successful return. Report metric faults alone.
                    try:
                        self.report['secondary_errors'].append(dict(
                            label=label, error_type=type(failure).__name__, error=str(failure)))
                    except BaseException:
                        pass
        return call

    def install(self, target, name, replace, label, **options):
        replace(target, name, self.wrapper(getattr(target, name), label, **options))


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def value(obj):
    if isinstance(obj, bytes):
        return {'bytes_hex': obj.hex()}
    if isinstance(obj, Mapping):
        return {str(k): value(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [value(v) for v in obj]
    if callable(getattr(obj, 'model_dump', None)):
        return value(obj.model_dump())
    if type(obj) not in (str, int, float, bool, type(None)):
        return {'diagnostic_type': type(obj).__name__, 'diagnostic_repr': repr(obj)}
    return obj


def encoded(obj):
    return json.dumps(value(obj), ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def dump(path, obj):
    path.write_text(json.dumps(value(obj), ensure_ascii=False, sort_keys=True,
                               indent=2) + '\n', encoding='utf-8')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run_git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def source_lock(repo):
    files = list((repo / 'src' / 'sim2act').rglob('*.py'))
    files += [p for p in (repo / 'schemas').rglob('*') if p.is_file()]
    files += [repo / 'pyproject.toml', repo / 'tests/test_cold_binding_graph_integration.py']
    require(all(p.is_file() for p in files), 'Source lock input missing')
    hashes = {str(p.relative_to(repo)): sha(p) for p in sorted(set(files))}
    return {'head': run_git(repo, 'rev-parse', 'HEAD'), 'files': hashes,
            'files_fingerprint': hashlib.sha256(encoded(hashes).encode()).hexdigest(),
            'script_sha256': sha(Path(__file__).resolve())}


def verify_lock(repo, expected):
    actual = source_lock(repo)
    require(actual == expected, 'Current source/script differs from frozen source lock')
    return actual


@contextlib.contextmanager
def ro(db):
    c = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True, timeout=1)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    try:
        yield c
    finally:
        c.close()


def snapshot(db):
    with ro(db) as c:
        schema = [dict(r) for r in c.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
        tables = [r['name'] for r in schema if r['type'] == 'table']
        rows = {}
        for name in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            rows[name] = sorted((dict(r) for r in c.execute('SELECT * FROM ' + quoted)), key=encoded)
        return {'schema': schema, 'tables': rows}


def compact(db):
    with ro(db) as c:
        return {'runs': [dict(r) for r in c.execute(
                    'SELECT id,status,fence,worker_id,version FROM runs ORDER BY id')],
                'attempts': [dict(r) for r in c.execute(
                    'SELECT run_id,status,COUNT(*) AS n FROM attempts GROUP BY run_id,status ORDER BY run_id,status')],
                'counts': {name: c.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0]
                           for name in ('runs', 'attempts', 'events', 'internal_instance_data',
                                        'delivery_graph_requests', 'grants', 'reservations')}}


def proc_snapshot(pid):
    result = {}
    for name in ('status', 'stat', 'wchan'):
        try:
            result[name] = Path(f'/proc/{pid}/{name}').read_text()[:12000]
        except OSError as e:
            result[name] = {'error': str(e)}
    return result


def derive_pin(store, settings, out):
    """All identities and material/Goal/recipe values come from actual copied rows."""
    from sqlalchemy import select
    from sim2act import natural_live_admission as admission
    from sim2act.db import (attempts, delivery_graph_requests, goal_application_candidates,
                           goal_card_versions, internal_app_runs, internal_releases,
                           internal_run_bindings, projects, resources, runs)
    from sim2act.production_trial_admission import canonical_quota_subject
    from sim2act.spec_production import ProductionTrialBinding
    from sim2act.worker import Worker

    with store.tx() as c:
        bindings = [dict(r) for r in c.execute(select(internal_run_bindings)).mappings()]
        cold_bindings = [r for r in bindings if 'pb_use' in r['snapshot']]
        require(len(cold_bindings) == 1, 'Expected one preserved queued PB per-use binding')
        cb = cold_bindings[0]['snapshot']
        current = dict(c.execute(select(runs).where(runs.c.id == cb['run_id'])).mappings().one())
        require(current['status'] == 'QUEUED' and current['fence'] == 0
                and current['worker_id'] is None, 'Cold has already been processed')
        cold_release = dict(c.execute(select(internal_releases).where(
            internal_releases.c.id == cb['release_id'])).mappings().one())
        cold_draft = cold_release['snapshot']['draft']
        extraction_rows = [dict(r) for r in c.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == cold_draft['id'],
            delivery_graph_requests.c.kind == 'pb_natural_spec_extract')).mappings()]
        require(len(extraction_rows) == 1, 'Expected exact preserved extraction receipt')
        extraction = extraction_rows[0]['snapshot']['request']['review']
        source_id = cold_draft['candidate']['spec_task']['source_run_id']
        require(extraction['source_run_id'] == source_id, 'Extraction/source identity mismatch')
        source_job = dict(c.execute(select(runs).where(runs.c.id == source_id)).mappings().one())
        source_binding = next(r['snapshot'] for r in bindings if r['run_id'] == source_id)
        source_release = dict(c.execute(select(internal_releases).where(
            internal_releases.c.id == source_binding['release_id'])).mappings().one())
        source_draft = source_release['snapshot']['draft']
        marker = dict(c.execute(select(goal_application_candidates).where(
            goal_application_candidates.c.app_id == source_draft['id'])).mappings().one())
        generation = dict(c.execute(select(runs).where(runs.c.id == marker['run_id'])).mappings().one())
        source_app_run = dict(c.execute(select(internal_app_runs).where(
            internal_app_runs.c.id == source_binding['app_run_id'])).mappings().one())
        project = dict(c.execute(select(projects).where(projects.c.id == current['project_id'])).mappings().one())
        attempt_rows = [dict(r) for r in c.execute(select(attempts)).mappings()]
        ga_rows = [r for r in attempt_rows if r['run_id'] == generation['id']]
        src_rows = [r for r in attempt_rows if r['run_id'] == source_id]
        require(len(ga_rows) == 3 and all(r['status'] == 'RECEIVED' for r in ga_rows), 'Preserved G3 facts changed')
        require(source_job['status'] == 'SUCCEEDED' and len(src_rows) == 2
                and all(r['status'] == 'VERIFIED' for r in src_rows), 'Preserved Source2 facts changed')
        require(not any(r['run_id'] == current['id'] for r in attempt_rows), 'Cold already has Attempt')
        require(len(attempt_rows) == 5, 'Unexpected additional attempts in preserved prefix')

        def material_goal(saved):
            row = dict(c.execute(select(goal_card_versions).where(
                goal_card_versions.c.card_id == saved['card_id'],
                goal_card_versions.c.version == saved['version'])).mappings().one())
            require(row['fingerprint'] == saved['fingerprint'] and row['snapshot'] == saved['snapshot'],
                    'Frozen Goal and actual version differ')
            resource_id, = row['snapshot']['content']['resource_refs']
            resource = dict(c.execute(select(resources).where(resources.c.id == resource_id)).mappings().one())
            require(resource['format'] == 'txt' and resource['project_id'] == current['project_id'],
                    'Preserved synthetic material format/project changed')
            require(sha256_text(resource['content']) == resource['hash'], 'Material bytes/hash changed')
            return dict(resource_id=resource_id, content=resource['content'], source_hash=resource['hash'],
                        card_id=row['card_id'], goal_version=row['version'],
                        goal_fingerprint=row['fingerprint'], goal_snapshot=row['snapshot'])

        materials = [material_goal(source_binding['spec_goal']), material_goal(cb['spec_goal'])]
        cold_review = cb['pb_use']['review']
        require(materials[1]['resource_id'] == cold_review['resource_id'], 'Cold material mismatch')
        keys = dict(generate=generation['request_key'], source=source_app_run['request_key'],
                    cold=cold_review['request_key'])
        require(keys == dict(generate='natural-generation', source='spec-actual', cold='plain-cold-graph-queue'),
                'This script accepts only the identified current-environment fixture')
        trial = admission.PBTrialContract(
            trial_key='synthetic-first-binding-pin', project_id=current['project_id'],
            principal_id=current['principal_id'], runtime_id=project['runtime_id'],
            quota_subject=canonical_quota_subject('synthetic-first-binding-account'),
            software_fingerprint='b' * 64, authorization_fingerprint='c' * 64,
            bindings=materials, stage_keys=keys, expires_at=time.time() + 3600, path='P-B',
            extraction_request_key=extraction['request_key'], extraction_recipe=extraction['recipe'])
        pin = ProductionTrialBinding(trial, 'synthetic-unapproved-read-pin', 'synthetic-first-binding-account')
        facts = dict(scope=SCOPE, generation_run=generation, source_run=source_job, cold_run=current,
                     source_release_id=source_release['id'], cold_release_id=cold_release['id'],
                     source_app_id=source_draft['id'], cold_app_id=cold_draft['id'],
                     source_instance_id=source_binding['instance_id'], cold_instance_id=cb['instance_id'],
                     generation_attempt_ids=[r['id'] for r in ga_rows], generation_attempts=ga_rows,
                     source_attempt_ids=[r['id'] for r in src_rows], materials=materials, stage_keys=keys,
                     extraction_review=extraction, read_pin=trial.model_dump(),
                     approval_key=pin.approval_key,
                     note='Fake software/authorization fingerprints and unapproved key are continuity pins only.')
        dump(out / 'existing-prefix-and-synthetic-read-pin.json', facts)

    worker = object.__new__(Worker)  # Deliberately bypass Worker initialization/claim loop.
    worker.store, worker.s, worker.pa_trial = store, settings, pin
    worker.id = 'synthetic-first-binding-reader'
    worker.stop = threading.Event()
    worker.goal_planner_transport = None
    worker._journal_trial_store = store
    worker._journal_trial_binding = pin
    worker._journal_trial_drift = False
    return worker, current, facts


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def child(args):
    repo, out, db = Path(args.repo).resolve(), Path(args.out).resolve(), Path(args.db).resolve()
    expected = json.loads(Path(args.manifest).read_text())
    verify_lock(repo, expected)
    require(out in db.parents and db.name == 'prefix-copy.db', 'Child can only open its own DB copy')
    sys.path.insert(0, str(repo / 'src'))
    import httpx
    from sqlalchemy import event
    from sim2act import app_jobs, apps, lifecycle, text_apps
    from sim2act import goal_applications as ga
    from sim2act import natural_live_admission as admission
    from sim2act import natural_spec_runtime as runtime
    from sim2act import natural_trial_budget as old_budget
    from sim2act import pa_spec_apps as spec
    from sim2act import pa_trial_dispatch as dispatch
    from sim2act import pb_natural_specs as pb
    from sim2act import pb_natural_uses as use
    from sim2act import production_trial_journal as journal
    from sim2act import spec_production
    from sim2act.config import Settings
    from sim2act.contracts import Limits
    from sim2act.db import Store
    from sim2act.model import InternModel
    from sim2act.worker import Worker

    require(Path(runtime.__file__).resolve() == repo / 'src/sim2act/natural_spec_runtime.py',
            'Imported runtime is not current frozen source')
    state = dict(phase='setup', counters={}, stage_stack=[], blocked=[], sql_count=0)
    log = (out / 'child-events.jsonl').open('a', buffering=1, encoding='utf-8')
    stacks = (out / 'child-stacks.txt').open('a', buffering=1, encoding='utf-8')
    faulthandler.enable(file=stacks, all_threads=True)
    faulthandler.dump_traceback_later(args.interval, repeat=True, file=stacks)
    if hasattr(signal, 'SIGUSR1'):
        faulthandler.register(signal.SIGUSR1, file=stacks, all_threads=True)
    start = time.monotonic()
    def emit(kind, **data):
        # Build the mapping without duplicate keyword expansion. Payload fields
        # never replace the observer's own event identity/elapsed clock.
        record = dict(kind=kind, wall=time.monotonic() - start)
        for key, item in data.items():
            record['payload_' + key if key in record else key] = item
        log.write(encoded(record) + '\n')
    secondary_errors = []
    def recording_failure(where, failure, primary):
        item = dict(where=where, error_type=type(failure).__name__, error=str(failure),
                    primary_type=type(primary).__name__ if primary is not None else None)
        secondary_errors.append(item)
        try:
            sys.stderr.write('SECONDARY_DIAGNOSTIC_RECORDING_FAILURE ' + encoded(item) + '\n')
            sys.stderr.flush()
        except BaseException:
            pass
    phases = []
    @contextlib.contextmanager
    def phase(name):
        state['phase'] = name
        wall, cpu, sql = time.monotonic(), time.thread_time(), state['sql_count']
        counters = dict(state['counters'])
        emit('phase-begin', phase=name)
        dump(out / 'phase-current.json', dict(phase=name, status='ENTERED',
             wall=wall - start, sql_count=sql, counters=counters))
        primary = None
        try:
            yield
        except BaseException as exc:
            primary = exc
            raise
        finally:
            try:
                item = dict(phase=name, phase_elapsed_wall=time.monotonic() - wall,
                            phase_elapsed_thread_cpu=time.thread_time() - cpu,
                            sql_count=state['sql_count'] - sql,
                            counters={k: v - counters.get(k, 0) for k, v in state['counters'].items()},
                            status='EXCEPTION' if primary is not None else 'RETURNED')
                phases.append(item)
                emit('phase-end', **item)
                dump(out / 'phase-timings.json', phases)
            except BaseException as failure:
                recording_failure('phase-finally:' + name, failure, primary)
                if primary is None:
                    raise
    done = threading.Event()
    def observer():
        while not done.wait(args.interval):
            emit('periodic', phase=state['phase'], stage_stack=list(state['stage_stack']),
                 counters=dict(state['counters']), sql_count=state['sql_count'],
                 last_sql=state.get('last_sql'), process_cpu=time.process_time(),
                 process=proc_snapshot(os.getpid()))
    thread = threading.Thread(target=observer, name='diagnostic-observer', daemon=True)
    thread.start()
    store = Store('sqlite:///' + str(db), test_only=True)
    settings = Settings('sqlite:///' + str(db), out, mode='mock')
    full = Limits(**{k: getattr(settings, k) for k in Limits.model_fields})
    changed = []
    metrics = {}
    codec_cost_tap = PassiveCodecCostTap(lambda: state['phase'])
    before = snapshot(db)
    before_sha = sha(db)
    dump(out / 'database-before.json', before)
    dump(out / 'checkpoint-initial.json', dict(scope=SCOPE, phase='before-pin-and-producer',
         source_lock=expected, database_sha256=before_sha, database=compact(db),
         settings_limits=full.model_dump(), facets=args.facets,
         public_bound_oracle_requested=args.public_oracle))
    emit('initial-checkpoint-persisted', file='checkpoint-initial.json',
         public_bound_oracle_requested=args.public_oracle)
    require(not any(r['kind'].startswith((journal.KIND, old_budget.KIND))
                    for r in before['tables']['delivery_graph_requests']), 'Unexpected trial authority rows')

    def forbidden(label):
        def fail(*a, **kw):
            primary = AssertionError('Forbidden ancestor/execution/authority call: ' + label)
            state['blocked'].append(label)
            try:
                emit('TRIPWIRE', label=label)
            except BaseException as failure:
                recording_failure('tripwire:' + label, failure, primary)
            raise primary
        return fail
    def replace(target, name, method):
        require(hasattr(target, name), f'Tripwire/stage target disappeared: {target}.{name}')
        changed.append((target, name, getattr(target, name)))
        setattr(target, name, method)
    def block(target, names):
        for name in names:
            replace(target, name, forbidden(getattr(target, '__name__', type(target).__name__) + '.' + name))
    def measured(target, name, events=True):
        original = getattr(target, name)
        label = target.__name__ + '.' + name
        @functools.wraps(original)
        def call(*a, **kw):
            begin, cpu = time.monotonic(), time.thread_time()
            state['counters'][label] = state['counters'].get(label, 0) + 1
            if events:
                state['stage_stack'].append(label)
                emit('stage-begin', stage=label)
            primary = None
            try:
                return original(*a, **kw)
            except BaseException as exc:
                primary = exc
                raise
            finally:
                try:
                    m = metrics.setdefault(label, dict(count=0, wall=0.0, thread_cpu=0.0))
                    m['count'] += 1
                    m['wall'] += time.monotonic() - begin
                    m['thread_cpu'] += time.thread_time() - cpu
                    if events:
                        try:
                            emit('stage-end', stage=label, metric=m)
                        finally:
                            state['stage_stack'].pop()
                except BaseException as failure:
                    recording_failure('stage-finally:' + label, failure, primary)
                    if primary is None:
                        raise
        replace(target, name, call)

    # Deny SQL writes independently of post-call equality. Transactions/read ACLs remain real.
    sql_file = (out / 'sql.jsonl').open('a', buffering=1, encoding='utf-8')
    def sql_before(conn, cursor, statement, parameters, context, executemany):
        op = statement.lstrip().split(None, 1)[0].upper()
        require(op == 'SELECT' or statement.strip().upper() == 'BEGIN IMMEDIATE',
                'Diagnostic attempted non-read SQL: ' + statement[:160])
        state['sql_count'] += 1
        state['last_sql'] = statement[:3000]
        sql_file.write(encoded(dict(wall=time.monotonic() - start, statement=statement,
                                    parameters=parameters, executemany=executemany)) + '\n')
    event.listen(store.engine, 'before_cursor_execute', sql_before)
    result = dict(scope=SCOPE, outcome='INCOMPLETE', source_lock=expected,
                  facets=args.facets, public_bound_oracle_requested=args.public_oracle,
                  settings_limits=full.model_dump(), diagnostic_timeout_does_not_change_limits=True,
                  codec_cost_tap=codec_cost_tap.report)
    error = None
    try:
        state['phase'] = 'derive-synthetic-read-pin-from-existing-rows'
        emit('derive-pin-begin')
        worker, current, facts = derive_pin(store, settings, out)
        emit('derive-pin-end')
        block(Worker, ('once', 'process', 'reserve', 'finish', 'checkpoint', '_heartbeat_lease'))
        block(Store, ('claim',))
        block(InternModel, ('request', 'request_serialized', 'request_serialized_captured', '_request_serialized'))
        for target, names in [
            (admission, ('approve', 'approve_stage', '_approved', 'admit')),
            (spec_production, ('source', 'receive_source')),
            (journal, ('read', 'reserve', 'record_attempt', 'settle', '_apply_in_transaction')),
            (dispatch, ('_admission', '_account', 'preflight', 'reserved', 'request_captured',
                        'settle_verified', 'check_commit', 'check_journal_claim')),
        ]:
            block(target, names)
        for target, name in [(httpx.Client, 'send'), (httpx.AsyncClient, 'send'),
                             (httpx.HTTPTransport, 'handle_request'),
                             (httpx.AsyncHTTPTransport, 'handle_async_request'),
                             (httpx.MockTransport, 'handle_request'),
                             (httpx.MockTransport, 'handle_async_request')]:
            block(target, (name,))
        # Optional public bound is an expected-output oracle only; it never enters
        # a private fact producer as input. Keep execution/authority/SQL barriers
        # installed even here; install full-ancestor tripwires immediately after.
        public_hashes = {}
        if args.public_oracle:
            from sqlalchemy import select
            from sim2act.db import runs
            with phase('optional-public-bound-oracles'), store.tx() as c, pb._source_reads(store, c):
                fresh = dict(c.execute(select(runs).where(runs.c.id == current['id'])).mappings().one())
                for role, limits in (('platform', full), ('trial', admission._limits(worker.pa_trial.contract))):
                    with phase('optional-public-bound-' + role):
                        oracle = spec.bound(store, c, fresh['principal_id'], fresh, limits)
                        dump(out / ('public-bound-' + role + '.json'), oracle)
                        public_hashes[role] = hashlib.sha256(encoded(oracle).encode()).hexdigest()
                        del oracle
            require(snapshot(db) == before, 'Optional public bound oracle changed the DB')
            dump(out / 'public-bound-expected-hashes.json', public_hashes)
        # Exact same full-ancestor tripwires as the integration test. Never replace
        # a protected ancestor with a fabricated successful value.
        for target, names in [
            (ga, ('source', 'initial_messages', 'history', '_history', 'verified_candidate', '_verified_candidate', 'parse_candidate')),
            (spec, ('bound', '_bound', 'verify_job', 'receipts', 'verify_origin', 'model_source', 'audit_fingerprint', 'from_response')),
            (pb, ('source', '_source', 'source_audit', '_source_audit', 'review', 'verify', 'audit_fingerprint')),
            (use, ('bound', 'review', 'audit')),
            (apps, ('validate_frozen_candidate',)), (lifecycle, ('read_release', '_read_release')),
            (app_jobs, ('load_binding',)), (text_apps, ('verify_origin',)),
        ]:
            block(target, names)
        for target, names in [
            (runtime, ('_cold_first_binding', '_cold_run_facts', '_cold_binding_limits_facet', '_cold_audit_seed')),
            (app_jobs, ('_cold_binding_prefix', '_cold_binding_release_prefix')),
            (lifecycle, ('_cold_release_prefix', '_cold_release_complete')),
            (apps, ('_cold_candidate_prefix',)),
            (ga, ('_cold_generation_source', '_cold_history_from_source', '_cold_candidate_from_history')),
            (spec, ('_cold_original_origin_prefix', '_cold_original_origin_from_generation',
                    '_cold_bound_prefix', '_native_audit_facts', '_cold_receipts', '_cold_verify_job_from_receipts')),
            (pb, ('_cold_verify_prefix', '_cold_source_prefix', '_cold_source_typed',
                  '_cold_source_audit_from_original', '_cold_source_from_audit',
                  '_cold_review_from_source', '_cold_verify_from_review', '_cold_audit_from_source')),
            (use, ('_cold_bound_prefix', '_cold_review_prefix', '_cold_review_from_audit', '_cold_bound_from_review')),
        ]:
            for name in names:
                measured(target, name)
        measured(runtime._ColdGraphRead, 'check', events=False)
        measured(runtime._ColdGraphRead, 'input_key', events=False)
        measured(runtime, '_model_inputs', events=False)
        # Only narrow cost taps; no full/public/Mock observer installation.
        # Preserve the existing v3 wrappers and restore both layers in reverse.
        for target, name, label, returned_bytes in [
            (runtime._ColdGraphRead, 'check', 'CGR.check', False),
            (runtime._ColdGraphRead, 'input_key', 'CGR.input_key', False),
            (runtime._ColdGraphRead, 'input_bytes', 'CGR.input_bytes', True),
            (runtime, '_cold_graph_bytes', 'serializer', True),
            (runtime, '_cold_graph_validate_inputs', 'validator', False),
            (runtime, '_cold_graph_inputs', 'codec.inputs', False),
            (runtime, '_model_inputs', 'model_inputs', False),
        ]:
            codec_cost_tap.install(target, name, replace, label, byte_return=returned_bytes)
        codec_cost_tap.install(hashlib, 'sha256', replace, 'sha256_constructor',
                               hash_input=True, only_nested=True)
        emit('tripwires-installed', patched_functions=len(changed),
             note='All listed ancestor, Worker, transport and authority functions fail on invocation.')
        if args.facets:
            from sqlalchemy import select
            from sim2act.db import delivery_graph_requests, internal_releases, internal_run_bindings, runs

            def report_graph(label, graph, guard, driver):
                require(graph.guard is guard and guard.active, 'Graph lost its exact active guard')
                require(graph.binding['source']['resource_id'] == facts['materials'][1]['resource_id'], 'Cold material changed')
                require(graph.source_binding['source']['resource_id'] == facts['materials'][0]['resource_id'], 'Source material changed')
                require(graph.binding['release']['id'] == facts['cold_release_id'], 'Cold Release changed')
                require(graph.source_binding['snapshot']['run_id'] == facts['source_run']['id'], 'Source Run changed')
                require(graph.generation_history[1] == facts['generation_attempts'], 'Preserved G3 receipts changed')
                require(graph.native_audit['attempts'] == sorted(facts['generation_attempts'], key=lambda r: r['id']),
                        'Preserved native audit changed')
                require(driver.total_changes == 0, 'SQLite changes occurred')
                raw = dict(binding=graph.binding, source_binding=graph.source_binding,
                           source_outputs=graph.source_outputs, source_proved=graph.source_proved,
                           source_proof=graph.source_facts.proof,
                           source_typed=dict(graph.source_facts.typed.typed),
                           native_audit=graph.native_audit, source_audit=graph.source_audit.digest,
                           extraction_origin=graph.extraction_origin,
                           extraction_audit=graph.extraction_audit, use_value=graph.use_value,
                           generation_history=graph.generation_history,
                           generation_raw=graph.generation_raw)
                dump(out / (label + '-complete-raw.json'), raw)
                hashes = {name: hashlib.sha256(encoded(v).encode()).hexdigest() for name, v in raw.items()}
                dump(out / (label + '-hashes.json'), hashes)
                return hashes

            def current_rows(c):
                # No G0 DTO/reader/seed is supplied to G1. Re-select full original
                # rows under the new TX/source-read token, including the receipt
                # that supplies the caller's effective draft to the audit edge.
                fresh = dict(c.execute(select(runs).where(runs.c.id == facts['cold_run']['id'])).mappings().one())
                binding_row = dict(c.execute(select(internal_run_bindings).where(
                    internal_run_bindings.c.run_id == fresh['id'])).mappings().one())
                accepted = binding_row['snapshot']
                release = dict(c.execute(select(internal_releases).where(
                    internal_releases.c.id == accepted['release_id'])).mappings().one())
                saved = dict(c.execute(select(delivery_graph_requests).where(
                    delivery_graph_requests.c.app_id == accepted['instance_id'],
                    delivery_graph_requests.c.principal_id == fresh['principal_id'],
                    delivery_graph_requests.c.kind == use.PB.use,
                    delivery_graph_requests.c.request_key == accepted['pb_use']['review']['request_key'])).mappings().one())
                frozen = saved['snapshot']['response']
                reviewed = frozen['reviewed']
                draft = {**copy.deepcopy(release['snapshot']['draft']),
                         'candidate': copy.deepcopy(reviewed['effective_candidate']),
                         'fingerprint': reviewed['effective_fingerprint'], 'pb_use_run_id': fresh['id']}
                return fresh, draft, dict(run=fresh, binding=binding_row, release=release, receipt=saved,
                                         seed_draft=draft)

            role_hashes = {}
            with phase('G0-fresh-scope'), store.tx() as c, pb._source_reads(store, c):
                g0_token = c.info.get('pb_source_reads')
                g0_current = dict(c.execute(select(runs).where(runs.c.id == facts['cold_run']['id'])).mappings().one())
                trial_limits = admission._limits(worker.pa_trial.contract)
                roles = dict(source=full, generate=None, platform=full, trial=trial_limits, per_use=full)
                dump(out / 'G0-role-limits.json', {k: v.model_dump() if v is not None else None for k, v in roles.items()})
                with runtime._cold_graph_read(worker, c, dict(current=g0_current), roles, 'pre') as guard:
                    with phase('G0-first-binding-platform'):
                        graph = runtime._cold_first_binding(worker, c, guard, g0_current, full)
                    role_hashes['platform'] = report_graph('G0-platform', graph, guard, c.connection.driver_connection)
                    with phase('G0-trial-limits-facet'):
                        trial_graph = runtime._cold_binding_limits_facet(worker, c, graph, trial_limits, role='trial')
                    role_hashes['trial'] = report_graph('G0-trial', trial_graph, guard, c.connection.driver_connection)
                    for role, oracle_hash in public_hashes.items():
                        require(role_hashes[role]['binding'] == oracle_hash, 'G0 complete public bound mismatch: ' + role)
                require(not guard.active, 'G0 guard remained active')
            # Retain only primitive hashes/IDs for cross-epoch comparison. None of
            # these complete objects may become a G1 producer/seed input.
            del graph, trial_graph, guard, roles, g0_current, trial_limits
            dump(out / 'G0-expected-comparison-hashes-only.json', role_hashes)
            require(snapshot(db) == before, 'G0 changed DB before G1')

            with phase('G1-fresh-scope'), store.tx() as c, pb._source_reads(store, c):
                require(c.info.get('pb_source_reads') is not g0_token, 'G1 reused G0 source-read token')
                with phase('G1-actual-full-row-inputs'):
                    g1_current, g1_draft, g1_rows = current_rows(c)
                    dump(out / 'G1-actual-full-row-inputs.json', g1_rows)
                trial_limits = admission._limits(worker.pa_trial.contract)
                roles = dict(source=trial_limits, generate=None, platform=full,
                             trial=trial_limits, per_use=trial_limits)
                dump(out / 'G1-role-limits.json', {k: v.model_dump() if v is not None else None for k, v in roles.items()})
                with runtime._cold_graph_read(worker, c, dict(current=g1_current), roles, 'post') as guard:
                    with phase('G1-audit-seed-from-this-epoch-raw-rows'):
                        seed = runtime._cold_audit_seed(worker, c, guard, g1_draft)
                    dump(out / 'G1-audit-seed-complete-fields.json', seed.fields())
                    with phase('G1-first-binding-trial-with-local-seed'):
                        graph = runtime._cold_first_binding(worker, c, guard, g1_current, trial_limits, audit_seed=seed)
                    g1_trial_hashes = report_graph('G1-trial', graph, guard, c.connection.driver_connection)
                    require(g1_trial_hashes == role_hashes['trial'], 'G1 trial complete raw facts differ from G0 trial')
                    with phase('G1-platform-limits-facet'):
                        platform_graph = runtime._cold_binding_limits_facet(worker, c, graph, full, role='platform')
                    g1_platform_hashes = report_graph('G1-platform', platform_graph, guard, c.connection.driver_connection)
                    require(g1_platform_hashes == role_hashes['platform'], 'G1 platform complete raw facts differ from G0 platform')
                    for role, oracle_hash in public_hashes.items():
                        hashes = g1_trial_hashes if role == 'trial' else g1_platform_hashes
                        require(hashes['binding'] == oracle_hash, 'G1 complete public bound mismatch: ' + role)
                require(not guard.active, 'G1 guard remained active')
            require(not state['blocked'], 'A tripwire fired')
            result['outcome'] = 'PASS_READ_ONLY_PRODUCER'
            result['facet_raw_equalities'] = dict(G0_trial_equals_G1_trial=True, G0_platform_equals_G1_platform=True)
        else:
            state['phase'] = 'first-binding'
            with store.tx() as c, pb._source_reads(store, c):
                driver = c.connection.driver_connection
                changes = driver.total_changes
                roles = dict(source=full.model_copy(deep=True), generate=None, platform=full,
                             trial=full.model_copy(deep=True), per_use=full.model_copy(deep=True))
                with runtime._cold_graph_read(worker, c, dict(current=current), roles, 'pre') as guard:
                    graph = runtime._cold_first_binding(worker, c, guard, current, full)
                    require(graph.guard is guard and guard.active, 'Returned graph lost active exact guard')
                    require(graph.binding['source']['resource_id'] == facts['materials'][1]['resource_id'],
                            'Cold material identity changed')
                    require(graph.source_binding['source']['resource_id'] == facts['materials'][0]['resource_id'],
                            'Source material identity changed')
                    require(graph.binding['release']['id'] == facts['cold_release_id'], 'Cold Release changed')
                    require(graph.source_binding['snapshot']['run_id'] == facts['source_run']['id'], 'Source Run changed')
                    require(len(graph.generation_history[1]) == 3
                            and graph.generation_history[1] == facts['generation_attempts'],
                            'Graph changed preserved G3 receipts')
                    require(graph.native_audit['attempts'] == sorted(facts['generation_attempts'], key=lambda row: row['id']),
                            'Graph changed preserved original native audit')
                    require(driver.total_changes == changes == 0, 'SQLite change counter advanced')
                    dump(out / 'graph-summary.json', dict(
                        scope=SCOPE, cold_binding=graph.binding, source_binding=graph.source_binding,
                        source_outputs=graph.source_outputs, source_proved=graph.source_proved,
                        native_audit=graph.native_audit, source_proof=graph.source_facts.proof,
                        source_audit_digest=graph.source_audit.digest,
                        extraction_audit=graph.extraction_audit,
                        generation_history_attempt_count=len(graph.generation_history[1]),
                        active_guard_at_return=guard.active, sqlite_total_changes=driver.total_changes))
                require(not guard.active, 'Graph scope stayed active after exit')
            require(not state['blocked'], 'A tripwire fired')
            result['outcome'] = 'PASS_READ_ONLY_PRODUCER'
    except BaseException as exc:
        error = exc
        result.update(outcome='FAIL', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        try:
            emit('exception', **{k: result[k] for k in ('error_type', 'error', 'traceback')})
        except BaseException as failure:
            recording_failure('primary-exception-recording', failure, error)
    finally:
        try:
            state['phase'] = 'final-snapshot'
            for target, name, original in reversed(changed):
                setattr(target, name, original)
            event.remove(store.engine, 'before_cursor_execute', sql_before)
            store.engine.dispose()
            after = snapshot(db)
            dump(out / 'database-after.json', after)
            result.update(database_unchanged=(before == after), db_before_sha256=before_sha,
                          db_after_sha256=sha(db), metrics=metrics, blocked=state['blocked'],
                          sql_count=state['sql_count'], elapsed=time.monotonic() - start, phases=phases,
                          secondary_recording_errors=secondary_errors,
                          existing_prefix_after=compact(db))
            try:
                verify_lock(repo, expected)
                result['source_unchanged'] = True
            except BaseException as exc:
                result.update(source_unchanged=False, source_drift_error=str(exc), outcome='FAIL')
            if before != after:
                result['outcome'] = 'FAIL_DB_CHANGED'
            dump(out / 'result.json', result)
            done.set()
            thread.join(timeout=2)
            faulthandler.cancel_dump_traceback_later()
            stacks.close()
            sql_file.close()
            log.close()
        except BaseException as failure:
            recording_failure('child-finalization', failure, error)
            if error is None:
                raise
            # Preserve the original producer/harness exception as primary even
            # when a snapshot, evidence write, restoration or cleanup also fails.
            result['secondary_recording_errors'] = secondary_errors
            try:
                dump(out / 'result-fallback-primary-exception.json', result)
            except BaseException as further:
                recording_failure('fallback-primary-exception-file', further, error)
            done.set()
            faulthandler.cancel_dump_traceback_later()
            for handle in (stacks, sql_file, log):
                try:
                    handle.close()
                except BaseException:
                    pass
    if error is not None:
        raise error
    require(result['outcome'] == 'PASS_READ_ONLY_PRODUCER', result['outcome'])


def parent(args):
    repo = Path(args.repo).resolve()
    if args.capture_manifest:
        target = Path(args.capture_manifest).resolve()
        require(not target.exists(), 'Refusing to overwrite source lock')
        target.parent.mkdir(parents=True, exist_ok=True)
        dump(target, source_lock(repo))
        print('Captured source lock only; no target import, DB copy or producer execution:', target)
        return
    require(args.manifest and args.out, '--manifest and --out required for diagnostic execution')
    require(not args.public_oracle or args.facets, '--public-oracle requires explicit --facets')
    source, out = Path(args.source_db).resolve(), Path(args.out).resolve()
    manifest_path = Path(args.manifest).resolve()
    expected = json.loads(manifest_path.read_text())
    verify_lock(repo, expected)
    require(source == DEFAULT_DB.resolve(), 'Only the authorized current-environment DB is accepted')
    require(source.is_file() and not out.exists(), 'Source missing or output directory already exists')
    require(not (repo == out or repo in out.parents), 'Evidence must stay outside the repository')
    require(15 <= args.interval <= 120, 'Observer interval must be at least 15s and bounded')
    require(30 <= args.timeout <= 1800, 'Each child must have bounded 30..1800s timeout')
    require(1 <= args.repeat <= 5, 'Explicit bounded repetition count required (1..5)')
    for suffix in ('-wal', '-journal'):
        side = Path(str(source) + suffix)
        require(not side.exists() or side.stat().st_size == 0,
                'Source has a nonempty SQLite sidecar; refusing incomplete byte copy: ' + str(side))
    source_sha = sha(source)
    source_before = snapshot(source)
    out.mkdir(parents=True)
    dump(out / 'source-lock.json', expected)
    dump(out / 'source-database-before.json', source_before)
    dump(out / 'invocation.json', dict(scope=SCOPE, argv=sys.argv, source_db=str(source),
         source_db_sha256=source_sha, python=sys.executable, timeout=args.timeout,
         repeat=args.repeat, interval=args.interval, source_lock=expected,
         facets=args.facets, public_bound_oracle_requested=args.public_oracle,
         no_budget_lease_or_guard_override=True))
    statuses = []
    for index in range(1, args.repeat + 1):
        verify_lock(repo, expected)
        require(sha(source) == source_sha, 'Source DB changed before repetition')
        folder = out / f'repeat-{index:02d}'
        folder.mkdir()
        db = folder / 'prefix-copy.db'
        shutil.copyfile(source, db)
        require(sha(db) == source_sha, 'DB copy differs from preserved source')
        command = [sys.executable, str(Path(__file__).resolve()), '--child', '--repo', str(repo),
                   '--manifest', str(manifest_path), '--out', str(folder), '--db', str(db),
                   '--interval', str(args.interval)]
        if args.facets:
            command.append('--facets')
        if args.public_oracle:
            command.append('--public-oracle')
        dump(folder / 'command.json', command)
        started = time.monotonic()
        timed_out = False
        with (folder / 'stdout.log').open('wb') as stdout, (folder / 'stderr.log').open('wb') as stderr, \
                (folder / 'parent-observations.jsonl').open('a', buffering=1) as observations:
            env = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1')
            # No configuration/credential environment is consumed by Settings(...).
            p = subprocess.Popen(command, stdout=stdout, stderr=stderr, env=env, start_new_session=True)
            while p.poll() is None:
                remaining = args.timeout - (time.monotonic() - started)
                if remaining <= 0:
                    timed_out = True
                    if hasattr(signal, 'SIGUSR1'):
                        p.send_signal(signal.SIGUSR1)
                    try:
                        p.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        p.terminate()
                    try:
                        p.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait(timeout=5)
                    break
                try:
                    p.wait(timeout=min(args.interval, remaining))
                except subprocess.TimeoutExpired:
                    item = dict(wall=time.monotonic() - started, pid=p.pid, process=proc_snapshot(p.pid))
                    try:
                        item['database'] = compact(db)
                    except BaseException as exc:
                        item['database_observation_error'] = repr(exc)
                    observations.write(encoded(item) + '\n')
            after = snapshot(db)
            dump(folder / 'parent-database-after.json', after)
            status = dict(index=index, exit_code=p.returncode, timed_out=timed_out,
                          wall=time.monotonic() - started, database_unchanged=(after == source_before),
                          db_sha256=sha(db), child_result_exists=(folder / 'result.json').is_file())
            if status['child_result_exists']:
                status['child_outcome'] = json.loads((folder / 'result.json').read_text())['outcome']
            dump(folder / 'parent-result.json', status)
            statuses.append(status)
        if timed_out or p.returncode != 0 or not status['database_unchanged']:
            break  # No automatic retry; preserve the first failure/timeout.
    source_after = snapshot(source)
    dump(out / 'source-database-after.json', source_after)
    summary = dict(scope=SCOPE, repeats=statuses, source_db_unchanged=(source_after == source_before),
                   source_db_bytes_unchanged=(sha(source) == source_sha), source_lock=expected)
    verify_lock(repo, expected)
    summary['source_code_unchanged'] = True
    summary['outcome'] = 'PASS_READ_ONLY_REUSE' if (
        len(statuses) == args.repeat and summary['source_db_unchanged']
        and summary['source_db_bytes_unchanged'] and all(
            r['exit_code'] == 0 and not r['timed_out'] and r['database_unchanged']
            and r.get('child_outcome') == 'PASS_READ_ONLY_PRODUCER' for r in statuses)) else 'FAIL_OR_TIMEOUT'
    dump(out / 'summary.json', summary)
    print(json.dumps(dict(outcome=summary['outcome'], evidence=str(out), scope=SCOPE), ensure_ascii=False))
    require(summary['outcome'] == 'PASS_READ_ONLY_REUSE', 'See preserved raw evidence')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default='/workspace/Sim2Act')
    p.add_argument('--source-db', default=str(DEFAULT_DB))
    p.add_argument('--capture-manifest')
    p.add_argument('--manifest')
    p.add_argument('--out')
    p.add_argument('--repeat', type=int, default=1)
    p.add_argument('--timeout', type=float, default=300)
    p.add_argument('--interval', type=float, default=15)
    p.add_argument('--facets', action='store_true', help='G0 platform->trial facet, then fresh G1 audit-seed/trial->platform facet')
    p.add_argument('--public-oracle', action='store_true', help='Explicitly compute public bound expected values before ancestor barriers')
    p.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--db', help=argparse.SUPPRESS)
    args = p.parse_args()
    child(args) if args.child else parent(args)


if __name__ == '__main__':
    main()

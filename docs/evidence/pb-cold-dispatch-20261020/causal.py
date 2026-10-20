"""Two bounded dormant readers; no Worker execution, models or PB acceptance."""
import argparse
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act')
BASE = 'f7e0d0b9922fedbb5730b4142d22d47a7c488171'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sources():
    paths = sorted((REPO / 'src').rglob('*.py'))
    return {str(p.relative_to(REPO)): sha(p) for p in paths}


def child(arm, epoch):
    import httpx
    from sqlalchemy import event
    from sim2act import natural_live_admission as admission
    from sim2act import natural_spec_runtime as runtime
    from sim2act import pa_trial_dispatch as dispatch
    from sim2act import pb_natural_specs as pb
    from sim2act import production_trial_journal as journal
    from sim2act import spec_production
    from sim2act.config import Settings
    from sim2act.contracts import Limits
    from sim2act.db import Store
    from sim2act.model import InternModel
    from sim2act.worker import Worker

    out = ROOT / arm
    db = out / 'prefix.db'
    record = dict(arm=arm, baseline=BASE, scope='DORMANT_FIRST_BINDING_SYNTHETIC_READ_PIN_ONLY',
                  source_before=sources(), db_before=sha(db), producer_calls=0,
                  counts={}, sql_counts={}, blocked=[])
    if arm == 'baseline':
        # Only the three reviewed functions differ. No old modules/instances run.
        for module in (runtime, admission):
            path = ROOT / (module.__name__.split('.')[-1] + '-baseline.py')
            exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
    real_clock = time.time

    def block(target, name):
        def denied(*args, **kwargs):
            record['blocked'].append(target.__name__ + '.' + name)
            raise AssertionError('Forbidden execution path: ' + target.__name__ + '.' + name)
        setattr(target, name, denied)

    for target, names in [
        (Worker, ('__init__', 'once', 'process', 'reserve', 'finish', 'checkpoint', '_heartbeat_lease')),
        (Store, ('claim',)),
        (InternModel, ('request', 'request_serialized', 'request_serialized_captured', '_request_serialized')),
        (admission, ('approve', 'approve_stage', '_approved', 'admit')),
        (spec_production, ('source', 'receive_source')),
        (journal, ('read', 'reserve', 'record_attempt', 'settle', '_apply_in_transaction')),
        (dispatch, ('_admission', '_account', 'preflight', 'reserved', 'request_captured',
                    'settle_verified', 'check_commit', 'check_journal_claim')),
        (httpx.Client, ('send',)), (httpx.AsyncClient, ('send',)),
        (httpx.HTTPTransport, ('handle_request',)),
        (httpx.AsyncHTTPTransport, ('handle_async_request',)),
        (httpx.MockTransport, ('handle_request', 'handle_async_request')),
    ]:
        for name in names:
            block(target, name)
    spec = importlib.util.spec_from_file_location('sealed_read_pin_helper', ROOT / 'read_pin_helper.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    saved_helper_clock = helper.time
    helper.time = SimpleNamespace(time=lambda: epoch)
    url = 'sqlite:///' + str(db)
    store, settings = Store(url, test_only=True), Settings(url, out, mode='mock')
    sql_digest = hashlib.sha256()
    active = False

    def before_sql(conn, cursor, statement, parameters, context, executemany):
        op = statement.lstrip().split(None, 1)[0].upper()
        if op != 'SELECT' and statement.strip().upper() != 'BEGIN IMMEDIATE':
            record['blocked'].append('NONREAD_SQL:' + op)
            raise AssertionError('Read-only causal regression rejects ' + op)
        if active:
            record['sql_counts'][op] = record['sql_counts'].get(op, 0) + 1
            sql_digest.update(json.dumps([statement, parameters], ensure_ascii=False,
                separators=(',', ':'), default=str).encode())

    event.listen(store.engine, 'before_cursor_execute', before_sql)
    try:
        worker, current, _ = helper.derive_pin(store, settings, out)
        helper.time = saved_helper_clock
        assert time.time is real_clock and runtime.time.time is real_clock
        full = Limits(**{name: getattr(settings, name) for name in Limits.model_fields})
        for name in ('check', 'input_key', 'add'):
            original = getattr(runtime._ColdGraphRead, name)
            def counted(*args, _name=name, _original=original, **kwargs):
                if active:
                    record['counts'][_name] = record['counts'].get(_name, 0) + 1
                return _original(*args, **kwargs)
            setattr(runtime._ColdGraphRead, name, counted)
        with store.tx() as c, pb._source_reads(store, c):
            driver = c.connection.driver_connection
            roles = dict(source=full, generate=None, platform=full,
                         trial=admission._limits(worker.pa_trial.contract), per_use=full)
            with runtime._cold_graph_read(worker, c, dict(current=current), roles, 'pre') as guard:
                assert driver.total_changes == 0
                active = True
                record['producer_calls'] += 1
                started, cpu = time.perf_counter(), time.thread_time()
                graph = runtime._cold_first_binding(worker, c, guard, current, full)
                record['cpu_seconds'] = time.thread_time() - cpu
                record['wall_seconds'] = time.perf_counter() - started
                active = False
                assert graph.guard is guard and guard.active
                final_bytes = guard.input_bytes()
                (out / 'complete-input.bin').write_bytes(final_bytes)
                record.update(final_bytes=len(final_bytes), final_sha=hashlib.sha256(final_bytes).hexdigest(),
                              guard_active_at_return=guard.active, changes=driver.total_changes)
            assert driver.total_changes == 0
        assert time.time is real_clock and not record['blocked']
        record['outcome'] = 'READ_COMPLETED_NOT_ADMISSION'
    except BaseException as error:
        record.update(outcome='FAILED', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        helper.time = saved_helper_clock
        store.engine.dispose()
        record.update(db_after=sha(db), source_after=sources(), sql_sha=sql_digest.hexdigest(),
                      product_clock_unchanged=time.time is real_clock)
        write(out / 'result.json', record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--child', choices=['baseline', 'candidate'])
    parser.add_argument('--epoch', type=float)
    args = parser.parse_args()
    if args.child:
        child(args.child, args.epoch)
        return
    initial = sources()
    summary = dict(baseline=BASE, source=initial, timeout_seconds_per_arm=45,
                   sealed_db_sha=sha(ROOT / 'sealed-prefix.db'), helper_sha=sha(ROOT / 'read_pin_helper.py'),
                   epoch=time.time(), arms=[])
    for arm in ('baseline', 'candidate'):
        out = ROOT / arm
        out.mkdir(exist_ok=False)
        shutil.copyfile(ROOT / 'sealed-prefix.db', out / 'prefix.db')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(REPO / 'src')
        with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
            started = time.perf_counter()
            process = subprocess.Popen([sys.executable, str(Path(__file__)), '--child', arm,
                '--epoch', str(summary['epoch'])], env=env, cwd=out, stdout=stdout, stderr=stderr)
            try:
                code = process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                summary.update(outcome='TIMEOUT', arm=arm)
                write(ROOT / 'summary.json', summary)
                raise
        summary['arms'].append(dict(arm=arm, exit_code=code, outer_seconds=time.perf_counter()-started))
        write(ROOT / 'summary.json', summary)
        if code != 0:
            raise RuntimeError('Arm refused or failed; no retry: ' + arm)
    old, new = [json.loads((ROOT / arm / 'result.json').read_text()) for arm in ('baseline', 'candidate')]
    for result in (old, new):
        assert result['source_before'] == result['source_after'] == initial == sources()
        assert result['db_before'] == result['db_after'] == summary['sealed_db_sha']
        assert result['producer_calls'] == 1 and result['changes'] == 0 and not result['blocked']
    assert old['sql_sha'] == new['sql_sha'] and old['sql_counts'] == new['sql_counts']
    assert old['counts'] == new['counts']
    assert (ROOT / 'baseline/complete-input.bin').read_bytes() == (ROOT / 'candidate/complete-input.bin').read_bytes()
    summary.update(outcome='EQUIVALENT_BOUNDED_DORMANT_READS', old_wall=old['wall_seconds'],
        new_wall=new['wall_seconds'], wall_reduction=1-new['wall_seconds']/old['wall_seconds'],
        old_cpu=old['cpu_seconds'], new_cpu=new['cpu_seconds'],
        complete_bytes_sha=old['final_sha'], counts=old['counts'], sql_counts=old['sql_counts'])
    write(ROOT / 'summary.json', summary)
    print(json.dumps({key:value for key,value in summary.items() if key!='source'}, indent=2))


if __name__ == '__main__':
    main()

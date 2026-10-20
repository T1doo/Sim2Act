"""One bounded paired dormant first binding; no real Worker/admission/model."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import tracemalloc
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act')
BASE = '78ed5bef2da3a175d819eb9a2f58b3bbf097f75b'
CANDIDATE = '25ee757bf07155bc30a809549af6a11a449bcd44'
DB_SHA = '9a9bdfcf0264a251670a2c59dcbd401e1e035656542413e032357a442802e4db'
HELPER_SHA = '1714d223e667948a1d84a54abfdb8e35f2670c6384fc162581105da775cf6d8a'
RUNTIME = 'src/sim2act/natural_spec_runtime.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sources():
    paths = list((REPO / 'src').rglob('*.py'))
    paths += [p for p in (REPO / 'schemas').rglob('*') if p.is_file()]
    paths += [REPO / 'pyproject.toml', REPO / 'requirements.lock']
    return {str(p.relative_to(REPO)): sha(p) for p in sorted(paths)}


def function_source(source):
    node = next(n for n in ast.parse(source).body
        if isinstance(n, ast.FunctionDef) and n.name == '_cold_graph_bytes')
    return ast.get_source_segment(source, node) + '\n'


def child(arm, epoch):
    import httpx
    from sqlalchemy import event
    from sim2act import app_jobs, apps, goal_applications as ga, lifecycle, text_apps
    from sim2act import natural_live_admission as admission
    from sim2act import natural_spec_runtime as runtime
    from sim2act import pa_spec_apps as spec, pa_trial_dispatch as dispatch
    from sim2act import pb_natural_specs as pb, pb_natural_uses as use
    from sim2act import production_trial_journal as journal, spec_production
    from sim2act.config import Settings
    from sim2act.contracts import Limits
    from sim2act.db import Store
    from sim2act.model import InternModel
    from sim2act.worker import Worker

    out, record = ROOT / arm, dict(arm=arm, producer_calls=0, blocked=[], counts={}, sql_counts={})
    db = out / 'prefix.db'
    record.update(source_before=sources(), db_before=sha(db))
    if arm == 'baseline':
        path = ROOT / 'baseline_function.py'
        exec(compile(path.read_text(), str(path), 'exec'), vars(runtime))
    real_clock = time.time
    active, phase, sql_records = False, 'setup', []

    def block(target, names):
        for name in names:
            label = target.__name__ + '.' + name
            def denied(*args, _label=label, **kwargs):
                record['blocked'].append(_label)
                raise AssertionError('Forbidden dormant reader path: ' + _label)
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
        (httpx.HTTPTransport, ('handle_request',)), (httpx.AsyncHTTPTransport, ('handle_async_request',)),
        (httpx.MockTransport, ('handle_request', 'handle_async_request')),
    ]:
        block(target, names)
    aliases = [('sim2act.lifecycle', 'validate_frozen_candidate', apps, 'validate_frozen_candidate'),
        ('sim2act.app_jobs', 'validate_frozen_candidate', apps, 'validate_frozen_candidate'),
        ('sim2act.app_jobs', 'read_release', lifecycle, 'read_release'),
        ('sim2act.registered_run_extraction', 'read_release', lifecycle, 'read_release')]
    originals = {(id(owner), name): getattr(owner, name) for _, _, owner, name in aliases}
    for target, names in [
        (ga, ('source', 'initial_messages', 'history', '_history', 'verified_candidate', '_verified_candidate', 'parse_candidate')),
        (spec, ('bound', '_bound', 'verify_job', 'receipts', 'verify_origin', 'model_source', 'audit_fingerprint', 'from_response')),
        (pb, ('source', '_source', 'source_audit', '_source_audit', 'review', 'verify', 'audit_fingerprint')),
        (use, ('bound', 'review', 'audit')), (apps, ('validate_frozen_candidate',)),
        (lifecycle, ('read_release', '_read_release')), (app_jobs, ('load_binding',)), (text_apps, ('verify_origin',)),
    ]:
        block(target, names)
    for module_name, alias, owner, name in aliases:
        module = sys.modules.get(module_name)
        if module is not None and getattr(module, alias) is originals[(id(owner), name)]:
            setattr(module, alias, getattr(owner, name))

    def sql_value(value):
        kind = type(value)
        if kind in (str, int, float, bool, type(None)):
            return value
        if kind is bytes:
            return {'bytes_hex': value.hex()}
        if kind is list or kind is tuple:
            return [sql_value(v) for v in value]
        if kind is dict and all(type(k) is str for k in value):
            return {k: sql_value(v) for k, v in value.items()}
        raise AssertionError('Unexpected SQL parameter type: ' + kind.__name__)

    def before_sql(conn, cursor, statement, parameters, context, executemany):
        op = statement.lstrip().split(None, 1)[0].upper()
        if op != 'SELECT' and statement.strip().upper() != 'BEGIN IMMEDIATE':
            record['blocked'].append('NONREAD_SQL:' + op)
            raise AssertionError('Read-only regression rejects ' + op)
        key = phase + ':' + op
        record['sql_counts'][key] = record['sql_counts'].get(key, 0) + 1
        # Copy only native driver parameters. No IO/hash or product traversal.
        sql_records.append(json.dumps([phase, statement, sql_value(parameters)],
            ensure_ascii=False, separators=(',', ':'), allow_nan=False))

    helper_spec = importlib.util.spec_from_file_location('sealed_read_pin_helper', ROOT / 'read_pin_helper.py')
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    helper_clock = helper.time
    helper.time = SimpleNamespace(time=lambda: epoch)
    url = 'sqlite:///' + str(db)
    store, settings = Store(url, test_only=True), Settings(url, out, mode='mock')
    event.listen(store.engine, 'before_cursor_execute', before_sql)
    try:
        worker, current, _ = helper.derive_pin(store, settings, out)
        helper.time = helper_clock
        assert time.time is real_clock and runtime.time.time is real_clock
        assert not tracemalloc.is_tracing() and sys.gettrace() is None and sys.getprofile() is None
        full = Limits(**{name: getattr(settings, name) for name in Limits.model_fields})
        for name in ('check', 'input_key', 'add'):
            original = getattr(runtime._ColdGraphRead, name)
            def counted(*args, _name=name, _original=original, **kwargs):
                if active:
                    record['counts'][_name] = record['counts'].get(_name, 0) + 1
                return _original(*args, **kwargs)
            setattr(runtime._ColdGraphRead, name, counted)
        original_producer = runtime._cold_first_binding
        def once(*args, **kwargs):
            record['producer_calls'] += 1
            assert record['producer_calls'] == 1, 'Second producer forbidden before execution'
            return original_producer(*args, **kwargs)
        runtime._cold_first_binding = once
        phase = 'scope_setup'
        with store.tx() as c, pb._source_reads(store, c):
            driver = c.connection.driver_connection
            roles = dict(source=full, generate=None, platform=full,
                trial=admission._limits(worker.pa_trial.contract), per_use=full)
            with runtime._cold_graph_read(worker, c, dict(current=current), roles, 'pre') as guard:
                assert driver.total_changes == 0
                active, phase = True, 'producer'
                started, cpu = time.perf_counter(), time.thread_time()
                graph = runtime._cold_first_binding(worker, c, guard, current, full)
                record['cpu_seconds'] = time.thread_time() - cpu
                record['wall_seconds'] = time.perf_counter() - started
                active, phase = False, 'post_measurement'
                assert graph.guard is guard and guard.active
                assert not tracemalloc.is_tracing()
                result_bytes = guard.input_bytes()
                (out / 'complete-input.bin').write_bytes(result_bytes)
                record.update(final_bytes=len(result_bytes), final_sha=hashlib.sha256(result_bytes).hexdigest(),
                    guard_active_at_return=guard.active, changes=driver.total_changes)
            assert driver.total_changes == 0
        assert not record['blocked'] and record['producer_calls'] == 1
        record['outcome'] = 'COMPLETE_DORMANT_READ_NOT_ADMISSION'
    except BaseException as error:
        record.update(outcome='FAILED', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        helper.time = helper_clock
        store.engine.dispose()
        sql_bytes = ('\n'.join(sql_records) + '\n').encode()
        (out / 'ordered-sql.jsonl').write_bytes(sql_bytes)
        record.update(source_after=sources(), db_after=sha(db), sql_sha=hashlib.sha256(sql_bytes).hexdigest(),
            product_clock_unchanged=time.time is real_clock, tracemalloc_active=tracemalloc.is_tracing())
        write(out / 'result.json', record)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--child', choices=['baseline', 'candidate'])
    parser.add_argument('--epoch', type=float)
    args = parser.parse_args()
    if args.child:
        child(args.child, args.epoch)
        return
    assert sha(ROOT / 'sealed-prefix.db') == DB_SHA
    assert sha(ROOT / 'read_pin_helper.py') == HELPER_SHA
    old = subprocess.check_output(['git', '-C', str(REPO), 'show', BASE + ':' + RUNTIME], text=True)
    new = subprocess.check_output(['git', '-C', str(REPO), 'show', CANDIDATE + ':' + RUNTIME], text=True)
    assert (ROOT / 'baseline_function.py').read_text() == function_source(old)
    assert (REPO / RUNTIME).read_text() == new
    initial = sources()
    receipt = dict(baseline=BASE, candidate=CANDIDATE, source=initial, epoch=time.time(),
        script_sha=sha(Path(__file__)), baseline_function_sha=sha(ROOT / 'baseline_function.py'),
        db_sha=DB_SHA, helper_sha=HELPER_SHA, timeout_seconds_per_arm=45, arms=[])
    for arm in ['baseline', 'candidate']:
        out = ROOT / arm
        out.mkdir(exist_ok=False)
        shutil.copyfile(ROOT / 'sealed-prefix.db', out / 'prefix.db')
        env = os.environ.copy()
        env['PYTHONPATH'] = str(REPO / 'src')
        command = [sys.executable, str(Path(__file__)), '--child', arm, '--epoch', str(receipt['epoch'])]
        with (out / 'stdout.txt').open('w') as stdout, (out / 'stderr.txt').open('w') as stderr:
            process = subprocess.Popen(command, env=env, cwd=out, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                receipt.update(outcome='TIMEOUT_STOPPED_NO_RETRY', failed_arm=arm)
                write(ROOT / 'receipt.json', receipt)
                raise
        receipt['arms'].append(dict(arm=arm, exit_code=code, command=command))
        write(ROOT / 'receipt.json', receipt)
        if code:
            raise RuntimeError('Refused/failed arm, no retry or second dependent arm: ' + arm)
    old, new = [json.loads((ROOT / arm / 'result.json').read_text()) for arm in ['baseline', 'candidate']]
    for result in [old, new]:
        assert result['source_before'] == result['source_after'] == initial == sources()
        assert result['db_before'] == result['db_after'] == DB_SHA == sha(ROOT / 'sealed-prefix.db')
        assert result['producer_calls'] == 1 and result['changes'] == 0 and not result['blocked']
        assert result['product_clock_unchanged'] and not result['tracemalloc_active']
    assert old['counts'] == new['counts'] and old['sql_counts'] == new['sql_counts']
    assert (ROOT / 'baseline/ordered-sql.jsonl').read_bytes() == (ROOT / 'candidate/ordered-sql.jsonl').read_bytes()
    assert (ROOT / 'baseline/complete-input.bin').read_bytes() == (ROOT / 'candidate/complete-input.bin').read_bytes()
    receipt.update(outcome='EQUIVALENT_SINGLE_PAIR_NOT_STATISTICAL_PERFORMANCE',
        old_wall=old['wall_seconds'], new_wall=new['wall_seconds'],
        old_cpu=old['cpu_seconds'], new_cpu=new['cpu_seconds'],
        wall_change_fraction=new['wall_seconds']/old['wall_seconds']-1,
        cpu_change_fraction=new['cpu_seconds']/old['cpu_seconds']-1,
        final_bytes=old['final_bytes'], final_sha=old['final_sha'], sql_sha=old['sql_sha'],
        counts=old['counts'], sql_counts=old['sql_counts'])
    write(ROOT / 'receipt.json', receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k != 'source'}, indent=2))


if __name__ == '__main__':
    main()

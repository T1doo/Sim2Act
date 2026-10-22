"""Pure supervisor shims: no subprocess, Mock, DB, model or signals execute."""

import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('mode', ['own-process-write', 'sample-error', 'child-timeout',
    'final-receipt-write', 'exit0-without-result', 'signal-permission-denied', 'source-read-error'])
def test_failures_are_sticky_and_clean_only_the_own_group(tmp_path, monkeypatch, mode):
    source = Path(__file__).parents[1] / 'scripts/run_cold_row_semantic_pair.py'
    spec = importlib.util.spec_from_file_location('offline_supervisor_shim', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo = tmp_path / 'fake-repo'
    scripts = repo / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / source.name).write_text('FAKE UNIT ROOT, NEVER EXECUTED')
    builder = scripts / 'build_cold_typed_native.py'
    builder.write_text('FAKE UNIT BUILD, NEVER EXECUTED')
    module.__file__ = str(scripts / source.name)
    out = tmp_path / 'fake-output'
    now, signals, waits = [0.0], [], []
    process = SimpleNamespace(pid=77777777, returncode=None)
    stderr = io.StringIO()
    def monotonic():
        return now[0]
    def sleep(seconds):
        now[0] += seconds
    module.time = SimpleNamespace(monotonic=monotonic, sleep=sleep)
    module.sys = SimpleNamespace(executable=sys.executable, stderr=stderr)
    def poll():
        return process.returncode
    def wait(timeout):
        waits.append(timeout)
        if process.returncode is None:
            now[0] += timeout
            raise subprocess.TimeoutExpired('FAKE ONLY', timeout)
        return process.returncode
    process.poll, process.wait = poll, wait
    def killpg(pid, value):
        assert pid == process.pid
        if value == 0:
            if process.returncode is not None:
                raise ProcessLookupError('FAKE group absent')
            return
        signals.append(value)
        if mode == 'signal-permission-denied':
            raise PermissionError('SIMULATED denial; no real signal was sent')
        if value == signal.SIGTERM and mode == 'child-timeout':
            return
        process.returncode = -value
    module.os = SimpleNamespace(walk=os.walk, environ=os.environ, killpg=killpg)
    def popen(command, **kwargs):
        assert kwargs['start_new_session'] is True
        assert kwargs['env']['COLD_MOCK_PROGRESS_PATH'] == str(out / 'mock-progress.json')
        if mode in ('final-receipt-write', 'exit0-without-result', 'source-read-error'):
            process.returncode = 0
        if mode == 'exit0-without-result':
            module.write(out / 'mock-progress.json', dict(mock_exchange_admissions=7,
                mock_entry_admissions=9, source_delegates=2))
        if mode == 'source-read-error':
            builder.unlink()
        return process
    module.subprocess = SimpleNamespace(Popen=popen, STDOUT=subprocess.STDOUT,
        TimeoutExpired=subprocess.TimeoutExpired, check_output=lambda *a, **kw: 'FAKE_HEAD\n')
    original_write = module.write
    def writing(path, value):
        if ((mode == 'own-process-write' and path.name == 'own-process.json') or
                (mode == 'final-receipt-write' and path.name == 'supervision.json')):
            raise OSError('SIMULATED receipt failure')
        original_write(path, value)
    module.write = writing
    if mode == 'sample-error':
        def sampling(path):
            raise OSError('SIMULATED sampling error')
        module.disk = sampling
    else:
        module.disk = lambda path: 64*1024**2+1
    monkeypatch.setattr(sys, 'argv', [str(source), '--output', str(out),
        '--typed-build', str(tmp_path), '--row-build', str(tmp_path)])
    with pytest.raises(SystemExit) as stopped:
        module.main()
    assert stopped.value.code == 1
    if mode == 'final-receipt-write':
        text = stderr.getvalue()
        assert text.startswith('SUPERVISION_RECEIPT_FALLBACK ')
        report = json.loads(text.removeprefix('SUPERVISION_RECEIPT_FALLBACK '))
        assert any(item['phase'] == 'final-receipt' for item in report['errors'])
    else:
        report = json.loads((out / 'supervision.json').read_text())
    assert report['status'] == 'FAILED_OR_UNKNOWN'
    assert report['cleanup_elapsed_seconds'] <= 10
    if mode == 'signal-permission-denied':
        assert signals == [signal.SIGTERM] and report['own_process_group_absent'] is False
        assert process.returncode is None
    elif mode in ('own-process-write', 'sample-error', 'child-timeout'):
        assert signals and waits and report['own_process_group_absent'] is True
    if mode == 'exit0-without-result':
        assert report['complete_mock_usage'] is True and report['complete_semantic_result'] is False
    if mode == 'source-read-error':
        assert report['source_freeze_unchanged'] is None

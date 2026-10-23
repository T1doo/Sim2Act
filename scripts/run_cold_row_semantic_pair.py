"""One bounded synthetic pair, never real-clock G0 or production authority."""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def disk(root):
    total = 0
    def denied(error):
        raise error
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=denied):
        dirs[:] = [name for name in dirs if not Path(folder, name).is_symlink()]
        for name in files:
            path = Path(folder, name)
            if not path.is_symlink():
                try:
                    total += path.stat().st_size
                except FileNotFoundError:
                    pass  # SQLite's journal may disappear between samples.
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=('row', 'frontier'), default='row')
    parser.add_argument('--typed-build', type=Path)
    parser.add_argument('--row-build', type=Path)
    args = parser.parse_args()
    if args.case == 'row' and (args.typed_build is None or args.row_build is None):
        parser.error('row comparison requires the original two explicit builds')
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir()  # Never overwrite, restore an old DB or automatically retry.
    paths = [*sorted((repo / 'src/sim2act').glob('*.py')),
        *sorted((repo / 'src/sim2act').glob('*.c')),
        *sorted((repo / 'tests').glob('*.py')), Path(__file__).resolve(),
        repo / 'scripts/build_cold_typed_native.py']
    frozen = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    write(output / 'source-freeze.json', frozen)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    write(output / 'technical-grant.json', dict(
        classification='SINGLE_USE_SYNTHETIC_TEST_ONLY_NOT_ACCOUNT_OR_MODEL_AUTHORITY',
        id=uuid.uuid4().hex, head=head, case=args.case, status='consumed-for-one-launch',
        limits=dict(mock_exchanges=7, mock_entries=9, total_seconds=600,
            cleanup_seconds=10, sampled_disk_bytes=64*1024**2, sample_interval_seconds=0.1),
        semantic_clock_only=True, real_models=0, cold2=False, w5=False))
    command = [sys.executable, '-m', 'pytest', '-q', '-s',
        ('tests/test_cold_row_native_pair.py' if args.case == 'row'
            else 'tests/test_cold_frontier_complete_pair.py'), '--basetemp=' + str(output / 'run'),
        '--junitxml=' + str(output / 'pair.xml')]
    env = dict(os.environ, COLD_MOCK_PROGRESS_PATH=str(output / 'mock-progress.json'))
    if args.case == 'row':
        env.update(COLD_NATIVE_TEST_DIR=str(args.typed_build.resolve()),
            COLD_ROW_TEST_DIR=str(args.row_build.resolve()))
    errors, samples = [], []
    process, reason, peak = None, None, 0
    denied_signal, gone = False, False
    start = time.monotonic()
    receipt = dict(head=head, status='FAILED_OR_UNKNOWN', automatic_retries=0)

    def error(phase, caught):
        errors.append(dict(phase=phase, type=type(caught).__name__, message=str(caught)))

    def exists():
        nonlocal denied_signal, gone
        if gone:
            return False
        if denied_signal:
            return None
        try:
            os.killpg(process.pid, 0)
            return True
        except ProcessLookupError:
            gone = True
            return False
        except BaseException as caught:
            error('group-probe', caught)
            if isinstance(caught, PermissionError):
                denied_signal = True
            return None

    def send(value):
        nonlocal denied_signal, gone
        if denied_signal or gone:
            return
        try:
            os.killpg(process.pid, value)  # Only our Popen-created session.
        except ProcessLookupError:
            gone = True
        except BaseException as caught:
            error('own-group-signal', caught)
            if isinstance(caught, PermissionError):
                denied_signal = True  # No alternate signal/permission bypass.

    def collect(phase, action, default=None):
        try:
            return action()
        except BaseException as caught:
            error(phase, caught)
            return default

    phase = 'log-open'
    try:
        with (output / 'pair.log').open('wb') as log:
            phase = 'spawn'
            process = subprocess.Popen(command, cwd=repo, env=env, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
            phase = 'own-process-receipt'
            write(output / 'own-process.json', dict(pid=process.pid, pgid=process.pid, command=command))
            phase = 'monitor'
            while process.poll() is None:
                now = time.monotonic()
                peak = max(peak, disk(output))
                samples.append(now-start)
                if now-start >= 600:
                    reason = 'wall-limit'
                elif peak > 64*1024**2:
                    reason = 'sampled-disk-limit'
                if reason:
                    break
                time.sleep(0.1)
    except BaseException as caught:
        error(phase, caught)
        reason = reason or 'supervision-error'
    finally:
        cleanup_start = time.monotonic()
        deadline = cleanup_start + 10
        group_absent = False
        if process is not None:
            try:
                code = collect('root-poll', process.poll)
                active = exists()
                if code is None or active is True:
                    send(signal.SIGTERM)
                try:
                    process.wait(timeout=max(0, deadline-time.monotonic()-1))
                except subprocess.TimeoutExpired:
                    send(signal.SIGKILL)
                    collect('root-reap', lambda: process.wait(timeout=max(0, deadline-time.monotonic())))
                except BaseException as caught:
                    error('root-wait', caught)
                    send(signal.SIGKILL)
                    collect('root-reap', lambda: process.wait(timeout=max(0, deadline-time.monotonic())))
                active = exists()
                if active is True:
                    send(signal.SIGKILL)
                    while active is True and time.monotonic() < deadline:
                        time.sleep(min(0.01, max(0, deadline-time.monotonic())))
                        active = exists()
                group_absent = active is False
            except BaseException as caught:
                error('cleanup', caught)
        cleanup_elapsed = time.monotonic()-cleanup_start
        usage = collect('mock-progress', lambda: json.loads((output/'mock-progress.json').read_text()), 'UNKNOWN')
        usage_ok = (type(usage) is dict and usage.get('mock_exchange_admissions') == 7
            and usage.get('mock_entry_admissions') == 9 and usage.get('source_delegates') == 2)
        unchanged = collect('source-freeze', lambda: all(
            hashlib.sha256((repo/p).read_bytes()).hexdigest() == h for p,h in frozen.items()))
        def result_check():
            results = list(output.rglob('row-pair.json' if args.case == 'row' else 'frontier-pair.json'))
            if len(results) != 1:
                return False
            result = json.loads(results[0].read_text())
            return (result.get('classification') == 'CONFIGURED_SYNTHETIC_SEMANTIC_CLOCK_NOT_G0'
                and result.get('exact_output_sql_receipt_final_gate') is True
                and result.get('base_qualification_preserved') is True
                and result.get('cleanup_threads_empty') is True
                and result.get('mock_exchanges') == 7 and result.get('mock_entries') == 9
                and result.get('real_models') == 0 and result.get('cold2') is False
                and result.get('w5') is False)
        complete = collect('semantic-result', result_check, False)
        intervals = [b-a for a,b in zip(samples, samples[1:], strict=False)]
        receipt.update(pid=None if process is None else process.pid,
            returncode=None if process is None else process.returncode, stop_reason=reason,
            elapsed_seconds=time.monotonic()-start, cleanup_elapsed_seconds=cleanup_elapsed,
            own_process_group_absent=group_absent, errors=errors,
            sampled_peak_bytes=peak, configured_sample_interval_seconds=0.1,
            actual_interval_min_seconds=min(intervals) if intervals else None,
            actual_interval_max_seconds=max(intervals) if intervals else None, samples=len(samples),
            disk_monitor_is_not_native_quota=True, source_freeze_unchanged=unchanged,
            mock_usage=usage, complete_mock_usage=usage_ok, complete_semantic_result=complete)
        if (process is not None and process.returncode == 0 and not errors and reason is None
                and group_absent and unchanged is True and usage_ok and complete
                and cleanup_elapsed <= 10):
            receipt['status'] = 'COMPLETE_SYNTHETIC_PASS'
        try:
            write(output / 'supervision.json', receipt)
        except BaseException as caught:
            error('final-receipt', caught)
            receipt['status'] = 'FAILED_OR_UNKNOWN'
            print('SUPERVISION_RECEIPT_FALLBACK ' + json.dumps(receipt), file=sys.stderr)
    if receipt['status'] != 'COMPLETE_SYNTHETIC_PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()

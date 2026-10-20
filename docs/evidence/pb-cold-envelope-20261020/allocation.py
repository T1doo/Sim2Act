"""Bounded synthetic codec allocation comparison; no Worker, DB, model or PB."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc

BASE = '78ed5bef2da3a175d819eb9a2f58b3bbf097f75b'
ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act')
SOURCE = 'src/sim2act/natural_spec_runtime.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def child(arm):
    import httpx
    from sqlalchemy.engine import RowMapping
    from sqlalchemy.engine.result import SimpleResultMetaData
    from sqlalchemy.sql.elements import quoted_name
    from sim2act import natural_spec_runtime as runtime
    from sim2act.contracts import Limits

    def forbidden(*args, **kwargs):
        raise AssertionError('Codec allocation comparison forbids all HTTP and Mock')

    for cls, name in [(httpx.Client, 'send'), (httpx.AsyncClient, 'send'),
        (httpx.HTTPTransport, 'handle_request'), (httpx.AsyncHTTPTransport, 'handle_async_request'),
        (httpx.MockTransport, 'handle_request'), (httpx.MockTransport, 'handle_async_request')]:
        setattr(cls, name, forbidden)
    before = sha((REPO / SOURCE).read_bytes())
    encode = runtime._cold_graph_bytes
    if arm == 'baseline':
        namespace = dict(vars(runtime))
        code = (ROOT / 'baseline_function.py').read_text()
        exec(compile(code, str(ROOT / 'baseline_function.py'), 'exec'), namespace)
        encode = namespace['_cold_graph_bytes']
    results = []
    for size in [6435, 65536, 579257]:
        full = Limits(max_requests=4, max_tools=4, max_repairs=1,
            max_total_tokens=64000, max_output_tokens=1024, run_seconds=300)
        shared = dict(wire=b'x' * size, limits=full)
        data = (shared, dict(hidden=[full, shared]))
        row = RowMapping(SimpleResultMetaData([quoted_name('visible', True)]), None,
            {'visible': 0, 'unused': 1}, data)
        values = dict(first=row, again=row, shared=shared, complete_data=data)
        # Complete incoming validation is unchanged and outside allocation scope.
        runtime._cold_graph_validate_inputs(values)
        tracemalloc.start()
        started, cpu = time.perf_counter(), time.thread_time()
        encoded = encode(values)
        elapsed_cpu = time.thread_time() - cpu
        elapsed = time.perf_counter() - started
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        path = ROOT / f'{arm}-{size}.bin'
        path.write_bytes(encoded)
        results.append(dict(payload_size=size, output_size=len(encoded), output_sha=sha(encoded),
            current_bytes=current, peak_bytes=peak, wall_seconds=elapsed, cpu_seconds=elapsed_cpu))
    after = sha((REPO / SOURCE).read_bytes())
    assert before == after
    (ROOT / f'{arm}.json').write_text(json.dumps(dict(arm=arm, source_sha=before,
        source_unchanged=before == after, vectors=results), indent=2) + '\n')


def main():
    if len(sys.argv) == 2:
        child(sys.argv[1])
        return
    source = subprocess.check_output(['git', '-C', str(REPO), 'show', BASE + ':' + SOURCE], text=True)
    tree = ast.parse(source)
    original = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
        and node.name == '_cold_graph_bytes')
    baseline = ast.get_source_segment(source, original) + '\n'
    path = ROOT / 'baseline_function.py'
    assert not path.exists()
    path.write_text(baseline)
    initial = sha((REPO / SOURCE).read_bytes())
    commands = []
    for arm in ['baseline', 'candidate']:
        command = [sys.executable, str(Path(__file__)), arm]
        with (ROOT / f'{arm}.stdout').open('w') as stdout, (ROOT / f'{arm}.stderr').open('w') as stderr:
            # Pure synthetic codec only, at most 15 seconds per independent child.
            result = subprocess.run(command, cwd=REPO, stdout=stdout, stderr=stderr, timeout=15)
        commands.append(dict(arm=arm, command=command, exit_code=result.returncode))
        if result.returncode:
            raise RuntimeError('Refused/failed arm; stop without retry: ' + arm)
    old = json.loads((ROOT / 'baseline.json').read_text())
    new = json.loads((ROOT / 'candidate.json').read_text())
    comparison = []
    for left, right in zip(old['vectors'], new['vectors'], strict=True):
        size = left['payload_size']
        assert (ROOT / f'baseline-{size}.bin').read_bytes() == (ROOT / f'candidate-{size}.bin').read_bytes()
        comparison.append(dict(payload_size=size, output_size=left['output_size'], output_sha=left['output_sha'],
            old_peak=left['peak_bytes'], new_peak=right['peak_bytes'],
            peak_reduction=left['peak_bytes']-right['peak_bytes']))
    assert initial == sha((REPO / SOURCE).read_bytes()) == old['source_sha'] == new['source_sha']
    receipt = dict(scope='SYNTHETIC_CODEC_ONLY_NOT_G0_OR_PB', baseline=BASE,
        baseline_function_sha=sha(path.read_bytes()), script_sha=sha(Path(__file__).read_bytes()),
        source_sha=initial, commands=commands, baseline_result=old, candidate_result=new, comparison=comparison,
        same_complete_bytes=True, source_unchanged=True,
        limitation='tracemalloc peak of one encoding per vector; no G0 timing/performance inference')
    (ROOT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(comparison, indent=2))


if __name__ == '__main__':
    main()

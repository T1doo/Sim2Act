"""Reuse completed sealed facts, never seed/submit/execute a new business run."""
import json
import os
import subprocess
import time
from pathlib import Path


def test_frontend_read_sealed_local_api(tmp_path):
    root = tmp_path / 'content'
    root.mkdir()
    until = time.time() + 30
    env = dict(os.environ, PYTHONPATH=str(Path('src').resolve()))
    log = (tmp_path / 'api.log').open('wb')
    child = subprocess.Popen(['.venv/bin/python', 'scripts/readonly_content_fixture.py',
                              str(root), str(until * 1000)], env=env, stdout=log,
                             stderr=subprocess.STDOUT)
    forced = False
    try:
        ready = root / 'content-ready.json'
        while not ready.exists():
            assert child.poll() is None and time.time() < until, 'readonly fixture startup failed'
            time.sleep(.01)
        # Keep the synthetic public identity out of driver stdout; original
        # helper deletes this private ready file on normal cleanup.
        result = subprocess.run(['node', 'tests/frontend_read_http.cjs', str(ready)],
                                capture_output=True, text=True,
                                timeout=max(.01, until - time.time()), env=env)
        (tmp_path / 'driver.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        assert report['status'] == 'PASS' and report['business_post'] == report['models'] == 0
    finally:
        (root / 'content-stop').touch()
        try:
            child.wait(timeout=max(.01, until + 10 - time.time()))
        except subprocess.TimeoutExpired:
            forced = True
            child.terminate()
            child.wait(timeout=2)
        log.close()
    assert not forced and child.returncode == 0
    saved = json.loads((root / 'content-result.json').read_text())
    assert saved['status'] == 'PASS' and saved['database_bytes_unchanged']
    assert saved['before'] == saved['after'] and saved['server_counts']['business_get'] == 7
    assert saved['server_counts']['business_post'] == 0 and not saved['forbidden_calls']
    assert saved['cleanup']['api_stopped'] and not saved['cleanup']['anyio_alive']
    assert saved['cleanup']['within_deadline'] and saved['cleanup']['fixture_deleted']

"""One finite controlled current-GET failure test; no HTTP/Worker/native."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def test_current_failed_get_keeps_original_save_pending(tmp_path):
    repo = Path('/workspace/Sim2Act')
    own = Path('/tmp/own-goal-read-error-review-20261012/final')
    source = repo / 'src/sim2act/web/owner-review.js'
    output = tmp_path / 'result.json'
    result = subprocess.run(['node', str(own / 'current_readback_failure.cjs'),
        'current-save-readback-failure', str(source), str(output), str(repo / 'src/sim2act/web')],
        text=True, capture_output=True, timeout=20,
        env={**os.environ, 'NODE_PATH': '/workspace/node-tools/node_modules'})
    evidence = own / 'current-readback-extra-artifacts'
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'current-save-readback-failure.log').write_text(result.stdout + result.stderr)
    (evidence / 'current-save-readback-failure-exit.json').write_text(json.dumps({'exit_code': result.returncode}))
    if output.exists():
        (evidence / 'current-save-readback-failure.json').write_bytes(output.read_bytes())
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads(output.read_text())
    assert proof['status'] == 'PASS' and all(proof['checks'].values())
    assert proof['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert proof['classification'] == 'CONTROLLED_LOCAL_SOURCE_JSDOM_REAL_SHA256'
    assert proof['checks']['pending_identity_kept'] and proof['checks']['current_state_not_cleared']
    assert proof['checks']['status_valid'] and proof['checks']['post_count_exact']
    assert len(proof['requests']) == 3
    assert [r['method'] for r in proof['requests']] == ['GET', 'POST', 'GET']
    assert '?request_key=' in proof['requests'][-1]['url']

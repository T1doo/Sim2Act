"""Filesystem-only preparation gate. Does not launch or authorize any window."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
plan = json.loads((ROOT / 'plan.json').read_text())
assert plan['status'] == 'DESIGN_ONLY_NOT_EXECUTABLE'
assert plan['execution_authorized'] is False and plan['run_created'] is False
subprocess.run(['git', 'merge-base', '--is-ancestor', plan['revised_after_product'], 'HEAD'],
               cwd=REPO, check=True)
manifest = json.loads((ROOT / 'runtime-manifest.json').read_text())
for name, witness in manifest.items():
    data = (REPO / name).read_bytes()
    if witness['normalization'] == 'LF':
        data = data.replace(b'\r\n', b'\n')
    assert hashlib.sha256(data).hexdigest() == witness['canonical_sha256'], name
for name, witness in plan['assets']['before'].items():
    data = (ROOT / 'before-assets' / name).read_bytes()
    assert len(data) == witness['bytes']
    assert hashlib.sha256(data).hexdigest() == witness['sha256'], name
assert len(plan['frames']) == plan['limits']['png_max'] == 4
assert {tuple(frame['viewport'].values()) for frame in plan['frames']} == {(1366, 900), (390, 844)}
for prefix, product in [('before', plan['before_product']),
                        ('after', plan['revised_after_product'])]:
    frames = [frame for frame in plan['frames'] if frame['name'].startswith(prefix + '-')]
    assert len(frames) == 2
    assert all(frame['product'] == product and frame['full_page'] is False for frame in frames)
    assert {tuple(frame['viewport'].values()) for frame in frames} == {(1366, 900), (390, 844)}
for name, value in {
    'job_seconds': 240, 'work_seconds_including_setup': 180,
    'shared_cleanup_seconds': 10, 'node_cleanup_max_seconds_within_shared': 4,
    'business_get_max': 100, 'static_get_max': 120,
    'business_post_max': 0, 'real_model_max': 0, 'new_worker_max': 0,
    'new_source_max': 0, 'new_extract_max': 0, 'auto_retry_max': 0,
    'redirect_or_paid_fallback': False, 'rss_or_disk_hard_quota_claimed': False,
}.items():
    assert type(plan['limits'][name]) is type(value) and plan['limits'][name] == value, name
print(json.dumps({'status': 'FILES_MATCH_NOT_WINDOW_READY', 'runtime_files': len(manifest),
                  'baseline_assets': 3, 'native_execution': 'NOT_RUN',
                  'blockers': plan['readiness_blockers']}, ensure_ascii=False, indent=2))

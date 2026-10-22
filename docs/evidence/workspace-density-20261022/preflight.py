"""Offline launch layout and sealed read-only fixture checks; never start a UI/API."""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'src'), str(REPO / 'scripts')]
spec = importlib.util.spec_from_file_location('visual_helper', REPO / 'scripts/protocol_completion_browser_ci.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
workflow = (REPO / '.github/workflows/windows-native-mock.yml').read_text()
block = workflow.split('sparse-checkout: |', 1)[1].split('      - uses:', 1)[0]
patterns = [line.strip().lstrip('/') for line in block.splitlines() if line.strip()]
files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=REPO, text=True).splitlines()
selected = [n for n in files if any(n.startswith(p) if p.endswith('/') else n == p for p in patterns)]
assert '[workspace-visual-once-20261022]' in workflow
assert 'WindowsExtractCompletionUI.ps1 -WorkspaceVisual' in workflow
with tempfile.TemporaryDirectory(prefix='sim-visual-preflight-', dir='/workspace') as temporary:
    root = Path(temporary)
    checkout = root / 'checkout'
    for name in selected:
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    tools = root / 'tool-layout'
    for name in ('python.exe', 'pwsh.exe', 'node.exe', 'npm.cmd', 'git.exe', 'node_modules/npm/bin/npm-cli.js'):
        file = tools / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'')  # Layout witnesses only; never execute these files.
    output = root / 'output'
    output.mkdir()
    with patch.object(helper, 'REPO', checkout), patch.object(sys, 'executable', str(tools / 'python.exe')), patch.object(helper.shutil, 'which', side_effect=lambda n: str(tools / n)), patch.dict(helper.os.environ, {'pythonLocation': str(tools)}):
        paths = helper.launch_paths(output, time.monotonic() + 10, 'source', readback=True, completion_readback=True, workspace_visual=True)
    from protocol_completion_readback_fixture import cases, prepare
    from sqlalchemy import event, select

    from sim2act.config import Settings
    from sim2act.db import Store, fingerprint, meta
    originals, sidecars = prepare(output)
    stores = [Store('sqlite:///' + str(output / n), test_only=True) for n in ('fixture.sqlite', 'extract.sqlite')]
    configs = [Settings(**dict(o['settings'], database_url=str(s.engine.url), data_dir=output)) for o, s in zip(originals, stores, strict=True)]
    verbs = {}
    def readonly(_c, _cu, sql, _p, _co, _m):
        verb = sql.lstrip().split(None, 1)[0].upper()
        assert verb in {'SELECT', 'BEGIN'}, sql
        verbs[verb] = verbs.get(verb, 0) + 1
    def snapshot(s):
        with s.engine.connect() as c:
            return {t.name: sorted(fingerprint(dict(r)) for r in c.execute(select(t)).mappings()) for t in meta.sorted_tables}
    for store in stores:
        event.listen(store.engine, 'before_cursor_execute', readonly)
    first = [snapshot(s) for s in stores]
    sides = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sidecars}
    try:
        with patch.object(time, 'time', return_value=max(o['resume_at'] for o in originals)):
            observed = cases(stores, configs, originals)
        assert [c['current']['phase'] for c in observed] == ['source', 'extract']
        assert [snapshot(s) for s in stores] == first
        assert sides == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sidecars}
    finally:
        for store in stores:
            store.engine.dispose()
    for name in ('index.html', 'app.css'):
        raw = (REPO / 'docs/evidence/workspace-refinement-native-20261022/before' / name).read_bytes()
        assert raw == subprocess.check_output(['git', 'show', '51bcbcde3d9188420081802aa9aa35aebe5d009a:src/sim2act/web/' + name], cwd=REPO)
    for name in (REPO / 'src/sim2act/web').glob('*.js'):
        assert name.read_bytes() == subprocess.check_output(['git', 'show', 'e4313c9d9c76fe10d4668983ce0e7cfadc3c1fcc:' + str(name.relative_to(REPO))], cwd=REPO)
    print(json.dumps({'status': 'PASS', 'scope': 'offline layout and sealed SQLite, not Windows/DOM/pixels', 'selected_files': len(selected), 'path_witnesses': len(paths), 'snapshot_tables': [len(x) for x in first], 'snapshot_fingerprints': [fingerprint(x) for x in first], 'sql_verbs': verbs, 'sidecars': sides, 'new_http': 0, 'new_models': 0, 'new_browser': 0, 'work_seconds': 180, 'shared_cleanup_seconds': 10, 'business_get_limit': 100, 'static_get_limit': 120, 'business_post_limit': 0, 'png_limit': 10, 'evidence_max_file_bytes': 500000, 'evidence_max_total_bytes': 2000000}, indent=2))

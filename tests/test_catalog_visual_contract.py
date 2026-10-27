"""No Windows process/browser/network: source and private dependency layout only."""
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalog_contract', REPO / 'scripts/catalog_visual_contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def test_frozen_runtime_and_product(tmp_path):
    # The native snapshot is historical. Normal product edits must not rewrite
    # its witnesses or be admitted by them. Check the exact prepared Git tree.
    prepared = '2e00d679884f195f02dc32cef9e75d95acb3de4a'
    local_git = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    available = subprocess.run(['git', 'cat-file', '-e', prepared + '^{commit}'],
                               cwd=REPO, env=local_git, capture_output=True)
    if available.returncode:
        pytest.skip('historical prepared Git object unavailable; no current-source qualification')
    manifest_path = contract.CONTRACT.parent / 'runtime-manifest.json'
    manifest = json.loads((REPO / manifest_path).read_text())
    names = [contract.CONTRACT.as_posix(), manifest_path.as_posix(), *manifest]
    specs = ''.join(prepared + ':' + name + '\n' for name in names)
    result = subprocess.run(['git', 'cat-file', '--batch'], input=specs.encode(),
                            cwd=REPO, env=local_git, capture_output=True, check=True)
    stream = io.BytesIO(result.stdout)
    for name in names:
        path = Path(name)
        assert not path.is_absolute() and '..' not in path.parts
        _, kind, size = stream.readline().split()
        assert kind == b'blob'
        data = stream.read(int(size))
        assert len(data) == int(size) and stream.read(1) == b'\n'
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    assert not stream.read()
    value = contract.verify_contract(tmp_path)
    assert not value['run_created'] and not value['execution_authorized']


def test_tools_are_private_and_refuse_reuse(tmp_path):
    tools, temp = contract.prepare_tools(REPO, tmp_path)
    assert tools.parent == temp.parent == tmp_path
    for name in ('package.json', 'package-lock.json'):
        assert (tools / name).read_bytes() == (REPO / 'scripts/browser-ci' / name).read_bytes()
    with pytest.raises(FileExistsError):
        contract.prepare_tools(REPO, tmp_path)


def test_drift_rejected_before_setup(tmp_path):
    dest = tmp_path / contract.CONTRACT
    dest.parent.mkdir(parents=True)
    value = json.loads((REPO / contract.CONTRACT).read_text())
    dest.write_text(json.dumps(value))
    target = tmp_path / 'changed.txt'
    target.write_text('drift')
    (dest.parent / 'runtime-manifest.json').write_text(json.dumps({'changed.txt': {
        'normalization': 'LF', 'canonical_sha256': '0' * 64}}))
    with pytest.raises(AssertionError, match='changed.txt'):
        contract.verify_contract(tmp_path)
    assert not (tmp_path / 'browser-tools').exists()

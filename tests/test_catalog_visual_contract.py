"""No Windows process/browser/network: source and private dependency layout only."""
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('catalog_contract', REPO / 'scripts/catalog_visual_contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def test_frozen_runtime_and_product():
    value = contract.verify_contract(REPO)
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

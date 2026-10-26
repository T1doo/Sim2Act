"""Offline source qualification and job-owned files for the catalog-only mode."""
import hashlib
import json
import shutil
from pathlib import Path

CONTRACT = Path('docs/evidence/catalog-four-frame-wiring-20261026/execution.json')
BASELINE = Path('docs/evidence/catalog-four-frame-plan-20261026/before-assets')


def verify_contract(repo):
    contract = json.loads((repo / CONTRACT).read_text(encoding='utf-8'))
    assert contract['status'] == 'SOURCE_PREPARED_NOT_RUN'
    assert contract['execution_authorized'] is False
    assert contract['before_product'] == 'cc4e609539e20d4e3d24a0186650e8f6fe2ce32e'
    assert contract['after_product'] == '521a47bcb1d6e60e3a11b4fa02552932043f7031'
    assert contract['limits'] == {'work_seconds': 180, 'cleanup_seconds': 10,
                                  'business_get': 100, 'static_get': 120,
                                  'screenshots': 4, 'business_post': 0}
    manifest = json.loads((repo / CONTRACT.parent / 'runtime-manifest.json').read_text())
    for name, witness in manifest.items():
        path = Path(name)
        assert not path.is_absolute() and '..' not in path.parts
        data = (repo / path).read_bytes()
        if witness['normalization'] == 'LF':
            data = data.replace(b'\r\n', b'\n')
        else:
            assert witness['normalization'] == 'exact_binary'
        assert hashlib.sha256(data).hexdigest() == witness['canonical_sha256'], name
    for name, digest in contract['before_assets'].items():
        assert name in ('index.html', 'app.css', 'app.js')
        assert hashlib.sha256((repo / BASELINE / name).read_bytes()).hexdigest() == digest
    for name, digest in contract['after_assets'].items():
        data = (repo / 'src/sim2act/web' / name).read_bytes().replace(b'\r\n', b'\n')
        assert hashlib.sha256(data).hexdigest() == digest, name
    return contract


def prepare_tools(repo, root):
    """Never install into checkout or delete an existing/shared dependency tree."""
    tools, temp = root / 'browser-tools', root / 'child-temp'
    tools.mkdir()  # Refuse reuse, even inside this fresh job root.
    temp.mkdir()
    for name in ('package.json', 'package-lock.json'):
        shutil.copyfile(repo / 'scripts/browser-ci' / name, tools / name)
    return tools, temp

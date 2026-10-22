"""ASAN preload identity only; no Worker, transport or Mock execution."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from sim2act import _cold_typed_native_candidate as candidate


def mapping(path, *, permissions='r-xp', inode=None, device=None):
    info = candidate._ASAN_REAL.stat()
    if device is None:
        device = f'{os.major(info.st_dev):02x}:{os.minor(info.st_dev):02x}'
    if inode is None:
        inode = info.st_ino
    return f'70000000-70001000 {permissions} 00000000 {device} {inode} {path}\n'


@pytest.mark.parametrize('spelling', ['_ASAN_LINK', '_ASAN_REAL'])
def test_known_runtime_link_and_canonical_mapping(monkeypatch, spelling):
    original = Path.read_text
    text = mapping(getattr(candidate, spelling))
    monkeypatch.setattr(Path, 'read_text', lambda self, *a, **kw:
        text if self == Path('/proc/self/maps') else original(self, *a, **kw))
    assert candidate._asan_runtime_mapped()


@pytest.mark.parametrize('case', ['absent', 'neighbor', 'deleted', 'nonexec',
    'inode', 'device', 'malformed', 'link', 'digest'])
def test_unknown_runtime_identity_rejected(monkeypatch, case):
    path = candidate._ASAN_REAL
    text = mapping(path)
    if case == 'absent':
        text = ''
    elif case == 'neighbor':
        text = mapping(str(path) + '.other')
    elif case == 'deleted':
        text = mapping(str(path) + ' (deleted)')
    elif case == 'nonexec':
        text = mapping(path, permissions='r--p')
    elif case == 'inode':
        text = mapping(path, inode=path.stat().st_ino + 1)
    elif case == 'device':
        text = mapping(path, device='00:00')
    elif case == 'malformed':
        text = mapping(path, device='unknown:device')
    elif case == 'link':
        monkeypatch.setattr(candidate, '_ASAN_LINK', path.with_name('unknown-libasan.so'))
    elif case == 'digest':
        monkeypatch.setattr(candidate, '_ASAN_SHA256', '0' * 64)
    original = Path.read_text
    monkeypatch.setattr(Path, 'read_text', lambda self, *a, **kw:
        text if self == Path('/proc/self/maps') else original(self, *a, **kw))
    assert not candidate._asan_runtime_mapped()


@pytest.mark.parametrize('changed', ['st_atime_ns', 'st_size', 'st_mtime_ns', 'st_ctime_ns'])
def test_hash_read_atime_is_allowed_but_content_metadata_changes_are_not(monkeypatch, changed):
    info = candidate._ASAN_REAL.stat()
    attributes = {name: getattr(info, name) for name in (
        'st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_atime_ns')}
    calls = []
    def fstat(fd):
        current = attributes.copy()
        if calls:
            current[changed] += 1
        calls.append(fd)
        return SimpleNamespace(**current)
    text = mapping(candidate._ASAN_REAL)
    original = Path.read_text
    monkeypatch.setattr(candidate.os, 'fstat', fstat)
    monkeypatch.setattr(Path, 'read_text', lambda self, *a, **kw:
        text if self == Path('/proc/self/maps') else original(self, *a, **kw))
    assert candidate._asan_runtime_mapped() is (changed == 'st_atime_ns')
    assert len(calls) == 2


def test_actual_preload_and_rejection_before_extension_import(tmp_path, monkeypatch):
    directory = os.environ.get('COLD_NATIVE_TEST_DIR')
    if directory is None:
        pytest.skip('Explicit native test build not requested')
    import json
    import sysconfig
    path = Path(directory) / ('_cold_typed_native_impl' + sysconfig.get_config_var('EXT_SUFFIX'))
    proof = json.loads(path.with_suffix(path.suffix + '.json').read_text())
    if proof['sanitizer'] != 'address':
        pytest.skip('This assertion requires the ASAN build and preload')
    assert candidate._asan_runtime_mapped()
    assert candidate.load_candidate(path) is not None
    monkeypatch.setattr(candidate, '_asan_runtime_mapped', lambda: False)
    def forbidden(*args, **kwargs):
        pytest.fail('Rejected ASAN mapping must not initialize an extension')
    monkeypatch.setattr(candidate.importlib.util, 'module_from_spec', forbidden)
    assert candidate.load_candidate(path) is None

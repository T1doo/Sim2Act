"""Explicit offline RowMapping leaf. Default runtime routing is unchanged.

No discovery, installation, permission, model or production qualification. The
original single-argument function runs only on a pre-projection None selection;
native exceptions propagate without retry. This is not a Pickler method.
"""

import hashlib
import builtins
import importlib.util
from inspect import getattr_static
import json
import sys
import sysconfig
from pathlib import Path
from types import MemberDescriptorType, ModuleType

from . import _cold_typed_native_candidate as build
from . import natural_spec_runtime as runtime

_ORIGINAL = runtime._cold_graph_row_storage
_SOURCES = {
    'natural_spec_runtime.py': 'c06226860b7690daff210be62e69433eb2a174f4a63b90ba3d18304b2fca0f12',
    'natural_specs.py': 'd9cc806c4d440d3a1486da263f6ffe71cce8612164264fca4760476f1a71b6e0',
}
_REQUIRE, _LEAF = runtime.require, runtime.codec.require
_CODES = (_ORIGINAL.__code__, _REQUIRE.__code__, _LEAF.__code__)
_BUILTINS = {name: getattr(builtins, name) for name in ('type', 'object', 'dict', 'list', 'tuple', 'str', 'len', 'all')}
_BINARIES = {
    None: 'd3fe559a0f5b11d958c11a6785828f422119b1294330adf30fe8a9023923b748',
    'address': '71d82103c0a91686b6a73760619b0d2df90a122f2fd69a9b7691d7ad9f8f246e',
}
_SQL = {
    'sqlalchemy.cyextension.resultproxy': '73c1c4ede83b6ceaabf546a4211b92e88da7a089dde29d96b539a7adb9f67f74',
    'sqlalchemy.engine.row': 'b02f758c84c1a22b448637909b7e884bb2a31b08992638b008acce15bc69e6aa',
    'sqlalchemy.engine.result': 'f5696c92dff3bf562ab3fe0476a125a8c565c8aba1a90ae6dc4a65ee2dd21698',
    'sqlalchemy.engine.cursor': 'e7ea64279c56a57c99e7a06e5e9f1951d023c0318e2119916eff888984ba2097',
    'sqlalchemy.sql.elements': 'e11b4b6db3482cffae1e2e6958ae8c80ff5f9d2e7a6626e10066373359235c95',
}


class _OfflineReader:
    __slots__ = ('module', 'entry')

    def __init__(self, module, entry):
        self.module, self.entry = module, entry

    def storage(self, value):
        actual = self.entry(value)
        if actual is None:
            return _ORIGINAL(value)
        return actual

    def counts(self):
        return self.module.counts(self.entry)


def load_candidate(path):
    """Only an explicit source/binary/ABI/installed-SQLAlchemy build witness."""
    if (sys.version != build._BUILD or sys.implementation.name != 'cpython'
            or sysconfig.get_config_var('SOABI') != 'cpython-312-x86_64-linux-gnu'
            or runtime._cold_graph_row_storage is not _ORIGINAL
            or runtime.require is not _REQUIRE or runtime.codec.require is not _LEAF
            or any(fn.__code__ is not code for fn, code in zip((_ORIGINAL, _REQUIRE, _LEAF), _CODES, strict=True))
            or any(getattr(builtins, name) is not value for name, value in _BUILTINS.items())
            or any(runtime.__dict__.get(name, value) is not value for name, value in _BUILTINS.items())):
        return None
    try:
        path = Path(path).resolve(strict=True)
        proof = json.loads(path.with_suffix(path.suffix + '.json').read_text())
        source = Path(__file__).with_name('_cold_row_native_impl.c')
        if any(hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != expected
                for name, expected in _SOURCES.items()):
            return None
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        include = Path(sysconfig.get_path('include'))
        sanitizer = proof['sanitizer']
        if (sanitizer not in (None, 'address') or proof['python'] != build._BUILD
                or proof['soabi'] != sysconfig.get_config_var('SOABI')
                or proof['source_sha256'] != digest or proof['headers'] != build._HEADERS
                or any(hashlib.sha256((include / name).read_bytes()).hexdigest() != value
                    for name, value in build._HEADERS.items())
                or proof['executable_sha256'] != build._EXECUTABLE
                or hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest() != build._EXECUTABLE
                or proof['binary_sha256'] != _BINARIES[sanitizer]
                or hashlib.sha256(path.read_bytes()).hexdigest() != _BINARIES[sanitizer]
                or proof['output'] != str(path)):
            return None
        command = ['/usr/bin/cc', '-shared', '-fPIC', '-O1' if sanitizer else '-O2',
            '-Wall', '-Wextra', '-Werror', '-DSIM2ACT_VISITOR_SOURCE_SHA="' + digest + '"',
            '-I' + str(include), str(source), '-o', str(path)]
        if sanitizer:
            command += ['-g', '-fsanitize=address', '-fno-omit-frame-pointer']
        if proof['command'] != command:
            return None
        for name, expected in _SQL.items():
            module = sys.modules.get(name)
            if type(module) is not ModuleType or hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != expected:
                return None
        kinds = (
            ('sqlalchemy.engine.row', 'RowMapping', runtime._ColdGraphRowMapping),
            ('sqlalchemy.engine.cursor', 'CursorResultMetaData', runtime._ColdGraphCursorMeta),
            ('sqlalchemy.engine.result', 'SimpleResultMetaData', runtime._ColdGraphSimpleMeta),
            ('sqlalchemy.sql.elements', 'quoted_name', runtime._ColdGraphQuotedName))
        if any(getattr(sys.modules[name], attribute) is not kind for name, attribute, kind in kinds):
            return None
        base = sys.modules['sqlalchemy.cyextension.resultproxy'].BaseRow
        if any(getattr_static(runtime._ColdGraphRowMapping, name) is not vars(base)[name]
                for name in ('_parent', '_data', '_key_to_index')):
            return None
        for kind in (runtime._ColdGraphCursorMeta, runtime._ColdGraphSimpleMeta):
            member = getattr_static(kind, '_keys')
            if (type(member) is not MemberDescriptorType or member.__objclass__ is not kind
                    or member.__name__ != '_keys'):
                return None
        if sanitizer and not build._asan_runtime_mapped():
            return None
        spec = importlib.util.spec_from_file_location('_cold_row_native_impl', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.build_identity() != (digest, build._BUILD):
            return None
        entry = module.make_reader(_ORIGINAL, runtime.require, runtime.codec.require,
            runtime._ColdGraphRowMapping, runtime._ColdGraphCursorMeta,
            runtime._ColdGraphSimpleMeta, runtime._ColdGraphQuotedName)
        return None if entry is None else _OfflineReader(module, entry)
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        return None

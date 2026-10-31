"""Explicit offline candidate, never selected by production routing.

The backend must be built and passed explicitly. There is no backend discovery,
automatic installation, cached graph or native-failure fallback. Recursion
resource thresholds still require qualification before any runtime substitution.
"""

import hashlib
import importlib.util
import json
import os
import stat
import sys
import sysconfig
from pathlib import Path
from types import BuiltinFunctionType, ModuleType

from pydantic import BaseModel

from . import natural_live_admission as gate

_PYTHON_STORAGE = gate._trial_typed_storage
_REQUIRE = gate.require
_ROOTS = gate._trial_typed_classes
_NESTED = gate._trial_typed_nested_classes
_ISSUER = object()
_BUILD = '3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]'
_EXECUTABLE = 'fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7'
_ASAN_LINK = Path('/usr/lib/gcc/x86_64-linux-gnu/14/libasan.so')
_ASAN_REAL = Path('/usr/lib/x86_64-linux-gnu/libasan.so.8.0.0')
_ASAN_SHA256 = 'f5c57422d80671ced6cffe350f92c8ab9bec23fda9b155658aac630d2bc2a240'
_BINARIES = {
    None: 'ce91773ea4c788483c877c60ad96985f0f712cee990724b8584b50a7b29ca71f',
    'address': '3cca77d9b8eecc2d8f583bff44bd7a80be914011a9952c038c10a8a4d3d68b89',
}
_HEADERS = {
    'Python.h': '729ef157f6026e6e1b3104593f87dddc597c3b83b60c7c2965878c62a56c6f7d',
    'pyconfig.h': '3a9546822f3c1b28caaedabf93cc862215f4cbff25a8d209edc08a21b908beba',
    'cpython/pystate.h': '11494795dd1d6945fbf8036af5ccf247463e94d405a760924a1c78f78ebfc4ec',
    'internal/pycore_ceval.h': '1af22b50c9ececfc4c3a5f37ecb70cc1c0eefad5a2656e6e22fc088cae54e226',
}


def project(backend, expected, model):
    from .contracts import BranchCondition, WorkflowStep

    # Unknown helper implementations retain the original Python path. This is
    # checked before native work; exceptions from native work propagate once.
    if (gate._trial_typed_storage is not _PYTHON_STORAGE or gate.require is not _REQUIRE
            or gate._trial_typed_classes is not _ROOTS
            or gate._trial_typed_nested_classes is not _NESTED):
        return gate._trial_typed_storage(expected, model)
    roots, allowed = gate._trial_typed_classes(), gate._trial_typed_nested_classes()
    return backend.project(expected, model, roots, allowed, BranchCondition, WorkflowStep,
        gate.require)


class _QualifiedBackend:
    """Build identity only is retained, never an input eligibility/PASS result."""

    __slots__ = ('module', 'identity', 'entry', 'native_calls', 'python_calls', 'reasons', 'last', '_issued', '_probe')

    def __init__(self, module, identity, *, _issuer):
        if _issuer is not _ISSUER:
            raise ValueError('Native backend must come from the verified local build loader')
        self._issued = _issuer
        self._probe = module.stack_ready
        self.module, self.identity = module, identity
        self.entry = module.select_project
        self.native_calls = self.python_calls = 0
        self.reasons = {}
        self.last = None

    def select(self, expected, model):
        """Return a dict or None; caller must run legacy AFTER this frame exits."""
        from .contracts import BranchCondition, WorkflowStep

        if (type(self.module) is not ModuleType or vars(self.module).get('select_project') is not self.entry
                or type(self.entry) is not BuiltinFunctionType or self.entry.__self__ is not self.module
                or gate._trial_typed_storage is not _PYTHON_STORAGE or gate.require is not _REQUIRE
                or gate._trial_typed_classes is not _ROOTS or gate._trial_typed_nested_classes is not _NESTED
                or sys.version != _BUILD):
            self.python_calls += 1
            self.last = dict(reason='helper-or-backend-identity', native=False)
            self.reasons['helper-or-backend-identity'] = self.reasons.get('helper-or-backend-identity', 0) + 1
            return None
        roots, allowed = gate._trial_typed_classes(), gate._trial_typed_nested_classes()
        reply = self.entry(expected, model, roots, allowed, BranchCondition, WorkflowStep,
            gate.require, BaseModel, type(BaseModel))
        result, reason, visits, work, need, py_left, c_left, chosen = reply
        self.last = dict(reason=reason, visits=visits, work=work, stack_need=need,
            python_remaining=py_left, c_remaining=c_left, native=bool(chosen))
        self.reasons[reason] = self.reasons.get(reason, 0) + 1
        self.native_calls += chosen
        self.python_calls += not chosen
        return result


_SELECT = _QualifiedBackend.select
_PROBE_SLOT = vars(_QualifiedBackend)['_probe']


def select_candidate(handle, expected, model):
    """Fixed internal entry: unknown/forged handles cannot dispatch callbacks."""
    if type(handle) is not _QualifiedBackend or vars(_QualifiedBackend).get('select') is not _SELECT:
        return None
    try:
        if handle._issued is not _ISSUER:
            return None
    except AttributeError:
        return None
    return _SELECT(handle, expected, model)


def _asan_runtime_mapped():
    """Recognize only this installed runtime, including its loader spelling.

    /proc reports the canonical pathname when LD_PRELOAD names the GCC symlink.
    Path text alone is insufficient: require the pinned file and an executable
    mapping of its device/inode. This neither searches for nor loads a library.
    """
    try:
        if _ASAN_LINK.resolve(strict=True) != _ASAN_REAL:
            return False
        with _ASAN_REAL.open('rb') as library:
            info = os.fstat(library.fileno())
            # Reading the library may itself update atime under relatime.
            stable = lambda item: (item.st_dev, item.st_ino, item.st_mode,
                item.st_size, item.st_mtime_ns, item.st_ctime_ns)
            if (not stat.S_ISREG(info.st_mode) or not info.st_ino
                    or hashlib.file_digest(library, 'sha256').hexdigest() != _ASAN_SHA256
                    or stable(os.fstat(library.fileno())) != stable(info)):
                return False
        for line in Path('/proc/self/maps').read_text().splitlines():
            parts = line.split(None, 5)
            if (len(parts) != 6 or parts[5] not in (str(_ASAN_REAL), str(_ASAN_LINK))
                    or 'x' not in parts[1]):
                continue
            device = parts[3].split(':')
            if (len(device) == 2 and int(device[0], 16) == os.major(info.st_dev)
                    and int(device[1], 16) == os.minor(info.st_dev)
                    and int(parts[4]) == info.st_ino):
                return True
        return False
    except (OSError, ValueError):
        return False


def load_candidate(path):
    """Explicit local build receipt, source, binary, interpreter and ABI witness.

    Unknown provenance returns None before importing an extension. This is a
    repository build/integrity contract, not a sandbox for arbitrary C binaries.
    Nothing auto-discovers, installs, enables or grants this candidate.
    """
    if (sys.implementation.name != 'cpython' or sys.version != _BUILD
            or sysconfig.get_config_var('SOABI') != 'cpython-312-x86_64-linux-gnu'):
        return None
    try:
        path = Path(path).resolve(strict=True)
        proof = json.loads(path.with_suffix(path.suffix + '.json').read_text())
        source = Path(__file__).with_name('_cold_typed_native_impl.c')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        include = Path(sysconfig.get_path('include'))
        if (proof['python'] != _BUILD or proof['soabi'] != sysconfig.get_config_var('SOABI')
                or proof['source_sha256'] != digest or proof['headers'] != _HEADERS
                or any(hashlib.sha256((include / name).read_bytes()).hexdigest() != value
                    for name, value in _HEADERS.items())
                or proof['executable_sha256'] != _EXECUTABLE
                or hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest() != _EXECUTABLE
                or proof['binary_sha256'] != _BINARIES.get(proof['sanitizer'])
                or proof['binary_sha256'] != hashlib.sha256(path.read_bytes()).hexdigest()
                or proof['output'] != str(path) or proof['sanitizer'] not in (None, 'address')):
            return None
        expected_command = ['/usr/bin/cc', '-shared', '-fPIC',
            '-O1' if proof['sanitizer'] else '-O2', '-Wall', '-Wextra', '-Werror',
            '-DSIM2ACT_VISITOR_SOURCE_SHA="' + digest + '"', '-I' + str(include),
            str(source), '-o', str(path)]
        if proof['sanitizer']:
            expected_command += ['-g', '-fsanitize=address', '-fno-omit-frame-pointer']
        if proof['command'] != expected_command:
            return None
        if proof['sanitizer'] == 'address' and not _asan_runtime_mapped():
            # Loading an ASAN DSO without the runtime preloaded can abort the
            # interpreter; an exact source digest alone does not qualify it.
            return None
        spec = importlib.util.spec_from_file_location('_cold_typed_native_impl', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        identity = module.build_identity()
        if identity != (digest, _BUILD, 288, 28, 36):
            return None
        return _QualifiedBackend(module, identity, _issuer=_ISSUER)
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        return None

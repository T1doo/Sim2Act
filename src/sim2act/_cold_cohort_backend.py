"""Complete fresh typed-cohort candidate, disabled pending differential review.

No Graph, authority, input or PASS is cached. Only import-time code metadata is
retained. Each successful local selection still scans/copies current model/raw
data, uses the original serializer once, then compares its result to LIVE raw.
"""
import builtins
import gc
import hashlib
import sys
import sysconfig
from inspect import getattr_static
from pathlib import Path
from types import BuiltinFunctionType, FunctionType

from pydantic import BaseModel
from pydantic_core import SchemaSerializer

from . import natural_live_admission as gate
from . import _cold_typed_stream as stream
from .contracts import BranchCondition, WorkflowStep
from .errors import DomainError

try:
    from . import _cold_typed_cohort as native
except ImportError:
    native = None

ENABLED = False
_ROOTS = gate._trial_typed_classes()
_ALLOWED = gate._trial_typed_nested_classes()
_SELECT = None if native is None else native.first_compare
_CURRENT = None if native is None else native.current
_PROBE = None if native is None else native.stack_ready
_STANDARD_DUMP = BaseModel.model_dump
_READY = False


def _functions_in(value, found, seen):
    if id(value) in seen:
        return
    seen.add(id(value))
    if type(value) is FunctionType:
        found[id(value)] = value
    elif type(value) is dict:
        for child in value.values():
            _functions_in(child, found, seen)
    elif type(value) is tuple or type(value) is list:
        for child in value:
            _functions_in(child, found, seen)


def _configure():
    if native is None:
        return False
    paths = ('_cold_typed_cohort.c', '_cold_typed_native_impl.c', '_raw_snapshot.c', '_cold_cohort_backend.py')
    if native.SOURCE_SHA256 != hashlib.sha256(b''.join(
            Path(__file__).with_name(name).read_bytes() for name in paths)).hexdigest():
        return False
    if (sys.implementation.name != 'cpython'
            or sys.version != '3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]'
            or sysconfig.get_config_var('SOABI') != 'cpython-312-x86_64-linux-gnu'
            or native.build_identity() != (native.SOURCE_SHA256, sys.version, 288, 28, 36)):
        return False
    # Gate functions already have an import-time independent code registry.
    # Do not mint a new witness from pre-mutated helper implementations.
    if type(gc.callbacks) is not list or gc.callbacks:
        return False
    gate._source_owned_code.current()
    from . import _cold_policy_segment as schema_code
    for module in (gate,stream):
        namespace=vars(module)
        if any(namespace.get(name) is not value for name,value in module._COHORT_MODULE_BINDINGS):
            return False
        if any(namespace.get(name,vars(builtins).get(name)) is not value
                for name,value in module._COHORT_BUILTIN_ROLES):
            return False
    for fn, code, defaults, kwdefaults, items in stream._COHORT_PRIMITIVE_CODE:
        if (fn.__code__ is not code or fn.__defaults__ is not defaults
                or fn.__kwdefaults__ is not kwdefaults
                or len(kwdefaults or {}) != len(items)
                or any(key is not old_key or value is not old_value
                    for (key,value),(old_key,old_value) in zip(
                        (kwdefaults or {}).items(),items,strict=True))):
            return False
    classes = {}
    functions = {}
    for kind in (*_ALLOWED, stream._Comparison):
        for cls in type.__getattribute__(kind, '__mro__'):
            if type.__getattribute__(cls, '__flags__') & (1 << 9):
                classes[id(cls)] = cls
        for cls in type.__getattribute__(type(kind), '__mro__'):
            classes[id(cls)] = cls
    for kind in _ALLOWED:
        if not schema_code._fixed_schema(kind):
            return False
        namespace = type.__getattribute__(kind, '__dict__')
        serializer = namespace.get('__pydantic_serializer__')
        if (getattr_static(kind, 'model_dump') is not _STANDARD_DUMP
                or type(serializer) is not SchemaSerializer
                or SchemaSerializer.__reduce__(serializer)[1][0]
                    is not namespace.get('__pydantic_core_schema__')):
            return False
        _functions_in(namespace.get('__pydantic_core_schema__'), functions, set())
    # The class namespaces/MROs are pinned completely, but unused metaclass
    # constructors/hash/validation methods are not callees of this bridge.
    for name in ('require', '_trial_typed_storage', '_trial_typed_classes',
                 '_trial_typed_nested_classes', '_trial_typed_equal',
                 '_trial_pure_data', '_trial_pure_mapping'):
        value = vars(gate)[name]
        functions[id(value)] = value
    for value in vars(stream).values():
        if type(value) is FunctionType and value.__module__ == stream.__name__:
            functions[id(value)] = value
    for value in vars(stream._Comparison).values():
        if type(value) is FunctionType:
            functions[id(value)] = value
    for value in tuple(globals().values()):
        if type(value) is FunctionType and value.__module__ == __name__:
            functions[id(value)] = value
    functions[id(_STANDARD_DUMP)] = _STANDARD_DUMP
    # A closure can carry arbitrary mutable context. Unsupported configurations
    # keep the original implementation; no closure contents are called here.
    if any(fn.__closure__ is not None for fn in functions.values()):
        return False
    bindings = {}
    for fn in functions.values():
        names = set()
        codes = [fn.__code__]
        while codes:
            code = codes.pop()
            names.update(code.co_names)
            codes.extend(child for child in code.co_consts if type(child) is type(code))
        for name in names:
            current = fn.__globals__.get(name, fn.__builtins__.get(name))
            bindings[id(fn.__globals__), name] = (
                fn.__globals__, fn.__builtins__, name, current)
    for name in ('_RAW_COPY', '_RAW_EQUAL', '_RAW_UNSUPPORTED', 'require',
                 '_trial_typed_equal', '_trial_typed_classes', '_trial_typed_nested_classes'):
        bindings[id(vars(gate)), name] = (vars(gate), vars(builtins), name, vars(gate)[name])
    record = (tuple((fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__,
                    tuple((fn.__kwdefaults__ or {}).items())) for fn in functions.values()),
        tuple(bindings.values()),
        tuple((cls, type(cls), type.__getattribute__(cls, '__mro__'),
               tuple(type.__getattribute__(cls, '__dict__').items())) for cls in classes.values()),
        (vars(gc), gc.callbacks))
    native.configure(record)
    return True


def try_triple(expected, model, raw):
    """True when completed; None means original-frame fallback before work."""
    current, select, probe = _CURRENT, _SELECT, _PROBE
    if (type(probe) is not BuiltinFunctionType or probe.__self__ is not native
            or probe() is not True):
        return None
    if (not _READY or type(current) is not BuiltinFunctionType
            or type(select) is not BuiltinFunctionType
            or current.__self__ is not native or select.__self__ is not native
            or current() is not True):
        return None
    matched = select(expected, model, _ROOTS, _ALLOWED, BranchCondition, WorkflowStep,
        gate.require, BaseModel, type(BaseModel), raw)
    if matched is None:
        return None
    # Native execution failures propagate once. Late eligibility changes must
    # reject, not replay a producer or reinterpret UNSUPPORTED as success.
    if current() is not True:
        raise DomainError('VERSION_CONFLICT', 'Typed cohort configuration changed during projection')
    gate.require(matched,
        'Typed trial storage changed after its complete raw proof')
    value = expected.model_dump(model, warnings=False)
    if current() is not True:
        raise DomainError('VERSION_CONFLICT', 'Typed cohort configuration changed during serialization')
    equal = gate._RAW_EQUAL(value, raw)
    if equal is gate._RAW_UNSUPPORTED:
        equal = stream._Comparison(_ALLOWED).equal(value, raw, typed=False)
    gate.require(equal, 'Typed trial fact changed after its complete raw proof')
    return True


_READY = True  # The immutable witness records the final ready-state value.
try:
    _READY = _configure()
except (DomainError, OSError, ValueError):
    _READY = False

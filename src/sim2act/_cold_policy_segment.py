"""Two fixed pure policy segments, bracketed by the caller's complete pins.

No permission, remembered PASS, reentrancy state or general guard bypass. Each
call copies its complete consumed inputs without user copy/serializer hooks.
Only the fixed original policy cores consume those private copies. SQL, clocks,
source resolution, new graph roots and publication remain in the coordinator.
"""

import copy as _copy
import hashlib
import math
from inspect import getattr_static
from io import BytesIO
from pickle import PickleBuffer, Pickler
from typing import Any

from pydantic import BaseModel, ValidationError
from pydantic_core import SchemaSerializer, SchemaValidator
from sqlalchemy.engine import RowMapping

from . import delivery_graph_apps as _pair_graph
from . import production_trial_policy as policy
from ._cold_typed_stream import _Comparison
from .errors import DomainError
from .natural_live_admission import (
    _trial_pure_mapping,
    _trial_typed_nested_classes,
    require,
)
from .pa_material_bindings import Metadata as _PairMetadata
from .text_workflows import RunScopeInput as _PairRunScope

_UNSUITABLE = object()
_VALIDATE = getattr_static(BaseModel, 'model_validate')
_INIT = getattr_static(BaseModel, '__init__')
_POST_INIT = getattr_static(BaseModel, 'model_post_init')
_REQUIREMENTS = policy._requirements
_RUN_CHECK = policy._run_check_from_facts


def _schema_shape(value, keep, active=None):
    """Code-configuration witness, never a value/validation/PASS cache.

    Read the complete live schema each time, including Python callback objects.
    Retained bootstrap leaves prevent id reuse. Compare only built-in tuples and
    scalars, never callback equality/repr/reduce. A rebuilt or mutated schema is
    ineligible, rather than assumed pure because its validator is a C object.
    """
    if active is None:
        active = set()
    kind = type(value)
    if any(kind is item for item in (str, int, float, bool, type(None))):
        return kind.__name__, value
    if kind is dict or kind is list or kind is tuple:
        require(id(value) not in active)
        active.add(id(value))
        if kind is dict:
            require(all(type(key) is str for key in value))
            result = ('dict', tuple((key, _schema_shape(child, keep, active))
                for key, child in dict.items(value)))
        else:
            result = (kind.__name__, tuple(_schema_shape(child, keep, active) for child in value))
        active.remove(id(value))
        return result
    if keep is not None:
        keep.append(value)
    return 'code-object', id(value)


def _schema_matches(value, expected, active=None):
    """Fresh full schema witness without rebuilding a second shape tree.

    The expected shape is bootstrap-owned. Visit every live child even after a
    mismatch so the original complete key/cycle gate and its order remain.
    No completed/PASS memo, user equality or serializer callback is used.
    """
    if active is None:
        active = set()
    kind = type(value)
    shape = expected if type(expected) is tuple and len(expected) == 2 else None
    if kind is str or kind is int or kind is float or kind is bool or kind is type(None):
        return (shape is not None and shape[0] == kind.__name__
            and (value is shape[1] or value == shape[1]))
    if kind is dict or kind is list or kind is tuple:
        identity = id(value)
        require(identity not in active)
        active.add(identity)
        children = shape[1] if shape is not None and shape[0] == kind.__name__ else ()
        matching = shape is not None and shape[0] == kind.__name__ and len(value) == len(children)
        if kind is dict:
            require(all(type(key) is str for key in value))
            for index, (key, child) in enumerate(dict.items(value)):
                prior = children[index] if index < len(children) else None
                if prior is None or key != prior[0]:
                    matching = False
                same = _schema_matches(child, None if prior is None else prior[1], active)
                matching = same and matching
        else:
            for index, child in enumerate(value):
                same = _schema_matches(child, children[index] if index < len(children) else None, active)
                matching = same and matching
        active.remove(identity)
        return matching
    return shape is not None and shape[0] == 'code-object' and id(value) == shape[1]


_SCHEMA_MATCHER = _schema_matches


# Fixed local schema/code configuration at module bootstrap, not permissions or
# input results. All live schema, serializer and validator metadata are reread
# for every private snapshot. This does not defend arbitrary process code edits.
_CODE_LEAVES: list[Any] = []
_PAIR_CHECKED = _pair_graph.checked
_PAIR_LOOKUP = _pair_graph.lookup
_PAIR_CHECKED_CODE = _PAIR_CHECKED.__code__
_PAIR_CONFLICT = _pair_graph.conflict
_PAIR_DEEPCOPY = _copy.deepcopy
_PAIR_KEEP_ALIVE = _copy._keep_alive
_PAIR_COPY_TYPES = (dict, list, tuple, str, int, float, bool, bytes, type(None))
_PAIR_COPY_DISPATCH = tuple((kind, _copy._deepcopy_dispatch.get(kind)) for kind in _PAIR_COPY_TYPES)
_PAIR_COPY_DISPATCH_TABLE = _copy._deepcopy_dispatch
_PAIR_FINGERPRINT = _pair_graph.fingerprint
_PAIR_STANDARD_DUMP = BaseModel.model_dump
_PAIR_CODE = tuple((fn, getattr(fn, '__code__', None)) for fn in
    (_PAIR_CHECKED, _PAIR_LOOKUP, _PAIR_CONFLICT, _PAIR_FINGERPRINT, _PAIR_DEEPCOPY, _PAIR_KEEP_ALIVE,
     _PAIR_STANDARD_DUMP, *[fn for _, fn in _PAIR_COPY_DISPATCH if fn is not None]))


def _pair_builtin_values(value):
    """Only private builtins may reach deepcopy; no model or foreign hooks."""
    pending, done = [value], set()
    while pending:
        value = pending.pop()
        kind = type(value)
        if any(kind is item for item in (str, int, float, bool, bytes, type(None))):
            continue
        if not any(kind is item for item in (dict, list, tuple)):
            return False
        if id(value) in done:
            continue
        done.add(id(value))
        if kind is dict:
            if not all(type(key) is str for key in value):
                return False
            pending.extend(dict.values(value))
        else:
            pending.extend(value)
    return True


def _persisted_pair_value(rows, expected, preflight, pair_require, *, pin):
    """SQL is already post-pinned; run only the fixed private pair arithmetic.

    Unknown metadata/code/representation returns to the original path before
    any checked/parser core runs. No result/PASS survives this invocation.
    """
    if (_fixed_schema is not _PAIR_SCHEMA_QUALIFIER
            or _fixed_schema.__code__ is not _PAIR_SCHEMA_QUALIFIER_CODE
            or _snapshot is not _PAIR_SNAPSHOT
            or _snapshot.__code__ is not _PAIR_SNAPSHOT_CODE
            or not _fixed_schema(expected)
            or any(getattr(fn, '__code__', None) is not code for fn, code in _PAIR_CODE)
            or _PAIR_CHECKED.__globals__.get('copy') is not _copy
            or any(getattr_static(kind, 'model_dump') is not _PAIR_STANDARD_DUMP
                or not _fixed_schema(kind)
                or type(type.__getattribute__(kind, '__pydantic_serializer__')) is not SchemaSerializer
                or SchemaSerializer.__reduce__(type.__getattribute__(kind, '__pydantic_serializer__'))[1][0]
                    is not type.__getattribute__(kind, '__pydantic_core_schema__')
                for kind, *_ in _SCHEMAS)
            or _pair_graph.checked is not _PAIR_CHECKED
            or _pair_graph.lookup is not _PAIR_LOOKUP
            or _PAIR_CHECKED.__code__ is not _PAIR_CHECKED_CODE
            or _pair_graph.conflict is not _PAIR_CONFLICT
            or _pair_graph.fingerprint is not _PAIR_FINGERPRINT
            or _copy.deepcopy is not _PAIR_DEEPCOPY
            or _copy._keep_alive is not _PAIR_KEEP_ALIVE
            or _copy._deepcopy_dispatch is not _PAIR_COPY_DISPATCH_TABLE
            or any(_copy._deepcopy_dispatch.get(kind) is not function
                for kind, function in _PAIR_COPY_DISPATCH)):
        return _UNSUITABLE
    owned = _snapshot(rows)
    if owned is _UNSUITABLE or not _pair_builtin_values(owned):
        return _UNSUITABLE
    pair_require(all(owned), 'Independent text logic seals missing')
    values = []
    for row in owned:
        preflight(row['snapshot'])
        values.append(_PAIR_CHECKED(row))
    left, right = values
    pair_require(set(left) == {'request', 'response'})
    pair_require(_PAIR_FINGERPRINT(left) == _PAIR_FINGERPRINT(right))
    try:
        body = expected.model_validate(left['request'])
    except (ValidationError, KeyError, TypeError, ValueError):
        raise DomainError('VERSION_CONFLICT', 'Malformed persisted DeliveryGraph binding') from None
    request_fp = _PAIR_FINGERPRINT(expected.model_dump(body))
    for row in owned:
        pair_require(row['request_fingerprint'] == request_fp)
    # Late complete graph boundary includes all work above and precedes use.
    pin()
    return body, left['response']


_SCHEMAS = tuple((kind, type.__getattribute__(kind, '__pydantic_core_schema__'),
    _schema_shape(type.__getattribute__(kind, '__pydantic_core_schema__'), _CODE_LEAVES),
    type.__getattribute__(kind, '__pydantic_validator__'),
    type.__getattribute__(kind, '__pydantic_serializer__'))
    for kind in (*_trial_typed_nested_classes(), _PairMetadata, _PairRunScope))


def _schema_identity_marker(*args):
    raise TypeError('Schema witnesses must never be loaded')


class _SchemaPickler(Pickler):
    def reducer_override(self, value):
        if value is _schema_identity_marker:
            return NotImplemented
        # Unknown leaves are code identities, never their serializers/equality.
        return _schema_identity_marker, (id(value),)


def _schema_bytes(value):
    output = BytesIO()
    encoder = _SchemaPickler(output, protocol=5)
    # Visit every occurrence of a shared mutable subtree, as the old matcher
    # does. This is a fresh encoding, without a completed-value/PASS memo.
    encoder.fast = True
    encoder.dump(value)
    return output.getvalue()


def _has_nan(value):
    if type(value) is float:
        return math.isnan(value)
    return type(value) is tuple and any(_has_nan(v) for v in value)


# Bootstrap code-configuration pins only. NaN identity semantics and any exact
# builtin that pickle would encode by value but our schema treats as an opaque
# code leaf retain the complete old matcher. Retained leaves prevent id reuse.
_SCHEMA_PINS = tuple(None if _has_nan(entry[2]) or any(
    type(v) in (bytes, bytearray, set, frozenset, PickleBuffer) for v in _CODE_LEAVES)
    else hashlib.sha256(_schema_bytes(entry[1])).digest() for entry in _SCHEMAS)


def _schema_current(trusted):
    pin = next((pin for entry, pin in zip(_SCHEMAS, _SCHEMA_PINS, strict=True)
        if entry is trusted), None)
    if pin is not None:
        try:
            if hashlib.sha256(_schema_bytes(trusted[1])).digest() == pin:
                return True
        except (ValueError, RecursionError):
            pass  # The original complete key/cycle gate owns rejection.
    return _schema_matches(trusted[1], trusted[2])


_SCHEMA_CURRENT = _schema_current
_SCHEMA_BYTES = _schema_bytes
_SCHEMA_ENCODER = _SchemaPickler
_SCHEMA_REDUCER = getattr_static(_SchemaPickler, 'reducer_override')
_SCHEMA_MARKER = _schema_identity_marker


def _fixed_schema(kind):
    namespace = type.__getattribute__(kind, '__dict__')
    validator = namespace.get('__pydantic_validator__')
    trusted = next((entry for entry in _SCHEMAS if entry[0] is kind), None)
    return (trusted is not None and namespace.get('__pydantic_core_schema__') is trusted[1]
        and _schema_current is _SCHEMA_CURRENT and _schema_bytes is _SCHEMA_BYTES
        and _SchemaPickler is _SCHEMA_ENCODER
        and getattr_static(_SchemaPickler, 'reducer_override') is _SCHEMA_REDUCER
        and _schema_identity_marker is _SCHEMA_MARKER
        and _schema_matches is _SCHEMA_MATCHER and _schema_current(trusted)
        and validator is trusted[3] and namespace.get('__pydantic_serializer__') is trusted[4]
        and getattr_static(kind, 'model_validate') is _VALIDATE
        and getattr_static(kind, '__init__') is _INIT
        and getattr_static(kind, 'model_post_init') is _POST_INIT
        and type(validator) is SchemaValidator
        and SchemaValidator.__reduce__(validator)[1][0]
            is namespace.get('__pydantic_core_schema__'))


_PAIR_SCHEMA_QUALIFIER = _fixed_schema
_PAIR_SCHEMA_QUALIFIER_CODE = _fixed_schema.__code__

def _snapshot(values):
    """Invocation-owned exact storage, including field sets and DAG sharing.

    This is not validation or a new acceptance limit. Unsupported representation
    or modified schema hooks select the old path *before* either core executes.
    Existing full guards and original policy validation still own rejection.
    RowMapping copies only policy-visible columns; it adds no hidden-data proof.
    Existing RowMappings in guard.inputs retain their original full pin.
    """
    comparison = _Comparison(_trial_typed_nested_classes())
    active: set[int] = set()
    completed: dict[int, tuple[Any, Any]] = {}

    def copy(value):
        kind = type(value)
        if any(kind is item for item in (str, int, float, bool, bytes, type(None))):
            return value
        require(any(kind is item for item in (dict, RowMapping, list, tuple))
            or any(kind is allowed for allowed in comparison.allowed))
        identity = id(value)
        require(identity not in active, 'Cyclic private policy snapshot')
        if identity in completed:
            original, result = completed[identity]
            require(original is value)
            return result
        active.add(identity)
        if kind is dict or kind is RowMapping:
            raw = _trial_pure_mapping(value)
            result = {key: copy(child) for key, child in dict.items(raw)}
        elif kind is list:
            result = [copy(child) for child in value]
        elif kind is tuple:
            result = tuple(copy(child) for child in value)
        else:
            raw, _ = comparison.model_fields(value)
            # No model_construct/default/validator/post-init/deepcopy dispatch.
            # Copy ALL stored fields, including the two optional None fields.
            result = object.__new__(kind)
            object.__setattr__(result, '__dict__', copy(raw))
            object.__setattr__(result, '__pydantic_fields_set__',
                set(object.__getattribute__(value, '__pydantic_fields_set__')))
            object.__setattr__(result, '__pydantic_extra__', None)
            object.__setattr__(result, '__pydantic_private__', None)
        active.remove(identity)
        completed[identity] = value, result
        return result

    try:
        result = copy(values)
        if (not comparison.standard_serializers()
                or not all(_fixed_schema(type(model))
                    for model, _, _ in comparison.models.values())
                or not all(_fixed_schema(kind) for kind in (
                    policy.RunCheck, policy.evidence.EvidenceRequirements, policy.budget.Scope))):
            return _UNSUITABLE
        return result
    except DomainError:
        return _UNSUITABLE


_PAIR_SNAPSHOT = _snapshot
_PAIR_SNAPSHOT_CODE = _snapshot.__code__

def _requirements_value(user, contract, key, *, pin):
    """Fixed requirements projection; no source/authorization/clock is included."""
    pin()
    values = _snapshot((user, contract, key))
    if values is _UNSUITABLE or policy._requirements is not _REQUIREMENTS:
        return policy._requirements(user, contract, key, _guard=pin)
    result = _REQUIREMENTS(*values)
    # Only success reaches this pin. An original core error is never overwritten
    # by a finally-pin, replayed, normalized, or converted to a late fallback.
    pin()
    return result


def _run_check_value(original, expected, approval, phase, run, at, stage,
                     run_id, version, fence, worker_id, *, pin):
    """Fixed RunCheck construction using the already sampled original `at`."""
    pin()
    values = _snapshot((original, expected, approval, phase, run, at, stage,
                        run_id, version, fence, worker_id))
    if values is _UNSUITABLE or policy._run_check_from_facts is not _RUN_CHECK:
        return policy._run_check_from_facts(original, expected, approval, phase, run,
            at, stage, run_id, version, fence, worker_id, _guard=pin)
    result = _RUN_CHECK(*values)
    pin()
    return result


# Import-time source comparison/schema/class configuration only. These records
# contain no runtime model instance, graph, permission or validation result.
from . import _cold_source_packet as _source_owned_code
from . import _cold_typed_stream as _cohort_stream
_source_classes={}
for _source_kind in (_Comparison,*(entry[0] for entry in _SCHEMAS
        if entry[0].__name__ in ('Slot','ReservationIdentity','Outcome','Capture','BodyArchive'))):
    for _source_base in (*_source_kind.__mro__,*type(_source_kind).__mro__):
        if _source_base.__flags__ & (1<<9):_source_classes[id(_source_base)]=_source_base
_source_owned_code.register(5,globals(),('_fixed_schema','_schema_current','_schema_bytes',
    '_schema_matches','_schema_shape','_schema_identity_marker'),tuple(_source_classes.values()),
    ('_SCHEMAS','_SCHEMA_CURRENT','_SCHEMA_BYTES','_SCHEMA_ENCODER','_SCHEMA_REDUCER',
     '_SCHEMA_MARKER','_SCHEMA_MATCHER','_Comparison'),
    constant_helpers=((vars(_cohort_stream),('_COHORT_PRIMITIVE_CODE',
        '_COHORT_BUILTIN_ROLES','_COHORT_MODULE_BINDINGS')),))
del _source_classes,_source_kind,_source_base

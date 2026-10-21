"""Two fixed pure policy segments, bracketed by the caller's complete pins.

No permission, remembered PASS, reentrancy state or general guard bypass. Each
call copies its complete consumed inputs without user copy/serializer hooks.
Only the fixed original policy cores consume those private copies. SQL, clocks,
source resolution, new graph roots and publication remain in the coordinator.
"""

from inspect import getattr_static
from typing import Any

from pydantic import BaseModel
from pydantic_core import SchemaValidator
from sqlalchemy.engine import RowMapping

from . import production_trial_policy as policy
from ._cold_typed_stream import _Comparison
from .errors import DomainError
from .natural_live_admission import (
    _trial_pure_mapping,
    _trial_typed_nested_classes,
    require,
)

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
_SCHEMAS = tuple((kind, type.__getattribute__(kind, '__pydantic_core_schema__'),
    _schema_shape(type.__getattribute__(kind, '__pydantic_core_schema__'), _CODE_LEAVES),
    type.__getattribute__(kind, '__pydantic_validator__'),
    type.__getattribute__(kind, '__pydantic_serializer__'))
    for kind in _trial_typed_nested_classes())


def _fixed_schema(kind):
    namespace = type.__getattribute__(kind, '__dict__')
    validator = namespace.get('__pydantic_validator__')
    trusted = next((entry for entry in _SCHEMAS if entry[0] is kind), None)
    return (trusted is not None and namespace.get('__pydantic_core_schema__') is trusted[1]
        and _schema_matches is _SCHEMA_MATCHER and _schema_matches(trusted[1], trusted[2])
        and validator is trusted[3] and namespace.get('__pydantic_serializer__') is trusted[4]
        and getattr_static(kind, 'model_validate') is _VALIDATE
        and getattr_static(kind, '__init__') is _INIT
        and getattr_static(kind, 'model_post_init') is _POST_INIT
        and type(validator) is SchemaValidator
        and SchemaValidator.__reduce__(validator)[1][0]
            is namespace.get('__pydantic_core_schema__'))


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

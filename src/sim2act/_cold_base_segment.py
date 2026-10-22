"""One invocation's fixed native _base segment; no PASS/skip/reentrant state.

Only the collector and fixed standard serializers are pure. Unknown code or
schemas retain the original full entry pin before any callback can execute.
"""

from collections.abc import Iterator
from inspect import getattr_static
from typing import Any

from pydantic import BaseModel
from pydantic_core import SchemaSerializer

from . import _cold_policy_segment as schema_code
from . import _cold_typed_stream as stream_code
from . import natural_live_admission as gate
from ._cold_policy_segment import _fixed_schema
from ._cold_typed_stream import _Comparison
from .errors import DomainError

_GATE_NAMES = ('_trial_typed_classes', '_trial_typed_nested_classes', '_trial_pure_mapping', '_trial_pure_data', '_trial_typed_equal',
    '_trial_typed_hold', '_trial_typed_values', '_graph_trial_journal_models_from_raw',
    '_graph_trial_frozen_models_from_raw', '_graph_trial_extraction_models_from_raw')
_GATE_CODE = tuple((name, getattr(gate, name)) for name in _GATE_NAMES)
_STREAM_CODE = tuple((name, getattr_static(_Comparison, name)) for name in (
    'validate_model', 'model_fields', 'raw_mapping', 'raw_equal', 'equal', 'standard_serializers'))
_STREAM_VALUES = stream_code._stream_values
_SCHEMA_SHAPE = schema_code._schema_shape
_SCHEMA_MATCHES = schema_code._schema_matches
_STANDARD_DUMP = BaseModel.model_dump


def _model_kinds(models):
    """Discover serializer classes, not actual-value validity or saved headers.

    The consumer still freshly validates every actual value and raw pin. Only
    this invocation's code eligibility needs the set of reachable classes.
    Retain completed objects so a removed DAG edge cannot permit id reuse.
    Native values/iteration never dispatch a foreign key hash or equality.
    """
    allowed = gate._trial_typed_nested_classes()
    kinds: dict[int, type] = {}
    completed: dict[int, Any] = {}
    active: set[int] = set()
    frames: list[tuple[Any, Iterator[Any]]] = [(None, iter(model for _, model, _ in models))]
    while frames:
        try:
            value = next(frames[-1][1])
        except StopIteration:
            value, _ = frames.pop()
            if value is not None:
                identity = id(value)
                active.remove(identity)
                completed[identity] = value
            continue
        kind = type(value)
        if (kind is str or kind is int or kind is float or kind is bool
                or kind is bytes or kind is type(None)):
            continue
        identity = id(value)
        if identity in active:
            return None
        if identity in completed:
            continue
        if kind is dict:
            children = iter(dict.values(value))
        elif kind is list or kind is tuple:
            children = iter(value)
        elif any(kind is item for item in allowed):
            raw = object.__getattribute__(value, '__dict__')
            if type(raw) is not dict:
                return None
            kinds[id(kind)] = kind
            children = iter(dict.values(raw))
        else:
            return None
        active.add(identity)
        frames.append((value, children))
    return tuple(kinds.values())


def serializers_current():
    """Fresh compiled-code witness, including kinds introduced after discovery.

    The immutable original C serializers contain only the already-reviewed
    callbacks. Changed compiled serializers/dump methods select a full entry pin before the
    original bridge; this is not a remembered content validation result.
    """
    return all(getattr_static(kind, 'model_dump') is _STANDARD_DUMP
        and type.__getattribute__(kind, '__dict__').get('__pydantic_serializer__') is serializer
        for kind, _, _, _, serializer in schema_code._SCHEMAS)


_MODEL_KINDS = _model_kinds
_SERIALIZERS_CURRENT = serializers_current
_SCHEMA_CATALOG = schema_code._SCHEMAS


def eligible(trial):
    from . import cold_accounted as owned
    from . import natural_spec_runtime as rt
    from ._cold_accounted_native import _NativeCandidate

    if (type(trial) is not rt._ColdTrialGraph
            or type(trial.guard) is not rt._ColdGraphRead
            or type(trial.guard.inputs) is not dict
            or not all(type(key) is str for key in trial.guard.inputs)
            or any(getattr(gate, name) is not function for name, function in _GATE_CODE)
            or stream_code._stream_values is not _STREAM_VALUES
            or schema_code._schema_shape is not _SCHEMA_SHAPE
            or schema_code._schema_matches is not _SCHEMA_MATCHES
            or schema_code._SCHEMAS is not _SCHEMA_CATALOG
            or _model_kinds is not _MODEL_KINDS
            or serializers_current is not _SERIALIZERS_CURRENT
            or any(getattr_static(_Comparison, name) is not function for name, function in _STREAM_CODE)
            or any(getattr_static(trial, name) is not function
                for name, function in zip(('_typed_parameter_models',
                    '_typed_values_from_models', '_native_base_mode'), rt._COLD_BASE_CORE, strict=True))):
        return False
    mode = getattr(trial, 'accounted_prewrite', None)
    return (type(mode) is owned._OwnedPrewriteMode and mode.graph is trial.guard
        and type(mode._native) is _NativeCandidate and mode._native.owned_ready is True
        and mode._native.graph is trial.guard and mode._native.mode is mode
        and all(getattr_static(mode if kind is owned._OwnedPrewriteMode else
                mode.scope if kind is owned._AccountedScope else kind, name) is function
            for kind, name, function in owned._BASE_PURE_MEMBERS)
        and all(getattr(owned, name) is function for name, function in owned._BASE_PURE_FUNCTIONS)
        and mode._base_pure_ready())


def fixed_serializers(models):
    """Fresh type discovery + complete schema/code witness before serialization.

    This metadata is discarded at return. No successful value or validation
    result survives into another _base invocation. Unfit input is not rejected
    by eligibility: the caller restores the original full entry pin and bridge.
    """
    try:
        kinds = _model_kinds(models)
        if kinds is None:
            return False
        for kind in kinds:
            namespace = type.__getattribute__(kind, '__dict__')
            serializer = namespace.get('__pydantic_serializer__')
            if (getattr_static(kind, 'model_dump') is not _STANDARD_DUMP
                    or type(serializer) is not SchemaSerializer
                    or SchemaSerializer.__reduce__(serializer)[1][0]
                        is not namespace.get('__pydantic_core_schema__')):
                return False
        return all(_fixed_schema(kind) for kind in kinds)
    except DomainError:
        return False

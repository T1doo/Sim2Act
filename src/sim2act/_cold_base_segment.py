"""One invocation's fixed native _base segment; no PASS/skip/reentrant state.

Only the collector and fixed standard serializers are pure. Unknown code or
schemas retain the original full entry pin before any callback can execute.
"""

from inspect import getattr_static

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
    """Fresh exact storage + complete schema/code witness, before serialization.

    This metadata is discarded at return. No successful value or validation
    result survives into another _base invocation. Unfit input is not rejected
    by eligibility: the caller restores the original full entry pin and bridge.
    """
    comparison = _Comparison(gate._trial_typed_nested_classes())
    try:
        for _, model, _ in models:
            comparison.validate_model(model)
        kinds = {type(model) for model, _, _ in comparison.models.values()}
        return comparison.standard_serializers() and all(_fixed_schema(kind) for kind in kinds)
    except DomainError:
        return False

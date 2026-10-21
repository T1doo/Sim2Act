"""Explicit offline candidate, never selected by production routing.

The backend must be built and passed explicitly. There is no backend discovery,
automatic installation, cached graph or native-failure fallback. Recursion
resource thresholds still require qualification before any runtime substitution.
"""

from . import natural_live_admission as gate

_PYTHON_STORAGE = gate._trial_typed_storage
_REQUIRE = gate.require
_ROOTS = gate._trial_typed_classes
_NESTED = gate._trial_typed_nested_classes


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

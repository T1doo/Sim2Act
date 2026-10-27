"""Default-off SQLite producer experiment; no ownership or cached PASS.

Only a fixed no-warning serialization and the intervening pure typed/hold
operations share two full content pins. Every invocation starts fresh. Original
SQL, authorization, business-clock and producer callers are untouched.
"""

from inspect import getattr_static

from pydantic_core import SchemaSerializer

from . import _cold_base_segment as code
from . import natural_live_admission as gate
from ._cold_typed_stream import _Comparison


class _ProducerSegment:
    __slots__ = ('graph', 'nonce', 'epoch', 'phase', 'qualified', 'fallback',
                 'legacy_base', 'base_qualified', 'stage_qualified', 'post_check', 'post_qualified')

    def __init__(self, graph, *, legacy_base=False, post_check=False):
        from . import natural_spec_runtime as runtime

        gate.require(type(graph) is runtime._ColdGraphRead and graph.store.test_only
                     and graph.store.sqlite and type(legacy_base) is bool and type(post_check) is bool,
                     'Isolated SQLite producer segment required')
        graph.check(graph.store, graph.connection)
        gate.require('_producer_segment_candidate' not in vars(graph),
                     'One producer segment per exact graph')
        self.graph, self.nonce = graph, graph.nonce
        self.epoch, self.phase = graph.epoch, graph.phase
        self.qualified = self.fallback = 0
        self.legacy_base = legacy_base
        self.base_qualified = 0  # diagnostic only, never queried for admission
        self.stage_qualified = 0
        self.post_check, self.post_qualified = post_check, 0
        graph._producer_segment_candidate = self

    def current(self, graph, store, c):
        from . import natural_spec_runtime as runtime

        gate.require(graph is self.graph and graph.nonce is self.nonce
                     and graph.epoch == self.epoch and graph.phase == self.phase
                     and vars(graph).get('_producer_segment_candidate') is self)
        runtime._ColdGraphRead._check_dynamic(graph, store, c)

    def stage_parent(self, graph, store, c, stage_facts):
        """After caller's full pin, keep second dynamic plus identical joins."""
        try:
            ready = self.legacy_base is True and code.legacy_stage_current()
        except Exception:
            return False  # Unknown qualification retains the original entry.
        if not ready:
            return False
        try:
            self.current(graph, store, c)
            inputs = gate._trial_pure_mapping(graph.inputs)
            gate.require('cold-trial:complete' in inputs)
            gate._graph_trial_stage_raw_from_raw(stage_facts, inputs['cold-trial:complete'])
            self.stage_qualified += 1
            return True
        except BaseException:
            gate._graph_trial_pin(graph, store, c)
            raise

    def produced(self, graph, store, c, models, expected, model, legacy):
        """Retain full entry/exit, three typed passes and the original hold.

        A no-warning dump is an invocation-local result, never a verdict stored
        across a pin. Unknown/warning input uses the unchanged original function
        before any new cohort entry or result is published.
        """
        from . import natural_spec_runtime as runtime

        def old():
            self.fallback += 1
            return legacy(graph, store, c, models, expected, model)

        # Discovery does not invoke serializers or arbitrary descriptors. Bad
        # cohort layout and unknown code retain the original error sequence.
        try:
            ready = not (type(models) is not list
                or not all(type(e) is tuple and len(e) == 3 for e in models)
                or not any(expected is cls for cls in gate._trial_typed_classes())
                or type(model) is not expected
                or not code.serializers_current()
                or not code.fixed_serializers([*models, (expected, model, {})]))
        except Exception:
            return old()
        if not ready:
            return old()
        try:
            self.current(graph, store, c)
            gate._graph_trial_pin(graph, store, c)
            gate._trial_typed_values(models)
            try:
                # Complete exact actual storage gate, including nested values,
                # fields_set and extra/private. No model_validate or callback.
                _Comparison(gate._trial_typed_nested_classes()).validate_model(model)
                serializer = type.__getattribute__(expected, '__dict__')['__pydantic_serializer__']
                # Match every local BaseModel.model_dump default. warnings=error
                # keeps the qualifying path free of warning-dispatch callbacks.
                raw = SchemaSerializer.to_python(serializer, model, mode='python',
                    include=None, exclude=None, context=None, by_alias=None,
                    exclude_unset=False, exclude_defaults=False, exclude_none=False,
                    exclude_computed_fields=False, round_trip=False, warnings='error',
                    fallback=None, serialize_as_any=False)
            except Exception:
                # No new triple/result has escaped. In particular warnings still
                # execute exactly through the original dump on this old route.
                return old()
            self.current(graph, store, c)
            gate._trial_typed_values(models)
            gate._graph_trial_hold(graph, store, c, models, expected, model, raw)
            gate._graph_trial_pin(graph, store, c)
            self.current(graph, store, c)
            gate._trial_typed_values(models)
            self.qualified += 1
            return raw
        except BaseException:
            runtime._ColdGraphRead.invalidate(graph)
            raise

    def check_trial(self, trial):
        """One fixed post check, retaining the LATE complete content boundary.

        Never replace a late pin with an earlier PASS. Original independent
        base/seed entries remain self-pinning. Seed fields/dumps follow their
        original late full check and are not assumed callback-free.
        """
        from . import natural_spec_runtime as rt
        from .production_trial_policy import RunCheck

        def authority(value):
            return (type(value) is tuple and len(value) == 5
                    and all(type(item) is str for item in value))

        try:
            if (not self.post_check or not self.legacy_base
                    or type(trial) is not rt._ColdTrialGraph or trial.guard is not self.graph
                    or self.phase != 'post' or trial.accounted_prewrite is not None
                    or trial._owned_models is not None or not code.eligible(trial)
                    or getattr_static(trial, '_base') is not rt._COLD_PUBLIC_BASE
                    or getattr_static(trial, '_check_links') is not rt._COLD_CHECK_LINKS
                    or any(getattr_static(trial, name) is not function for name, function in zip(
                        ('_typed_parameter_models', '_typed_values_from_models', '_native_base_mode'),
                        rt._COLD_BASE_CORE, strict=True))
                    or rt._ColdTrialGraph._check_links is not rt._COLD_CHECK_LINKS
                    or rt._ColdAuditSeed.check is not rt._COLD_AUDIT_SEED_CHECK
                    or type(trial.audit_seed) is not rt._ColdAuditSeed
                    or getattr_static(trial.audit_seed, 'check') is not rt._COLD_AUDIT_SEED_CHECK
                    or trial.audit_seed.guard is not self.graph
                    or type(trial.phase) is not str
                    or type(trial.authorities) is not set
                    or not all(authority(item) for item in trial.authorities)):
                return False
            for value in (trial.authority_fields, trial.authority_record):
                if value is not None and (type(value) is not dict
                        or not all(type(key) is str for key in value)):
                    return False
            if trial.authority_record is not None:
                values = trial.authority_record.get('authorities')
                if (type(trial.authority_record_key) is not str or type(values) is not tuple
                        or not all(authority(item) for item in values)):
                    return False
            if trial.context_record is not None:
                if (type(trial.context_record_key) is not str
                        or type(trial.context_record) is not dict
                        or not code.fixed_serializers([(RunCheck, trial.context, trial.context_record)])):
                    return False
            # Same collector and fixed serializers as the reviewed base segment.
            # No callback/output/SQL occurs during this conservative selection.
            models = trial._typed_parameter_models()
            if not code.fixed_serializers(models) or not code.serializers_current():
                return False
        except Exception:
            return False
        try:
            self.current(self.graph, trial.worker.store, trial.c)
            gate.require(trial.worker is self.graph.worker and trial.c is self.graph.connection)
            trial._typed_values_from_models(models)
            # Original base exit dynamic boundary remains at its original point.
            self.current(self.graph, trial.worker.store, trial.c)
            trial._check_links()
            # Original seed entry full boundary stays LATE: mutations anywhere
            # in the complete frontier during the pure middle cannot escape.
            trial.audit_seed.check(trial.worker.store, trial.c, self.graph)
            self.post_qualified += 1
            return True
        except BaseException:
            # Preserve complete-content rejection priority on pure failures.
            if self.graph.active:
                self.graph.check(trial.worker.store, trial.c)
            raise

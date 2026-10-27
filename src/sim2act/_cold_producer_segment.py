"""Default-off SQLite producer experiment; no ownership or cached PASS.

Only a fixed no-warning serialization and the intervening pure typed/hold
operations share two full content pins. Every invocation starts fresh. Original
SQL, authorization, business-clock and producer callers are untouched.
"""

from pydantic_core import SchemaSerializer

from . import _cold_base_segment as code
from . import natural_live_admission as gate
from ._cold_typed_stream import _Comparison


class _ProducerSegment:
    __slots__ = ('graph', 'nonce', 'epoch', 'phase', 'qualified', 'fallback')

    def __init__(self, graph):
        from . import natural_spec_runtime as runtime

        gate.require(type(graph) is runtime._ColdGraphRead and graph.store.test_only
                     and graph.store.sqlite, 'Isolated SQLite producer segment required')
        graph.check(graph.store, graph.connection)
        gate.require('_producer_segment_candidate' not in vars(graph),
                     'One producer segment per exact graph')
        self.graph, self.nonce = graph, graph.nonce
        self.epoch, self.phase = graph.epoch, graph.phase
        self.qualified = self.fallback = 0
        graph._producer_segment_candidate = self

    def current(self, graph, store, c):
        from . import natural_spec_runtime as runtime

        gate.require(graph is self.graph and graph.nonce is self.nonce
                     and graph.epoch == self.epoch and graph.phase == self.phase
                     and vars(graph).get('_producer_segment_candidate') is self)
        runtime._ColdGraphRead._check_dynamic(graph, store, c)

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
        if (type(models) is not list
                or not all(type(e) is tuple and len(e) == 3 for e in models)
                or not any(expected is cls for cls in gate._trial_typed_classes())
                or type(model) is not expected
                or not code.serializers_current()
                or not code.fixed_serializers([*models, (expected, model, {})])):
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

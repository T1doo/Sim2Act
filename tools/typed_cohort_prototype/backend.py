"""Offline complete-cohort experiment; deliberately not a runtime selector.

This reuses the existing explicit C projector to measure the whole four-stage
bridge, not just one contract's projection. Its build/helper/signal eligibility
is not yet a production certificate. Never import this module from src.
"""
from collections import Counter

from sim2act import natural_live_admission as gate
from sim2act._cold_typed_stream import _stream_values
from sim2act import _cold_cohort_backend as guarded


class CohortBackend:
    def __init__(self, backend=None):
        self.backend = backend
        self.calls = self.triples = 0
        self.selected = Counter()
        self.declined = Counter()

    def __call__(self, models):
        # Keep live list iteration and per-entry execution order. Neither the
        # cohort nor any future triple is copied or pre-validated in advance.
        gate.require(type(models) is list, 'Exact trial model cohort required')
        self.calls += 1
        for entry in models:
            gate.require(type(entry) is tuple and len(entry) == 3,
                'Exact trial model triple required')
            expected, model, raw = entry
            self.triples += 1
            if self.backend is None:
                if guarded.try_triple(expected, model, raw) is True:
                    self.selected[expected.__name__] += 1
                    continue
                self.declined[expected.__name__] += 1
                if _stream_values(expected, model, raw):
                    continue
                actual = gate._trial_typed_storage(expected, model)
            else:
                actual = self.backend.select(expected, model)
                if actual is None:
                    self.declined[expected.__name__] += 1
                    if _stream_values(expected, model, raw):
                        continue
                    actual = gate._trial_typed_storage(expected, model)
                else:
                    self.selected[expected.__name__] += 1
            gate.require(type(raw) is dict, 'Complete typed trial raw pin required')
            # The complete raw gate happens before either mismatch rejection
            # or serializer dispatch. It owns a real pre-serializer snapshot.
            saved = gate._trial_pure_data(raw)
            gate.require(gate._trial_typed_equal(actual, saved),
                'Typed trial storage changed after its complete raw proof')
            value = expected.model_dump(model, warnings=False)
            gate.require(gate._trial_typed_equal(value, saved),
                'Typed trial fact changed after its complete raw proof')

    def counts(self):
        return dict(calls=self.calls, triples=self.triples,
            selected=dict(self.selected), declined=dict(self.declined))

"""Earlier content-only calibration retains full SHA, ABA and dynamic boundaries."""

import sys

import pytest
from test_cold_extract_parse import local_origin as local_origin
from test_cold_extract_parse import no_external_transport as no_external_transport
from test_loaded_raw_segment import scope

from sim2act import natural_spec_runtime as r
from sim2act import pb_natural_specs as pb
from sim2act.errors import DomainError


def test_second_check_calibrates_with_both_full_keys_and_add_resets(local_origin):
    f = local_origin
    with f.store.tx() as c, pb._source_reads(f.store, c), scope(f, c) as graph:
        graph.add("frequency-boundary", [[1]])
        samples = []
        for _ in range(4):
            start = graph._diagnostic_counts[1]
            graph.check(f.store, c)
            samples.append(graph._diagnostic_counts[1] - start)
        assert samples == [1, 2, 0, 0]
        graph.add("new-full-edge", [[2]])
        assert "_structure_state" not in vars(graph)
        start = graph._diagnostic_counts[1]
        graph.check(f.store, c)
        assert graph._diagnostic_counts[1] - start == 1
        assert vars(graph)["_structure_state"].capsule is None
    assert not graph.active and "_structure_state" not in vars(graph)


@pytest.mark.parametrize("aba", [False, True])
def test_second_calibration_drift_or_aba_does_not_pin_changed_content(local_origin, aba):
    f = local_origin
    monitoring = sys.monitoring
    slot = next(i for i in (4, 3, 5) if monitoring.get_tool(i) is None)
    finished = False
    with f.store.tx() as c, pb._source_reads(f.store, c):
        with pytest.raises(DomainError):
            with scope(f, c) as graph:
                graph.add("calibration-aba", [[1]])
                graph.check(f.store, c)  # Original pending SHA, no prior PASS reused.
                value = graph.inputs["calibration-aba"][0]
                calls = []

                def entered(code, offset):
                    calls.append("start")
                    if aba and len(calls) == 3:
                        value[0] = 1

                def returned(code, offset, result):
                    calls.append("return")
                    if len(calls) == 2:
                        value[0] = 2

                monitoring.use_tool_id(slot, "full SHA calibration drift witness")
                monitoring.register_callback(slot, monitoring.events.PY_START, entered)
                monitoring.register_callback(slot, monitoring.events.PY_RETURN, returned)
                monitoring.set_local_events(
                    slot,
                    r._ColdGraphRead.input_key.__code__,
                    monitoring.events.PY_START | monitoring.events.PY_RETURN,
                )
                try:
                    if aba:
                        graph.check(f.store, c)
                        assert value == [1] and "_structure_state" not in vars(graph)
                        assert len(calls) == 6  # Before + after + original-frame fallback.
                    else:
                        with pytest.raises(DomainError):
                            graph.check(f.store, c)
                        assert len(calls) == 4
                finally:
                    monitoring.set_local_events(slot, r._ColdGraphRead.input_key.__code__, 0)
                    monitoring.free_tool_id(slot)
                if aba:
                    value[0] = 2
                    with pytest.raises(DomainError):
                        graph.check(f.store, c)
                assert not graph.active and "_structure_state" not in vars(graph)
                finished = True
    assert finished

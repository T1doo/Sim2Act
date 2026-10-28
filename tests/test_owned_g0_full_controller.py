"""One explicit owned G0 candidate on the unchanged finite Mock full controller.

All original functional assertions, quota spacing, fresh Cold Store, saved rows
and complete G1 execute. No global SQL listener, virtual clock or trace is used.
The original fixture substitutions are declared by exact function object, with
original source and closure witnesses still enforced by the candidate.
"""

import json
import sys
import time
import types
from contextlib import contextmanager

from test_pb_spec_production_controller import (
    observe_original_lease_failures as observe_original_lease_failures,
)
from test_pb_spec_production_controller import (
    test_pb_production_original_source_extraction_explicit_use_and_cold as original_flow,
)
from test_spec_production_controller import no_real_http as no_real_http

from sim2act import natural_spec_runtime as runtime
from sim2act import pa_spec_apps as spec
from sim2act import pa_trial_dispatch as dispatch
from sim2act import production_evidence as evidence
from sim2act import production_trial_admission as admission
from sim2act import spec_production as controller
from sim2act._owned_g0_candidate import MockCandidate
from sim2act.db import Store
from sim2act.worker import Worker


def declared_callbacks(*roots):
    result, seen = [], set()

    def visit(fn):
        if type(fn) is not types.FunctionType or id(fn) in seen:
            return
        seen.add(id(fn))
        if fn.__module__.startswith("test_"):
            result.append(fn)
        for cell in fn.__closure__ or ():
            visit(cell.cell_contents)

    for fn in roots:
        visit(fn)
    return tuple(result)


def test_owned_g0_full_original_controller(env, tmp_path, monkeypatch):
    candidates, g1, stages = [], [], {}
    original_once = Worker.once
    original_after = runtime._model_settlement_read

    def save():
        (tmp_path / "owned-g0-timings.json").write_text(
            json.dumps(
                dict(
                    classification="REAL_CLOCK_SYNTHETIC_MOCK_SQLITE_NOT_LIVE_NOT_PG",
                    candidates=[
                        dict(
                            selected=c.selected,
                            fallback=c.fallback,
                            stages=c.timings,
                            transactions=c.transactions,
                        )
                        for c in candidates
                    ],
                    g1=g1,
                    overlapping_g1_stage_times=stages,
                ),
                indent=2,
            )
            + "\n"
        )

    @contextmanager
    def measured_after(*args, **kwargs):
        # G0 has fully closed before original G1 begins. No hook survives this
        # original postwrite interval; the next G0 starts without monitoring.
        monitor = sys.monitoring
        slot = next(i for i in (4, 3, 5) if monitor.get_tool(i) is None)
        monitor.use_tool_id(slot, "owned candidate G1 passive timing")
        targets = (
            (runtime._ColdTrialGraph.commit, "graph.commit"),
            (runtime._cold_binding_limits_facet, "post_binding"),
            (spec._cold_receipts, "receipts"),
            (dispatch._graph_journal_chain, "journal_chain"),
            (runtime._ModelSettlementRead.live, "proof.live"),
            (runtime._ModelSettlementRead.check, "proof.check"),
        )
        codes = {fn.__code__: name for fn, name in targets}
        stacks = {}

        def enter(code, offset):
            stacks.setdefault(code, []).append(time.monotonic())

        def leave(code, offset, value):
            if stacks.get(code):
                started = stacks[code].pop()
                record = stages.setdefault(codes[code], dict(calls=0, seconds=0))
                record["calls"] += 1
                record["seconds"] += time.monotonic() - started

        for kind, callback in (
            (monitor.events.PY_START, enter),
            (monitor.events.PY_RETURN, leave),
            (monitor.events.PY_UNWIND, leave),
        ):
            monitor.register_callback(slot, kind, callback)
        for code in codes:
            monitor.set_local_events(
                slot,
                code,
                monitor.events.PY_START | monitor.events.PY_RETURN,
            )
        monitor.set_events(slot, monitor.events.PY_UNWIND)
        record = dict(started=time.time(), completed=False)
        start = time.monotonic()
        try:
            with original_after(*args, **kwargs) as value:
                yield value
            record["completed"] = True
        finally:
            record["seconds"] = time.monotonic() - start
            g1.append(record)
            monitor.set_events(slot, 0)
            for code in codes:
                monitor.set_local_events(slot, code, 0)
            monitor.free_tool_id(slot)
            save()

    def once(worker, *args, **kwargs):
        if controller.environment.__qualname__.endswith(".cold_environment"):
            callbacks = declared_callbacks(
                controller.environment,
                evidence.resolve_account,
                admission._qualified,
                Store.guard,
                dispatch.preflight,
                runtime.reservation_check,
                dispatch._journal_reads,
                runtime._model_settlement_read,
            )
            candidate = MockCandidate(fixture_callbacks=callbacks)
            worker._owned_g0_candidate = candidate
            candidates.append(candidate)
        try:
            return original_once(worker, *args, **kwargs)
        finally:
            save()

    monkeypatch.setattr(Worker, "once", once)
    monkeypatch.setattr(runtime, "_model_settlement_read", measured_after)
    try:
        original_flow(env, tmp_path, monkeypatch)
        assert len(candidates) == 1
        assert candidates[0].selected == 2 and candidates[0].fallback == 0
        assert len(candidates[0].transactions) == 2
        assert all(row["outcome"] == "COMMITTED" for row in candidates[0].transactions)
        assert len(g1) == 4 and all(row["completed"] for row in g1)
    finally:
        save()

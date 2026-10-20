"""Pure local observer validation; no business fixture, DB, Mock or G0."""

import contextlib
import os
import subprocess
import sys
import threading
import unittest
from pathlib import Path

from g0_stage_observer import StageObserver


class Clock:
    now = 0
    calls = 0

    def __call__(self):
        self.calls += 1
        return self.now


def metric(observer, name, stage=0):
    return observer.report()["stages"][stage]["metrics"][name]


class StageObserverUnits(unittest.TestCase):
    def tearDown(self):
        self.assertFalse(any(k == "sim2act" or k.startswith("sim2act.") for k in sys.modules))

    def test_nested_inclusive_and_observed_child_exclusive_cpu(self):
        clock = Clock()
        observer = StageObserver(clock)

        def child(value):
            clock.now += 3
            return b"wire"

        child = observer.wrapper(child, "codec", (0,))

        def parent(value):
            clock.now += 2
            self.assertEqual(child(value), b"wire")
            clock.now += 5
            return value

        parent = observer.wrapper(parent, "raw_copy", (0,))
        value = {"x": 1}
        with observer.region("_prepare"):
            self.assertIs(parent(value), value)
        self.assertEqual(clock.calls, 4)
        self.assertEqual(metric(observer, "raw_copy")["inclusive_cpu_ns"], 10)
        self.assertEqual(metric(observer, "raw_copy")["observed_child_exclusive_cpu_ns"], 7)
        self.assertEqual(metric(observer, "codec")["inclusive_cpu_ns"], 3)
        self.assertEqual(metric(observer, "codec")["codec_output_bytes"], 4)
        self.assertEqual(metric(observer, "raw_copy")["input_root_elements"], 1)
        self.assertEqual(observer.depth, 0)

    def test_stage_identity_gate_original_context_and_suppression(self):
        observer = StageObserver(Clock())
        owned, foreign = object(), object()
        events = []
        error = ValueError("original body error")

        @contextlib.contextmanager
        def original(instance, name):
            events.append("enter")
            try:
                yield
            except ValueError as caught:
                self.assertIs(caught, error)
                events.append("suppressed")
            finally:
                events.append("exit")

        stage = observer.stage_wrapper(original, lambda instance: instance is owned)
        function = observer.wrapper(lambda value: value, "codec", (0,))
        function(b"outside")
        with stage(foreign, "_prepare"):
            function(b"foreign")
        with stage(owned, "_prepare"):
            function(b"owned")
            raise error
        self.assertEqual(events, ["enter", "exit", "enter", "suppressed", "exit"])
        self.assertEqual(metric(observer, "codec")["calls"], 1)
        self.assertIsNone(observer.active)
        self.assertEqual(observer.report()["status"], "COMPLETE_OBSERVATION")

    def test_each_stage_is_separate_and_no_full_input_walk_or_model_getter(self):
        observer = StageObserver(Clock())

        class Foreign:
            @property
            def __dict__(self):
                raise AssertionError("observer must not read model attributes")

            def __len__(self):
                raise AssertionError("observer must not call foreign len")

        value = Foreign()
        f = observer.wrapper(lambda expected, value: value, "typed_storage", (1,))
        for stage in ("_prepare", "_graph_run_context", "_graph_pb_accounting",
                      "_graph_resolve_trial_source", "_graph_pb_archive_chain"):
            with observer.region(stage):
                self.assertIs(f(object(), value), value)
        for row in observer.report()["stages"]:
            self.assertEqual(row["metrics"]["typed_storage"]["calls"], 1)
            self.assertEqual(row["metrics"]["typed_storage"]["unknown_input_roots"], 1)

    def test_other_thread_is_bypassed_even_for_first_stage(self):
        clock = Clock()
        observer = StageObserver(clock)
        f = observer.wrapper(lambda x: x, "raw_copy", (0,))

        def other():
            with observer.region("_prepare"):
                f({"other": 1})

        thread = threading.Thread(target=other)
        thread.start()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(clock.calls, 0)
        self.assertEqual(observer.report()["status"], "NOT_REACHED")
        with observer.region("_prepare"):
            thread = threading.Thread(target=other)
            thread.start()
            thread.join(timeout=2)
            f({"owned": 1})
        self.assertEqual(metric(observer, "raw_copy")["calls"], 1)

    def test_original_baseexception_identity_and_traceback_survive(self):
        observer = StageObserver(Clock())
        error = BaseException("original cancellation")
        calls = []

        def original(value):
            calls.append(value)
            raise error

        f = observer.wrapper(original, "raw_copy", (0,))
        try:
            with observer.region("_prepare"):
                f("once")
        except BaseException as caught:
            self.assertIs(caught, error)
            frames, tb = [], caught.__traceback__
            while tb is not None:
                frames.append(tb.tb_frame.f_code.co_name)
                tb = tb.tb_next
            self.assertIn("original", frames)
        else:
            self.fail("original exception swallowed")
        self.assertEqual(calls, ["once"])
        self.assertEqual(metric(observer, "raw_copy")["raises"], 1)
        self.assertEqual(observer.depth, 0)
        self.assertIsNone(observer.active)

    def test_original_stage_entry_and_exit_errors_keep_body_count_and_identity(self):
        for where in ("enter", "exit"):
            observer = StageObserver(Clock())
            error = BaseException("original stage " + where)
            calls = []

            @contextlib.contextmanager
            def original(instance, name, where=where, error=error):
                if where == "enter":
                    raise error
                yield
                raise error

            stage = observer.stage_wrapper(original, lambda instance: True)
            with self.assertRaises(BaseException) as caught:
                with stage(object(), "_prepare"):
                    calls.append("body")
            self.assertIs(caught.exception, error)
            self.assertEqual(calls, [] if where == "enter" else ["body"])
            self.assertIsNone(observer.active)
            self.assertEqual(observer.depth, 0)

    def test_clock_and_aggregation_failure_do_not_replace_return_or_exception(self):
        for fail_at in (1, 2):
            clock = Clock()

            def broken_clock(clock=clock, fail_at=fail_at):
                result = clock()
                if clock.calls == fail_at:
                    raise BaseException("observer clock failure")
                return result

            observer = StageObserver(broken_clock)
            calls = []
            result = object()
            f = observer.wrapper(lambda value, calls=calls, result=result:
                                 calls.append(value) or result, "codec", (0,))
            with observer.region("_prepare"):
                self.assertIs(f(b"once"), result)
            self.assertEqual(calls, [b"once"])
            self.assertEqual(observer.report()["status"], "INCOMPLETE")
            self.assertEqual(observer.depth, 0)
        observer = StageObserver(Clock())
        observer.rows[0] = None  # Broken aggregate, not business input.
        error = ValueError("original failure")

        def original(value):
            raise error

        with self.assertRaises(ValueError) as caught:
            with observer.region("_prepare"):
                observer.wrapper(original, "codec", (0,))(b"once")
        self.assertIs(caught.exception, error)
        self.assertEqual(observer.report()["status"], "INCOMPLETE")

    def test_bounded_stack_overflow_calls_business_once_per_entry_and_unwinds(self):
        observer = StageObserver(Clock(), max_depth=2)
        calls = []

        def original(value):
            calls.append(value)
            return f(value - 1) if value else b"done"

        f = observer.wrapper(original, "codec", (0,))
        with observer.region("_prepare"):
            self.assertEqual(f(3), b"done")
        self.assertEqual(calls, [3, 2, 1, 0])
        self.assertEqual(len(observer.frames), 2)
        self.assertEqual(len(observer.rows), 20)
        self.assertEqual(observer.depth, 0)
        self.assertEqual(observer.report()["status"], "INCOMPLETE")

    def test_actual_pure_functions_stage_and_exact_results_in_isolated_child(self):
        code = r'''
import contextlib, json, socket, types
from unittest.mock import patch
import httpx
from g0_stage_observer import StageObserver
from sim2act import natural_spec_runtime as runtime, natural_live_admission as gate
from sim2act.contracts import Limits
from sim2act.db import Store
from sim2act.model import InternModel
from sim2act.worker import Worker
def deny(*args, **kwargs): raise AssertionError("no business or transport")
class Patcher:
    def __init__(self, stack): self.stack=stack
    def setattr(self, owner, name, value): self.stack.enter_context(patch.object(owner,name,value))
limits=Limits(max_requests=4,max_tools=4,max_repairs=1,max_total_tokens=64000,
              max_output_tokens=1024,run_seconds=300)
values={"wire":b"complete", "deep":[{"same":1},(2,3)]}
expected=(runtime._cold_graph_bytes(values), gate._trial_typed_storage(Limits,limits),
          gate._trial_pure_data(values),gate._trial_typed_equal(values,values))
observer=StageObserver()
instance=runtime._ColdCommitDiagnostics(types.SimpleNamespace(_diagnostic_counts=[0,0]))
with contextlib.ExitStack() as stack:
    p=Patcher(stack)
    for owner,name in ((Store,"__init__"),(Store,"tx"),(Worker,"__init__"),(Worker,"once"),
                       (InternModel,"__init__"),(socket,"getaddrinfo"),(socket.socket,"connect"),
                       (httpx.HTTPTransport,"handle_request"),(httpx.AsyncHTTPTransport,"handle_async_request"),
                       (httpx.MockTransport,"handle_request"),(httpx.MockTransport,"handle_async_request")):
        p.setattr(owner,name,deny)
    observer.install(p,runtime,gate,lambda item:item is instance)
    with instance.stage("_prepare"):
        actual=(runtime._cold_graph_bytes(values),gate._trial_typed_storage(Limits,limits),
                gate._trial_pure_data(values),gate._trial_typed_equal(values,values))
    assert actual==expected
    assert instance.guard._diagnostic_counts==[0,0]
    error=ValueError("original identity")
    try:
        with instance.stage("_graph_run_context"):raise error
    except ValueError as caught: assert caught is error
    else:raise AssertionError("original exception lost")
report=observer.report()
assert report["status"]=="COMPLETE_OBSERVATION"
assert [row["calls"] for row in report["stages"][0]["metrics"].values()]==[1,1,1,1]
assert report["stages"][0]["metrics"]["codec"]["codec_output_bytes"]==len(expected[0])
assert len(json.dumps(report))<16000
print("ACTUAL_PURE_STAGE_EQUIVALENT; NO_PIN_OR_BUSINESS_CALLS")
'''
        repo = Path(__file__).resolve().parents[2]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                   PYTHONPATH=os.pathsep.join((str(repo / "src"), str(Path(__file__).parent))))
        result = subprocess.run([sys.executable, "-B", "-c", code], cwd=repo, env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ACTUAL_PURE_STAGE_EQUIVALENT", result.stdout)


if __name__ == "__main__":
    unittest.main()

"""Test-only virtual business time with real, original heartbeat commits.

Only the original journal waiting call advances time. Heartbeat event waits
wake at their original virtual deadlines; advancement waits for each due body
to finish and park again. Original state/Run gates own renewal success; parking
alone is not a commit ACK. Real deadlines bound cooperative scheduling; the
test command needs its separate real outer timeout for stalled foreground work.
"""

import sys
import threading
import time
from types import CodeType, FunctionType, SimpleNamespace


class SemanticClock:
    def __init__(self, patch, *, epoch=1_800_000_000.0):
        from sim2act import goal_applications, text_workflows
        from sim2act import natural_spec_runtime as runtime
        from sim2act import pa_trial_dispatch as dispatch
        from sim2act.db import Store
        from sim2act.worker import Worker

        self.real = time.monotonic
        self.wait = threading.Event.wait
        self.lock = threading.Lock()
        self.epoch = self.value = epoch
        self.started = self.real()
        self.waiters = {}
        self.workers = []
        self.expected_threads = set()
        self.renewals = []
        self.steps = 0
        self.wait_code = dispatch._journal_wait.__code__
        self.beat_codes = {Worker._heartbeat_lease.__code__}
        self.beat_codes.update(code for code in text_workflows.process_job.__code__.co_consts
            if type(code) is CodeType and code.co_name == 'beat')
        self.target_codes = set(code for method in (text_workflows.process_job, goal_applications.process)
            for code in method.__code__.co_consts if type(code) is CodeType and code.co_name == 'beat')
        initialize = Worker.__init__

        def registered(worker, *args, **kwargs):
            initialize(worker, *args, **kwargs)
            assert worker.store.test_only and worker.store.sqlite
            self.workers.append(worker)

        patch.setattr(Worker, '__init__', registered)
        start = threading.Thread.start

        def started(thread):
            target = thread._target
            if type(target) is FunctionType and target.__code__ in self.target_codes:
                cells = dict(zip(target.__code__.co_freevars, target.__closure__, strict=True))
                assert any(cells['worker'].cell_contents is item for item in self.workers)
                with self.lock:
                    self.expected_threads.add(thread)
            return start(thread)

        patch.setattr(threading.Thread, 'start', started)
        heartbeat = Store.heartbeat

        def committed(store, *args, **kwargs):
            try:
                result = heartbeat(store, *args, **kwargs)
            except BaseException as error:
                self.renewals.append((self.now(), False, type(error).__name__))
                raise
            self.renewals.append((self.now(), result is not None, None))
            return result

        patch.setattr(Store, 'heartbeat', committed)
        patch.setattr(time, 'time', self.now)
        def waited(event, timeout=None):
            return self.event_wait(event, timeout, sys._getframe(1))

        patch.setattr(threading.Event, 'wait', waited)
        # Only the natural adapter's business elapsed value is deterministic.
        # All safety/test supervision and diagnostic clocks retain real time.
        patch.setattr(runtime, 'time', SimpleNamespace(time=self.now, monotonic=self.now))

    def now(self):
        with self.lock:
            return self.value

    def healthy(self):
        if self.real() - self.started > 300:
            raise AssertionError('Semantic regression exceeded real 300-second test budget')

    def reset(self, value):
        with self.lock:
            assert not any(thread.is_alive() for thread in set(self.waiters) | self.expected_threads)
            self.waiters.clear()
            self.expected_threads.clear()
            self.value = value

    def assert_closed(self):
        with self.lock:
            assert not any(thread.is_alive() for thread in set(self.waiters) | self.expected_threads)

    def settled(self, event):
        until = self.real() + 5
        while True:
            self.healthy()
            with self.lock:
                due = any(thread.is_alive() and (thread not in self.waiters
                    or self.waiters[thread] is None or self.waiters[thread] <= self.value)
                    for thread in self.expected_threads)
            if not due:
                return
            assert self.real() < until, 'Original heartbeat body did not finish/park'
            self.wait(event, 0.001)

    def event_wait(self, event, timeout, frame):
        code, local = frame.f_code, frame.f_locals
        if code is self.wait_code:
            worker = local['worker']
            assert any(worker is item for item in self.workers) and event is worker.stop
            assert type(timeout) in (float, int) and 0 <= timeout <= 0.25
            self.healthy()
            if event.is_set():
                return True
            self.settled(event)  # Initial started-but-not-parked handshake.
            with self.lock:
                self.value += timeout
                self.steps += 1
            self.settled(event)
            return event.is_set()
        if code not in self.beat_codes:
            return self.wait(event, timeout)
        worker = local.get('worker', local.get('self'))
        if (not any(worker is item for item in self.workers)
                or event is not local.get('stopped')):
            return self.wait(event, timeout)
        assert type(timeout) in (int, float) and timeout > 0
        thread = threading.current_thread()
        with self.lock:
            target = self.value + timeout
            self.waiters[thread] = target
        while not event.is_set():
            self.healthy()
            with self.lock:
                if self.value >= target:
                    self.waiters[thread] = None
                    return False
            self.wait(event, 0.001)
        with self.lock:
            self.waiters.pop(thread, None)
        return True

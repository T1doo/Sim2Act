"""CPython 3.12 cProfile with one coherent thread CPU clock.

3.12 cProfile monitoring callbacks otherwise receive events from every thread.
Filter only profiler callbacks; no application callable is replaced. Heartbeat
threads continue normally. Whole-process CPU is recorded separately by caller.
"""

import cProfile
import sys
import threading
import time


class MainThreadCPUProfile:
    def __init__(self):
        self.profile = cProfile.Profile(timer=time.thread_time)
        self.owner = threading.get_ident()
        self.callbacks = []

    def enable(self):
        assert threading.get_ident() == self.owner
        assert sys.version_info[:2] == (3, 12)
        assert sys.monitoring.get_tool(sys.monitoring.PROFILER_ID) is None
        self.profile.enable()
        try:
            events = sys.monitoring.get_events(sys.monitoring.PROFILER_ID)
            sys.monitoring.set_events(sys.monitoring.PROFILER_ID, 0)
            for name in ('PY_START', 'PY_RESUME', 'PY_RETURN', 'PY_YIELD', 'CALL',
                         'C_RETURN', 'C_RAISE', 'PY_THROW', 'PY_UNWIND'):
                event = getattr(sys.monitoring.events, name)
                original = sys.monitoring.register_callback(sys.monitoring.PROFILER_ID, event, None)
                assert original is not None

                def filtered(*args, original=original):
                    if threading.get_ident() == self.owner:
                        return original(*args)

                sys.monitoring.register_callback(sys.monitoring.PROFILER_ID, event, filtered)
                self.callbacks.append(filtered)
            # Discard the initial enable/installation window, which may have
            # received foreign events before all filters were installed.
            self.profile.clear()
            sys.monitoring.set_events(sys.monitoring.PROFILER_ID, events)
        except BaseException:
            self.disable()
            raise

    def disable(self):
        self.profile.disable()
        assert sys.monitoring.get_tool(sys.monitoring.PROFILER_ID) is None
        assert sys.monitoring.get_events(sys.monitoring.PROFILER_ID) == 0
        self.callbacks.clear()

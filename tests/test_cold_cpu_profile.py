import pstats
import threading
import time

from cold_cpu_profile import MainThreadCPUProfile


def test_profile_has_only_owner_calls_and_cpu_despite_live_other_thread():
    ready, go = threading.Event(), threading.Event()

    def foreign_only():
        return sum(number * number for number in range(20000))

    def background():
        ready.set()
        while not go.is_set():
            foreign_only()
            time.sleep(0)

    def owner_only():
        try:
            raise ValueError('profile exceptional return')
        except ValueError:
            return sum(number + 1 for number in range(20000))

    thread = threading.Thread(target=background)
    thread.start()
    assert ready.wait(5)
    profiler = MainThreadCPUProfile()
    profiler.enable()
    try:
        assert owner_only() == 200010000
        go.set()
        thread.join(5)
        assert not thread.is_alive()
    finally:
        go.set()
        profiler.disable()
        thread.join(5)
    stats = pstats.Stats(profiler.profile).stats
    def key(function):
        code = function.__code__
        return code.co_filename, code.co_firstlineno, code.co_name
    assert key(foreign_only) not in stats
    assert stats[key(owner_only)][1] == 1
    assert stats[key(owner_only)][2] > 0
    assert all(value[2] >= 0 and value[3] >= 0 for value in stats.values())

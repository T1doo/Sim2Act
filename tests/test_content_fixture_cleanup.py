"""Only newly owned finite Python children; no process scan or HTTP/model."""
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("content_coordinator", Path(__file__).parents[1] / "scripts/protocol_completion_browser_ci.py")
coordinator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coordinator)


def test_normal_owned_child_reaped():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    result = coordinator.close_content_child(child, time.monotonic()+5, lambda _name, fn: fn())
    assert result == {"forced": False, "exit": 0}


def test_stalled_owned_child_terminated_and_reaped_before_shared_deadline():
    child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(10)"])
    until = time.monotonic()+5
    try:
        result = coordinator.close_content_child(child, until, lambda _name, fn: fn())
        assert result["forced"] and result["exit"] is not None
        assert child.poll() is not None and time.monotonic() < until
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=1)


def test_wait_interrupt_still_reaps_exact_child_and_returns_unknown():
    child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(10)"])
    original_wait = child.wait
    failures = []
    calls = 0

    def interrupted_wait(*a, **k):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt("synthetic wait interruption")
        return original_wait(*a, **k)

    def attempt(name, fn):
        try:
            return fn()
        except BaseException as error:
            failures.append((name, type(error).__name__))
            return None

    child.wait = interrupted_wait
    try:
        result = coordinator.close_content_child(child, time.monotonic()+5, attempt)
        assert result["forced"] and result["exit"] is not None
        assert failures == [("content_terminate_wait", "KeyboardInterrupt")]
    finally:
        if child.poll() is None:
            child.kill()
        original_wait(timeout=1)

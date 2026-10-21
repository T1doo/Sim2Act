"""Scheduler stand-ins only; no Store/Worker constructor, HTTP or Mock."""

import threading
from types import SimpleNamespace

import pytest
from cold_semantic_clock import SemanticClock


def test_unrelated_event_and_thread_waits_keep_original_binding(monkeypatch):
    clock = SemanticClock(monkeypatch)
    event = threading.Event()
    thread = threading.Thread(target=event.set)
    thread.start()
    assert event.wait(1)
    thread.join(1)
    assert not thread.is_alive() and clock.now() == clock.epoch


def test_due_wait_body_finishes_before_next_virtual_step(monkeypatch):
    clock = SemanticClock(monkeypatch)
    stopped = threading.Event()
    worker = SimpleNamespace(stop=threading.Event())
    clock.workers.append(worker)
    renewed = []

    def beat():
        while not stopped.wait(10):
            assert not worker.stop.is_set()
            renewed.append(clock.now())

    def quota():
        for _ in range(48):
            assert worker.stop.wait(0.25) is False

    clock.beat_codes = {beat.__code__}
    clock.target_codes = {beat.__code__}
    clock.wait_code = quota.__code__
    thread = threading.Thread(target=beat)
    thread.start()
    try:
        until = clock.real() + 1
        while thread not in clock.waiters:
            assert clock.real() < until
            clock.wait(stopped, 0.001)
        quota()
        assert clock.now() == clock.epoch + 12
        assert renewed == [clock.epoch + 10]
    finally:
        stopped.set()
        thread.join(1)
    assert not thread.is_alive()


def test_started_heartbeat_must_park_before_first_clock_advance(monkeypatch):
    clock = SemanticClock(monkeypatch)
    stopped, release = threading.Event(), threading.Event()
    worker = SimpleNamespace(stop=threading.Event())
    clock.workers.append(worker)
    registered_at = []

    def beat():
        assert release.wait(1)
        assert not worker.stop.is_set()
        registered_at.append(clock.now())
        stopped.wait(10)

    def quota():
        worker.stop.wait(0.25)

    clock.beat_codes = clock.target_codes = {beat.__code__}
    clock.wait_code = quota.__code__
    thread = threading.Thread(target=beat)
    thread.start()

    def allow():
        clock.wait(release, 0.01)
        release.set()

    other = threading.Thread(target=allow)
    other.start()
    try:
        quota()
        assert registered_at == [clock.epoch]
        assert clock.now() == clock.epoch + 0.25
    finally:
        stopped.set()
        thread.join(1)
        other.join(1)
    assert not thread.is_alive() and not other.is_alive()


def test_unparked_live_expected_thread_blocks_cleanup_and_reset(monkeypatch):
    clock = SemanticClock(monkeypatch)
    release = threading.Event()
    thread = threading.Thread(target=lambda: release.wait(1))
    thread.start()
    clock.expected_threads.add(thread)
    try:
        assert thread not in clock.waiters
        with pytest.raises(AssertionError):
            clock.assert_closed()
        with pytest.raises(AssertionError):
            clock.reset(clock.epoch)
        assert thread in clock.expected_threads
    finally:
        release.set()
        thread.join(1)
    clock.assert_closed()
    clock.reset(clock.epoch)

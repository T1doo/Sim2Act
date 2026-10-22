"""Private cancellation and real local server teardown, not Edge/DOM/G0."""
import importlib.util
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI

REPO = Path(__file__).parents[1]


def test_private_waits_cancel_without_orphan_or_unhandled_rejection():
    result = subprocess.run(["node", "--unhandled-rejections=strict", "tests/extract_completion_window.cjs"], cwd=REPO, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert '"status":"PASS"' in result.stdout


def test_seven_sync_workers_normal_exit_in_coordinator_remainder():
    spec = importlib.util.spec_from_file_location("ui_window", REPO / "scripts/protocol_completion_browser_ci.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    app, barrier = FastAPI(), threading.Barrier(7)

    @app.get("/health")
    def health():
        barrier.wait(timeout=3)
        return {"api": "UP"}

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]})
    monitor_stop = threading.Event()
    monitor = threading.Thread(target=lambda: monitor_stop.wait())
    thread.start()
    monitor.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started:
            assert thread.is_alive() and time.monotonic() < deadline
            time.sleep(0.01)
        # Seven genuine AnyIO sync workers, seven local GETs, no DB/model/Worker.
        with httpx.Client(timeout=4) as client, ThreadPoolExecutor(max_workers=7) as pool:
            responses = list(pool.map(lambda _: client.get(f"http://127.0.0.1:{port}/health"), range(7)))
        assert all(response.status_code == 200 for response in responses)
        assert len([t for t in threading.enumerate() if t.name == "AnyIO worker thread"]) == 7
    finally:
        # Node's four-second subdeadline leaves six of the original ten. This
        # test verifies the actual coordinator join code with that remainder;
        # it does not simulate an Edge close or qualify Windows process handles.
        cleanup_until = time.monotonic() + 6
        server.should_exit = True
        monitor_stop.set()
        monitor.join(max(0, cleanup_until - time.monotonic()))
        alive = helper.join_api_threads(thread, cleanup_until, lambda _name, fn: fn())
        assert not thread.is_alive() and not monitor.is_alive() and not alive
        assert time.monotonic() <= cleanup_until

"""Separate process/clock for sealed CSV content, never a Worker or seed.

The native coordinator owns this subprocess and stop file. Its historical
semantic clock cannot affect the Source/Extract APIs in the parent process.
"""
import gzip
import hashlib
import json
import socket
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "docs/evidence/research-desk-content-20261023"
REAL_TIME = time.time


def write(root, name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    import uvicorn
    from sqlalchemy import event, select
    from starlette.responses import JSONResponse
    from sim2act.config import Settings
    from sim2act.db import Store, fingerprint, meta
    from sim2act.model import InternModel
    from sim2act.model_budget import BudgetedProvider
    from sim2act.synthetic_workspace import workspace_app
    from sim2act.worker import Worker

    root = Path(sys.argv[1]).resolve(strict=True)
    until = time.monotonic() + float(sys.argv[2]) / 1000 - REAL_TIME()
    evidence = json.loads((FIXTURE / "saved-csv.json").read_text())
    compressed = (FIXTURE / "saved-csv.sqlite.gz").read_bytes()
    assert hashlib.sha256(compressed).hexdigest() == evidence["compressed_sha256"]
    data = gzip.decompress(compressed)
    assert hashlib.sha256(data).hexdigest() == evidence["database_sha256"]
    db = root / "content.sqlite"
    with db.open("xb") as f:
        f.write(data)
    store = Store("sqlite:///" + str(db), test_only=True)
    settings = Settings(str(store.engine.url), root, mode="mock")
    assert not settings.live_enabled and not settings.token
    counts = dict(business_get=0, static_get=0, business_post=0, blocked=0)
    sql, forbidden_calls, errors = {}, [], []
    lock = threading.Lock()
    thread = server = listener = None
    report = dict(status="UNKNOWN", scope="sealed CSV / isolated historical test clock / read-only HTTP", model_calls=0, worker_calls=0)

    def forbidden(*a, **k):
        forbidden_calls.append("new-action")
        raise AssertionError("No new model, Worker, claim or event")

    for owner, name in ((Worker, "__init__"), (Worker, "reserve"), (Store, "claim"), (Store, "event"), (InternModel, "request"), (InternModel, "request_serialized"), (BudgetedProvider, "call"), (BudgetedProvider, "preflight"), (BudgetedProvider, "accept_candidate")):
        setattr(owner, name, forbidden)

    def only_read(_c, _cursor, statement, _params, _ctx, _many):
        verb = statement.lstrip().split(None, 1)[0].upper()
        with lock:
            sql[verb] = sql.get(verb, 0) + 1
        assert verb in {"SELECT", "BEGIN"}, "No DML/DDL"

    event.listen(store.engine, "before_cursor_execute", only_read)

    def snapshot():
        with store.engine.connect() as c:
            return {t.name: sorted(fingerprint(dict(row)) for row in c.execute(select(t)).mappings()) for t in meta.sorted_tables}

    try:
        before = snapshot()
        time.time = lambda: evidence["business_at"]
        app = workspace_app(store, settings)

        @app.middleware("http")
        async def bounded(request, call_next):
            with lock:
                kind = "business_get" if request.url.path.startswith("/api/") or request.url.path == "/health" else "static_get"
                if request.method == "GET":
                    counts[kind] += 1
                    allowed = counts[kind] <= (100 if kind == "business_get" else 120)
                else:
                    counts["business_post"] += 1
                    allowed = False
                if not allowed or time.monotonic() >= until:
                    counts["blocked"] += 1
                    return JSONResponse({"error": {"code": "READ_ONLY_WINDOW_STOP"}}, status_code=409)
            return await call_next(request)

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))

        def run():
            try:
                server.run(sockets=[listener])
            except BaseException as error:
                errors.append(type(error).__name__)

        thread = threading.Thread(target=run)
        thread.start()
        ready_until = min(until, time.monotonic() + 8)
        while not server.started:
            assert thread.is_alive() and time.monotonic() < ready_until, "Content API startup failed"
            time.sleep(.01)
        write(root, "content-ready.json", dict(base=f"http://127.0.0.1:{listener.getsockname()[1]}", **evidence))
        while not (root / "content-stop").exists() and not (root / "stop").exists() and time.monotonic() < until:
            assert thread.is_alive(), "Content API exited early"
            time.sleep(.02)
        assert time.monotonic() < until, "Content work deadline"
        after = snapshot()
        report.update(before=before, after=after, database_bytes_unchanged=db.read_bytes() == data)
        assert before == after and report["database_bytes_unchanged"] and not forbidden_calls
        assert counts["business_post"] == counts["blocked"] == 0
        report["status"] = "PASS"
    except BaseException as error:
        report.update(status="FAIL", error=type(error).__name__, message=str(error))
    finally:
        shared_until = min(until + 10, time.monotonic() + 10)
        if (root / "cleanup-until.json").exists():
            shared_until = min(shared_until, time.monotonic() + max(0, json.loads((root / "cleanup-until.json").read_text()) - REAL_TIME()))
        if server:
            server.should_exit = True
        if thread:
            thread.join(max(0, shared_until - time.monotonic()))
        for worker in threading.enumerate():
            if worker.name == "AnyIO worker thread":
                worker.join(max(0, shared_until - time.monotonic()))
        alive = [w.name for w in threading.enumerate() if w.name == "AnyIO worker thread" and w.is_alive()]
        stopped = not thread or not thread.is_alive()
        # Listener stays open until the Uvicorn event loop has finished.
        if stopped and listener:
            listener.close()
        if stopped and not alive:
            store.engine.dispose()
        time.time = REAL_TIME
        report.update(sql_verbs=sql, server_counts=counts, forbidden_calls=forbidden_calls, cleanup=dict(api_stopped=stopped, anyio_alive=alive, errors=errors, within_deadline=time.monotonic() <= shared_until))
        if not stopped or alive or errors or time.monotonic() > shared_until:
            report["status"] = "UNKNOWN"
        if report["status"] == "PASS":
            for name in ("content.sqlite", "content.sqlite-wal", "content.sqlite-shm", "content-ready.json"):
                (root / name).unlink(missing_ok=True)
        report["cleanup"]["fixture_deleted"] = not db.exists()
        write(root, "content-result.json", report)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

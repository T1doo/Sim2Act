import importlib.util
from pathlib import Path

import psutil
import pytest


def manager():
    spec = importlib.util.spec_from_file_location(
        "manage", Path(__file__).parents[1] / "scripts/manage.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_owned_process_verified_without_reading_cwd(monkeypatch):
    m = manager()
    command = [m.sys.executable, "-m", "sim2act.worker"]

    class Fake:
        def is_running(self):
            return True

        def status(self):
            return psutil.STATUS_RUNNING

        def create_time(self):
            return 100.0

        def cmdline(self):
            return command

        def cwd(self):
            raise AssertionError("Do not require cross-sandbox cwd access")

    p = Fake()
    monkeypatch.setattr(m.psutil, "Process", lambda pid: p)
    record = {"pid": 123, "created_at": 100.0, "kind": "worker", "command": command}
    assert m.process(record) is p
    assert m.process({**record, "created_at": 99.0}) is None
    assert m.process({**record, "command": ["unrelated"]}) is None


def test_unknown_process_permission_retains_actionable_error(monkeypatch):
    m = manager()

    def denied(pid):
        raise psutil.AccessDenied(pid)

    monkeypatch.setattr(m.psutil, "Process", denied)
    with pytest.raises(RuntimeError, match="retain PID record"):
        m.process({"pid": 123})


@pytest.mark.parametrize("mode", ["transient", "empty", "wrong", "exited"])
def test_start_requires_identity_and_health_but_cleans_retained_children(monkeypatch, tmp_path, mode):
    """Unavailable startup argv must neither fabricate exit nor leak owned children."""
    from sim2act.config import Settings

    m = manager()
    children = []

    class Child:
        def __init__(self, command, **kwargs):
            self.pid = 100 + len(children)
            self.command = command
            self.reads = 0
            self.terminated = False
            self.reaped = False
            children.append(self)

        def poll(self):
            return 0 if self.terminated or (mode == "exited" and self.pid == 101) else None

        def is_running(self):
            return self.poll() is None

        def status(self):
            return psutil.STATUS_RUNNING

        def create_time(self):
            return 100.0

        def cmdline(self):
            self.reads += 1
            if self.pid == 101:
                if mode == "empty" or (mode == "transient" and self.reads == 1):
                    return []
                if mode == "wrong":
                    return ["unrelated"]
            return self.command

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            self.reaped = True
            return 0

    class Health:
        def json(self):
            return {"database": "UP", "worker": "UP"}

    monkeypatch.setattr(Settings, "from_env", lambda: Settings("synthetic", tmp_path))
    monkeypatch.setattr(m.sys, "argv", ["manage.py", "start", "--port", "0"])
    monkeypatch.setattr(m.subprocess, "Popen", Child)
    monkeypatch.setattr(m.psutil, "Process", lambda pid: children[pid - 100])
    monkeypatch.setattr(m.httpx, "get", lambda *args, **kwargs: Health())
    monkeypatch.setattr(m.time, "sleep", lambda seconds: None)
    if mode == "transient":
        m.main()
        assert (tmp_path / "processes.json").exists()
        assert children[1].reads >= 2 and not any(c.terminated for c in children)
        m.stop_launched(children)
    else:
        with pytest.raises(RuntimeError, match="exited" if mode == "exited" else "timed out"):
            m.main()
        assert not (tmp_path / "processes.json").exists()
    assert len(children) == 2 and all(c.reaped for c in children)
    assert all(c.terminated for c in children if mode != "exited" or c.pid != 101)

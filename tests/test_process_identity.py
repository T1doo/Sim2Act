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

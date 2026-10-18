"""Session-wide guard starts before the module-scoped fresh prefix fixture."""
import json
import os
import socket
import threading
import time
import traceback
from pathlib import Path

import httpx
import pytest

from sim2act.config import Settings
from sim2act.model import InternModel, MockModel
from sim2act.db import Store

attempts = []
adapter_methods = []
heartbeats = []
controller_checks = []
patch = None


def pytest_sessionstart(session):
    global patch
    patch = pytest.MonkeyPatch()

    def blocked(*args, **kwargs):
        attempts.append("FORBIDDEN_REAL_IO_OR_ENV_DISCOVERY_OR_MOCK_FALLBACK")
        raise AssertionError("Fresh stages qualification permits only exact synthetic InternModel")

    patch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    patch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked)
    patch.setattr(socket.socket, "connect", blocked)
    patch.setattr(socket.socket, "connect_ex", blocked)
    patch.setattr(socket, "create_connection", blocked)
    patch.setattr(Settings, "from_env", blocked)
    patch.setattr(MockModel, "request", blocked)
    original_heartbeat = Store.heartbeat

    def observed_heartbeat(self, worker_id, run_id=None, fence=None, lease_seconds=30, **kwargs):
        if run_id is not None and not 0 < lease_seconds <= 30:
            blocked()
        started = time.time()
        renewed = original_heartbeat(self, worker_id, run_id, fence, lease_seconds, **kwargs)
        if run_id is not None:
            heartbeats.append(dict(run_id=run_id, fence=fence, lease_seconds=lease_seconds,
                deadline=kwargs.get("_deadline"), running_only=kwargs.get("_running_only",False),
                thread=threading.current_thread().name, started_at=started,
                committed_at=time.time(), renewed_until=renewed))
        return renewed
    patch.setattr(Store, "heartbeat", observed_heartbeat)
    from sim2act import production_trial_journal as journal
    from sim2act import production_trial_policy as policy
    for module, name in ((journal, "_apply_in_transaction"), (policy, "check_run")):
        original = getattr(module, name)

        def observed(*args, _original=original, _name=name, **kwargs):
            started = time.monotonic()
            value = args[5] if len(args) > 5 else kwargs.get(
                "stage" if _name == "check_run" else "identity")
            stage = value if _name == "check_run" else getattr(value, "stage", None)
            row = dict(function=_name, stage=stage, started_at=time.time())
            if _name == "_apply_in_transaction":
                row["operation"] = args[9] if len(args) > 9 else kwargs.get("operation")
            try:
                return _original(*args, **kwargs)
            except BaseException as exc:
                row.update(error=getattr(exc, "code", type(exc).__name__), traceback=[dict(file=Path(f.filename).name,
                    line=f.lineno, function=f.name) for f in traceback.extract_tb(exc.__traceback__)])
                raise
            finally:
                row.update(seconds=time.monotonic()-started, ended_at=time.time())
                controller_checks.append(row)
        patch.setattr(module, name, observed)
    for name in ("request", "request_serialized", "request_serialized_captured",
                 "_request_serialized", "_deadline_request"):
        original = getattr(InternModel, name)

        def guarded(self, *args, _original=original, _name=name, **kwargs):
            if (type(self) is not InternModel or type(self.transport) is not httpx.MockTransport
                    or type(self.settings) is not Settings or self.settings.mode != "mock"
                    or self.settings.token not in ("synthetic-offline-planner", "synthetic-offline-natural-spec")):
                blocked()
            adapter_methods.append(dict(method=_name, family=self.settings.token))
            return _original(self, *args, **kwargs)
        patch.setattr(InternModel, name, guarded)


def pytest_sessionfinish(session, exitstatus):
    Path(os.environ["STAGES_GUARD_PROOF"]).write_text(json.dumps(dict(
        attempts=attempts, adapter_methods=adapter_methods, heartbeats=heartbeats,
        passive_original_controller_checks=controller_checks,
        pytest_exitstatus=exitstatus,
        guard_starts_before_module_fixture=True,
        scope="Exact original InternModel with synthetic tokens and MockTransport only"), indent=2) + "\n")
    patch.undo()

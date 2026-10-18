"""Session-wide guard starts before the module-scoped fresh prefix fixture."""
import json
import os
import socket
from pathlib import Path

import httpx
import pytest

from sim2act.config import Settings
from sim2act.model import InternModel, MockModel

attempts = []
adapter_methods = []
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
        attempts=attempts, adapter_methods=adapter_methods, pytest_exitstatus=exitstatus,
        guard_starts_before_module_fixture=True,
        scope="Exact original InternModel with synthetic tokens and MockTransport only"), indent=2) + "\n")
    patch.undo()

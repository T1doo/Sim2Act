"""Run-wide offline sentinels; no outbound requests or credential discovery."""
import json
import os
from pathlib import Path

import httpx
import pytest

from sim2act.config import Settings
from sim2act.model import InternModel

attempts = []


@pytest.fixture(autouse=True)
def offline_boundary_guard(monkeypatch):
    def reject(*args, **kwargs):
        attempts.append("FORBIDDEN_PROVIDER_OR_CREDENTIAL_ACCESS")
        raise AssertionError("This execution is offline synthetic only")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", reject)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject)
    monkeypatch.setattr(Settings, "from_env", reject)
    for method in ("request", "request_serialized", "request_serialized_captured", "_request_serialized", "_deadline_request"):
        monkeypatch.setattr(InternModel, method, reject)


def pytest_sessionfinish(session, exitstatus):
    Path(os.environ["PRODUCTION_BOUNDARY_GUARD_PROOF"]).write_text(json.dumps(dict(
        forbidden_attempts=attempts, pytest_exitstatus=exitstatus,
        blocked_surfaces=["sync/async HTTPTransport", "Settings.from_env", "InternModel request methods"],
        scope="offline synthetic, TestClient ASGI allowed"), indent=2) + "\n")

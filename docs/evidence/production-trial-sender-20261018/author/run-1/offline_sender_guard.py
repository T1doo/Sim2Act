"""Real IO forbidden; existing InternModel is allowed only with exact synthetic adapter."""
import json
import os
import socket
from pathlib import Path

import httpx
import pytest

from sim2act.config import Settings
from sim2act.model import InternModel

attempts=[]
adapter_methods=[]

@pytest.fixture(autouse=True)
def offline_guard(monkeypatch):
    def blocked(*args,**kwargs):
        attempts.append('FORBIDDEN_REAL_IO_OR_ENV_DISCOVERY')
        raise AssertionError('Uninstalled sender qualification is offline only')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',blocked)
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(socket.socket,'connect_ex',blocked)
    monkeypatch.setattr(Settings,'from_env',blocked)
    for name in ('request','request_serialized','request_serialized_captured','_request_serialized','_deadline_request'):
        original=getattr(InternModel,name)
        def guarded(self,*args,_original=original,_name=name,**kwargs):
            if (type(self) is not InternModel or type(self.transport) is not httpx.MockTransport
                    or type(self.settings) is not Settings or self.settings.mode!='mock'
                    or self.settings.token!='synthetic-offline-planner'):
                blocked()
            adapter_methods.append(_name)
            return _original(self,*args,**kwargs)
        monkeypatch.setattr(InternModel,name,guarded)

def pytest_sessionfinish(session,exitstatus):
    Path(os.environ['SENDER_GUARD_PROOF']).write_text(json.dumps(dict(
        attempts=attempts,adapter_methods=adapter_methods,pytest_exitstatus=exitstatus,
        scope='Only exact existing synthetic InternModel/MockTransport; method calls are not real provider calls'),indent=2)+'\n')

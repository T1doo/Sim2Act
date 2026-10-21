import json
import socket
import sqlite3
import subprocess
from pathlib import Path

import httpx
import pytest
from sim2act.db import Store
from sim2act.worker import Worker
from sim2act.model import InternModel

ATTEMPTS = []


@pytest.fixture(autouse=True)
def no_business_io(monkeypatch):
    def trip(name):
        def stop(*args, **kwargs):
            ATTEMPTS.append(name)
            raise AssertionError('offline proof attempted ' + name)
        return stop
    for obj, name in ((Store, '__init__'), (Store, 'tx'), (Worker, '__init__'),
            (Worker, 'once'), (InternModel, '__init__'),
            (httpx.MockTransport, 'handle_request'),
            (httpx.MockTransport, 'handle_async_request'),
            (httpx.HTTPTransport, 'handle_request'),
            (httpx.AsyncHTTPTransport, 'handle_async_request'),
            (socket.socket, 'connect'), (socket, 'getaddrinfo'),
            (sqlite3, 'connect'), (subprocess, 'Popen')):
        monkeypatch.setattr(obj, name, trip(getattr(obj, '__name__', str(type(obj))) + '.' + name))
    yield


def pytest_sessionfinish(session, exitstatus):
    Path(__file__).with_name('TRIPWIRES.json').write_text(json.dumps(dict(
        scope='active for test setup/body/teardown after pure module imports',
        blocked_attempts=ATTEMPTS, pytest_exitstatus=exitstatus,
        no_db_or_transport_or_business_constructor=True), indent=2) + '\n')

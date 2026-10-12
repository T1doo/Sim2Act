"""Prepared independent SQLite fixture; not executed before final freeze."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store


@pytest.fixture
def env(tmp_path):
    url = "sqlite:///" + str(tmp_path / "independent.db")
    store = Store(url, test_only=True)
    store.initialize()
    a = store.user("independent A", "synthetic-test-A")
    b = store.user("independent B", "synthetic-test-B")
    settings = Settings(url, Path(tmp_path), mode="mock")
    client = TestClient(create_app(store, settings))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    response = client.post("/api/projects", json={"name": "independent provider scope"})
    assert response.status_code == 201, response.text
    pid = response.json()["id"]
    response = client.post(f"/api/projects/{pid}/resources", json={"name": "base.csv", "format": "csv", "content": "quantity\n1\n"})
    assert response.status_code == 201, response.text
    resource = response.json()["id"]
    yield store, settings, client, a, b, pid, resource
    client.close()
    store.engine.dispose()

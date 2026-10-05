import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, new_id


@pytest.fixture
def env(tmp_path):
    url = os.environ.get("SIM2ACT_TEST_DATABASE_URL", "sqlite:///" + str(tmp_path / "fixture.db"))
    store = Store(url, test_only=True)
    schema = new_id("test")
    if not store.sqlite:
        with store.engine.begin() as c:
            c.execute(text('CREATE SCHEMA "' + schema + '"'))
        store.engine = store.engine.execution_options(schema_translate_map={None: schema})
    store.initialize()
    # Explicit synthetic identities, never production secrets.
    a = store.user("fixture A", "synthetic-test-A")
    b = store.user("fixture B", "synthetic-test-B")
    s = Settings(url, Path(tmp_path), mode="mock")
    client = TestClient(create_app(store, s))
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    pid = client.post("/api/projects", json={"name": "中文 空格工程"}).json()["id"]
    fixture = Path(__file__).parent / "fixtures" / "f1.csv"
    resource = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "data.csv", "format": "csv", "content": fixture.read_text()},
    ).json()["id"]
    yield store, s, client, a, b, pid, resource
    client.close()
    if not store.sqlite:
        with store.engine.begin() as c:
            c.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
    store.engine.dispose()

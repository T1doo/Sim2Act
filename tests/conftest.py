import os
import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

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
    store.initialize(fresh_test_schema=None if store.sqlite else schema)
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


@pytest.fixture
def runtime_role(env):
    """A temporary PG application role; owner credentials stay in the test fixture only."""
    store, settings, *_ = env
    if store.sqlite:
        pytest.skip("Application-role subprocess regression requires explicit isolated PostgreSQL")
    schema = store.engine.get_execution_options()["schema_translate_map"][None]
    role = new_id("test_app")
    password = secrets.token_hex(32)
    try:
        with store.engine.begin() as c:
            c.execute(
                text(
                    f"CREATE ROLE \"{role}\" LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE"
                )
            )
            c.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO "{role}"'))
            c.execute(
                text(
                    f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO "{role}"'
                )
            )
    except Exception:
        raise RuntimeError(
            "Isolated test application-role setup failed; values suppressed"
        ) from None
    url = (
        make_url(settings.database_url)
        .set(username=role, password=password)
        .update_query_dict({"options": "-csearch_path=" + schema})
        .render_as_string(hide_password=False)
    )
    try:
        yield url
    finally:
        try:
            with store.engine.begin() as c:
                c.execute(text(f'DROP OWNED BY "{role}"'))
                c.execute(text(f'DROP ROLE "{role}"'))
        except Exception:
            raise RuntimeError("Isolated test role cleanup failed; values suppressed") from None

"""Only the explicitly authorized one-time CI, with runtime CRUD under an app role."""

import json
import os
import re
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, new_id


def private_config(path):
    if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REPOSITORY") != "T1doo/Sim2Act"
            or os.environ.get("GITHUB_REF") != "refs/heads/dev/production-trial-stages-20261018"
            or os.environ.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise ValueError("The record PG fixture requires the authorized actual CI runner")
    expected = (Path(os.environ["RUNNER_TEMP"]) /
        f"sim2act-record-pg-{os.environ['GITHUB_RUN_ID']}-1" / "private.json").resolve()
    if Path(path).resolve() != expected:
        raise ValueError("Only this run's private PG configuration is accepted")
    cfg = json.loads(expected.read_text(encoding="utf-8"))
    owner, runtime = (make_url(cfg[key]) for key in ("owner_url", "runtime_url"))
    if (cfg["sha"] != os.environ["GITHUB_SHA"] or owner.host != "127.0.0.1"
            or runtime.host != owner.host or runtime.port != owner.port
            or type(owner.port) is not int or not 1 <= owner.port <= 65535 or owner.port != cfg["port"]
            or runtime.database != owner.database or owner.database != cfg["database"] or owner.username != cfg["owner"]
            or runtime.username != cfg["app"] or not re.fullmatch(r"record_app_[a-f0-9]{32}", cfg["app"])):
        raise ValueError("The owned database and runtime identity must match")
    return cfg


def environment(tmp_path, path):
    cfg = private_config(path)
    schema = new_id("test")
    owner = Store(cfg["owner_url"], test_only=True)
    runtime = None
    client = None
    created = False
    role_proof = None
    try:
        with owner.engine.begin() as c:
            c.execute(text(f'CREATE SCHEMA "{schema}"'))
        created = True
        owner.engine = owner.engine.execution_options(schema_translate_map={None: schema})
        owner.initialize(fresh_test_schema=schema)
        with owner.engine.begin() as c:
            role = c.dialect.identifier_preparer.quote(cfg["app"])
            c.execute(text(f'GRANT USAGE ON SCHEMA "{schema}" TO {role}'))
            c.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "{schema}" TO {role}'))
        runtime = Store(cfg["runtime_url"], test_only=True)
        runtime.engine = runtime.engine.execution_options(schema_translate_map={None: schema})
        with runtime.engine.connect() as c:
            role = c.execute(text("SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
                "FROM pg_roles WHERE rolname=current_user")).one()
            role_proof = dict(zip(["superuser", "create_database", "create_role", "replication", "bypass_rls"], role, strict=True))
            assert not any(role)
            assert c.execute(text("SELECT current_user")).scalar_one() == cfg["app"]
            assert not c.execute(text("SELECT has_schema_privilege(current_user, :schema, 'CREATE')"),
                dict(schema=schema)).scalar_one()
        a = runtime.user("fixture A", "synthetic-test-A")
        b = runtime.user("fixture B", "synthetic-test-B")
        settings = Settings(cfg["runtime_url"], Path(tmp_path), mode="mock")
        client = TestClient(create_app(runtime, settings))
        client.headers.update({"Authorization": "Bearer synthetic-test-A"})
        pid = client.post("/api/projects", json={"name": "中文 空格工程"}).json()["id"]
        content = Path(__file__).with_name("fixtures").joinpath("f1.csv").read_text(encoding="utf-8")
        rid = client.post(f"/api/projects/{pid}/resources", json=dict(name="data.csv", format="csv", content=content)).json()["id"]
        yield runtime, settings, client, a, b, pid, rid
    finally:
        if client is not None:
            client.close()
        if runtime is not None:
            runtime.engine.dispose()
        dropped = False
        if created:
            with owner.engine.begin() as c:
                c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            dropped = True
        owner.engine.dispose()
        # No URLs/passwords in the role/fixture cleanup receipt.
        proof = Path(cfg["evidence"]) / "fixture-scopes"
        proof.mkdir(parents=True, exist_ok=True)
        (proof / (schema + ".json")).write_text(json.dumps(dict(schema=schema,
            runtime_role=cfg["app"], role_flags=role_proof, schema_dropped=dropped)), encoding="utf-8")

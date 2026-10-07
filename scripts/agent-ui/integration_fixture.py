"""Explicit synthetic integration fixture for the existing owned agent API."""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    app_drafts,
    attempts,
    fingerprint,
    grants,
    internal_app_runs,
    internal_instance_data,
    internal_run_bindings,
    principals,
    runs,
)
from sim2act.lifecycle import create_instance
from sim2act.worker import Worker


def context(root):
    url = "sqlite:///" + str(Path(root) / "fixture.db")
    return Store(url, test_only=True), Settings(url, Path(root), mode="mock")


def seed_integration(root):
    """Call only after original agent seed; existing identities, normal local API."""
    root = Path(root)
    info = json.loads((root / "info.json").read_text())
    store, settings = context(root)
    sys.path.insert(0, str(Path.cwd() / "tests"))
    from test_internal_lifecycle import limits, release

    owner = store.authenticate("synthetic-agent-ui-A")
    other = store.authenticate("synthetic-agent-ui-B")
    with TestClient(create_app(store, settings)) as client:
        client.headers.update({"Authorization": "Bearer synthetic-agent-ui-A"})
        project = store.project(owner, "SYNTHETIC integrated user journey")
        other_project = store.project(owner, "SYNTHETIC integrated empty owned")
        foreign = store.project(other, "SYNTHETIC integrated identity B")
        resource = client.post(
            f"/api/projects/{project}/resources",
            json={
                "name": "integrated.csv",
                "format": "csv",
                "content": "amount,tax,memo\n5,1,x\n7,2,y\n",
            },
        ).json()["id"]
        app = client.post(
            f"/api/projects/{project}/apps/csv-preview",
            json={
                "name": "Integrated synthetic sum",
                "resource_id": resource,
                "goal": "Synthetic two numeric columns, fixed resource",
            },
        ).json()["id"]
        with store.tx() as c:
            fp = c.execute(
                select(app_drafts.c.fingerprint).where(app_drafts.c.id == app)
            ).scalar_one()
        env = (store, settings, client, owner, other, project, resource)
        rel, _, _ = release(env, app, fp)
        instance = create_instance(
            store,
            owner,
            rel["id"],
            rel["fingerprint"],
            limits(env),
            request_key="integration-preexisting-instance",
        )
        first = client.post(
            f"/api/projects/{project}/runs",
            json={
                "goal": "Integrated ordinary persisted sample",
                "resource_refs": [resource],
                "request_key": "integration-first",
            },
        ).json()["run_id"]
        with store.tx() as c:
            oldest = c.execute(
                select(runs.c.id)
                .where(runs.c.status == "QUEUED")
                .order_by(runs.c.created_at)
                .limit(1)
            ).scalar_one()
            assert oldest == first, "Refuse to reorder or consume an unrelated queued Run"
        assert Worker(store, settings).once()
        received = client.get("/api/runs/" + first).json()
        assert received["status"] == "PARTIAL" and received["result"]["mode"] == "MOCK"
        info["integration"] = {
            "project": project,
            "other": other_project,
            "foreignProject": foreign,
            "app": app,
            "appName": "Integrated synthetic sum",
            "instance": instance["id"],
            "first": first,
            "resource": resource,
            "identityA": "synthetic-agent-ui-A",
            "identityB": "synthetic-agent-ui-B",
        }
        # Existing authority baseline must be recorded after all explicit fixture setup.
        from test_executor_family_provenance import effects

        info["grant_count"] = effects(store)["grants"]
        (root / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
    store.engine.dispose()


def integration_worker(root, run_id):
    """Existing CLI action, never a new business or test HTTP endpoint."""
    root = Path(root)
    binding = json.loads((root / "info.json").read_text())["integration"]
    store, settings = context(root)
    try:
        assert store.test_only and settings.mode == "mock"
        with store.tx() as c:
            oldest = (
                c.execute(
                    select(runs)
                    .where(runs.c.status == "QUEUED")
                    .order_by(runs.c.created_at)
                    .limit(1)
                )
                .mappings()
                .one()
            )
            assert oldest["id"] == run_id and oldest["project_id"] == binding["project"], (
                "Target must be actual oldest QUEUED; never reset/reorder"
            )
            app_run_id = c.execute(
                select(internal_run_bindings.c.app_run_id).where(
                    internal_run_bindings.c.run_id == run_id
                )
            ).scalar_one()
            job = (
                c.execute(select(internal_app_runs).where(internal_app_runs.c.id == app_run_id))
                .mappings()
                .one()
            )
            assert job["instance_id"] == binding["instance"]
        assert Worker(store, settings).once()
        with store.tx() as c:
            selected = c.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
            assert selected["status"] == "SUCCEEDED"
        return {
            "status": "PASS",
            "target": run_id,
            "actual_worker": "normal Settings(mode=mock)",
            "real_provider_requests": 0,
        }
    finally:
        store.engine.dispose()


def integration_counts(root):
    root = Path(root)
    binding = json.loads((root / "info.json").read_text())["integration"]
    store, settings = context(root)
    try:
        assert store.test_only and settings.mode == "mock"
        with store.tx() as c:
            ids = list(
                c.execute(
                    select(runs.c.id).where(runs.c.project_id == binding["project"])
                ).scalars()
            )
            authority = {
                name: [
                    dict(row) for row in c.execute(select(table).order_by(table.c.id)).mappings()
                ]
                for name, table in [("grants", grants), ("principals", principals)]
            }
            return {
                "authority_fingerprint": fingerprint(authority),
                "grants": len(authority["grants"]),
                "principals": len(authority["principals"]),
                "application_runs": len(
                    c.execute(
                        select(internal_app_runs.c.id).where(
                            internal_app_runs.c.instance_id == binding["instance"]
                        )
                    ).all()
                ),
                "data_versions": list(
                    c.execute(
                        select(internal_instance_data.c.version)
                        .where(internal_instance_data.c.instance_id == binding["instance"])
                        .order_by(internal_instance_data.c.version)
                    ).scalars()
                ),
                "attempts": [
                    dict(row)
                    for row in c.execute(
                        select(attempts.c.mode, attempts.c.status).where(attempts.c.run_id.in_(ids))
                    ).mappings()
                ],
                "real_model_requests": 0,
            }
    finally:
        store.engine.dispose()

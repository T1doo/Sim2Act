"""Real HTTP routing hints never substitute for current origin/permission inspection."""

import copy

import pytest
from sqlalchemy import update
from test_conditional_run_bindings import env as bounded_env
from test_report_manifest_apps import promoted
from test_report_validated_origin import whole_database

from sim2act.db import app_drafts, grants


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


def test_owned_catalog_hints_route_families_without_accepting_origin(env, tmp_path):
    store, _, client, _, _, pid, *_ = env
    report, _, _, _, wires = promoted(env, tmp_path)
    csv_resource = client.post(
        f"/api/projects/{pid}/resources",
        json={"name": "routing.csv", "format": "csv", "content": "amount\n7\n9\n"},
    ).json()["id"]
    csv = client.post(
        f"/api/projects/{pid}/apps/csv-preview",
        json={"name": "CSV instance candidate", "resource_id": csv_resource, "goal": "sum"},
    )
    assert csv.status_code == 201, csv.text
    csv_id = csv.json()["id"]
    before = whole_database(store)
    catalog = client.get("/api/apps")
    assert catalog.status_code == 200
    items = {item["id"]: item for item in catalog.json()["items"]}
    assert items[report["id"]]["csv_instance_candidate"] is False
    assert items[csv_id]["csv_instance_candidate"] is True
    assert all("candidate" not in item and "fingerprint" not in item for item in items.values())
    assert catalog.json()["state"] == "PREVIEW_ONLY" and catalog.json()["publishable"] is False
    assert whole_database(store) == before

    # Other identity sees no routing hint or metadata for an unowned project.
    outsider = client.get("/api/apps", headers={"Authorization": "Bearer synthetic-test-B"})
    assert outsider.status_code == 200 and outsider.json()["items"] == []
    assert whole_database(store) == before

    # Unknown/malformed family gives no optimistic hint. Direct inspection still rejects it.
    original = report["candidate"]
    for actions in [None, [], [None], [{"executor": None}]]:
        damaged = copy.deepcopy(original)
        damaged["actions"] = actions
        with store.tx() as c:
            c.execute(update(app_drafts).where(app_drafts.c.id == report["id"]).values(candidate=damaged))
        damaged_before = whole_database(store)
        items = {item["id"]: item for item in client.get("/api/apps").json()["items"]}
        assert "csv_instance_candidate" not in items[report["id"]]
        inspected = client.get("/api/apps/" + report["id"])
        assert inspected.status_code == 409, inspected.text
        assert whole_database(store) == damaged_before
    with store.tx() as c:
        c.execute(update(app_drafts).where(app_drafts.c.id == report["id"]).values(candidate=original))

    # A static family hint does not certify current authorization or accept a cold Run.
    target = original["report_proof"]["target_resource_id"]
    with store.tx() as c:
        c.execute(update(grants).where(grants.c.project_id == pid, grants.c.resource_id == target).values(revoked=True))
    revoked_before = whole_database(store)
    items = {item["id"]: item for item in client.get("/api/apps").json()["items"]}
    assert items[report["id"]]["csv_instance_candidate"] is False
    denied = client.get("/api/apps/" + report["id"])
    assert denied.status_code == 403, denied.text
    assert whole_database(store) == revoked_before
    assert len(wires) == 3

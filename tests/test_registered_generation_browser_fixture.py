"""Browser fixture provisions initial CSV domains, never registered Run/generation gold."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from sim2act.api import create_app
from sim2act.db import app_drafts, internal_run_bindings, runs, task_extractions
from sim2act.errors import DomainError

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "registered_browser_fixture", REPO / "scripts/agent-ui/fixture.py"
)
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


@pytest.fixture
def browser_fixture(tmp_path):
    FIXTURE.seed(tmp_path, 8073)
    info = json.loads((tmp_path / "info.json").read_text())
    store, settings = FIXTURE.context(tmp_path)
    with TestClient(create_app(store, settings)) as client:
        client.headers["Authorization"] = "Bearer synthetic-agent-ui-A"
        yield tmp_path, info, store, client
    store.engine.dispose()


def action(root, name, *extra):
    process = subprocess.run(
        [
            sys.executable,
            "scripts/agent-ui/fixture.py",
            "--root",
            str(root),
            "--action",
            name,
            *extra,
        ],
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    return process.stdout.strip()


def source_run(fixture, empty=False):
    root, info, _, client = fixture
    app = info["empty_target_source_app"] if empty else info["registered_source_app"]
    draft = client.get(f"/api/apps/{app}").json()
    approval = client.post(
        f"/api/internal/apps/{app}/release-approvals",
        json={
            "expected_draft_fingerprint": draft["fingerprint"],
            "sample_input": {"column": "amount"},
        },
    )
    assert approval.status_code == 201, approval.text
    approved = approval.json()
    released = client.post(
        f"/api/internal/approvals/{approved['id']}/commit",
        json={
            "fingerprint": approved["fingerprint"],
        },
    )
    assert released.status_code == 200, released.text
    release = released.json()
    instance = client.post(
        f"/api/internal/releases/{release['id']}/instances",
        json={
            "expected_release_fingerprint": release["fingerprint"],
            "request_key": "fixture-source-instance",
        },
    ).json()
    queued = client.post(
        f"/api/internal/instances/{instance['id']}/runs",
        json={
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "input": {"column": "amount"},
            "request_key": "fixture-source-run",
        },
    )
    assert queued.status_code == 202, queued.text
    action(root, "worker")
    path = f"/api/internal/instances/{instance['id']}/runs/{queued.json()['run_id']}"
    result = client.get(path)
    assert result.status_code == 200 and result.json()["status"] == "SUCCEEDED"
    assert result.json()["result"]["sum"] == "3"
    return path


def generate(fixture, source_path, key="fixture-generation"):
    info, client = fixture[1], fixture[3]
    options = client.get(source_path + "/extraction-options")
    assert options.status_code == 200, options.text
    values = options.json()
    target = next(t for t in values["targets"] if t["id"] == info["registered_target_app"])
    body = {
        "expected_proof_fingerprint": values["proof_fingerprint"],
        "target_app_id": target["id"],
        "expected_target_draft_fingerprint": target["fingerprint"],
        "name": "Browser generated",
        "request_key": key,
    }
    created = client.post(source_path + "/extract", json=body)
    assert created.status_code == 201, created.text
    return created.json(), body


def test_seed_only_initial_registered_apps_and_final_authority_baseline(browser_fixture):
    root, info, store, client = browser_fixture
    assert info["csv_app"] == info["registered_source_app"]
    targets = {
        info["registered_source_resource"],
        info["registered_target_resource"],
        info["empty_target_source_resource"],
    }
    with store.tx() as c:
        assert all(
            not targets.intersection(r) for r in c.execute(select(runs.c.resource_refs)).scalars()
        )
        assert all(
            s.get("kind") != "registered_csv_source.v1"
            for s in c.execute(select(task_extractions.c.snapshot)).scalars()
        )
        for aid in [
            info["registered_source_app"],
            info["registered_target_app"],
            info["empty_target_source_app"],
        ]:
            candidate = c.execute(
                select(app_drafts.c.candidate).where(app_drafts.c.id == aid)
            ).scalar_one()
            assert candidate["manifest"]["origin"] == "goal" and "task_proof" not in candidate
        assert (
            c.execute(select(internal_run_bindings.c.run_id)).first() is not None
        )  # Old agent fixture preserved.
    assert client.get(f"/api/projects/{info['other_project']}/resources").json() == []
    assert (
        client.get(f"/api/resources/{info['registered_target_resource']}").json()["content"]
        == "amount,quantity\n10,7\n20,8\n"
    )
    baseline = json.loads(action(root, "generation-counts"))
    assert baseline["grants"] == info["grant_count"]
    assert all(set(r) == {"id", "name"} for r in baseline["principal_rows"])
    assert baseline["principal_fingerprint_fields"] == ["id", "name", "token_hash"]
    assert len(baseline["grant_fingerprint"]) == len(baseline["principal_fingerprint"]) == 64
    assert client.get(f"/api/apps/{info['derived_app']}").status_code == 200


def test_http_generation_cold_worker_and_precise_generated_only_corruption(browser_fixture):
    root, info, store, client = browser_fixture
    path = source_run(browser_fixture)
    baseline = FIXTURE.generation_counts(store)
    created, body = generate(browser_fixture, path)
    assert client.post(path + "/extract", json=body).json()["id"] == created["id"]
    after = FIXTURE.generation_counts(store)
    for field in ["grant_rows", "principal_rows", "grant_fingerprint", "principal_fingerprint"]:
        assert after[field] == baseline[field]
    draft = client.get(f"/api/apps/{created['id']}").json()
    approval = client.post(
        f"/api/internal/apps/{created['id']}/release-approvals",
        json={
            "expected_draft_fingerprint": draft["fingerprint"],
            "sample_input": {"column": "quantity"},
        },
    ).json()
    release = client.post(
        f"/api/internal/approvals/{approval['id']}/commit",
        json={"fingerprint": approval["fingerprint"]},
    ).json()
    instance = client.post(
        f"/api/internal/releases/{release['id']}/instances",
        json={
            "expected_release_fingerprint": release["fingerprint"],
            "request_key": "fixture-generated-instance",
        },
    ).json()
    job = client.post(
        f"/api/internal/instances/{instance['id']}/runs",
        json={
            "expected_revision": instance["revision"],
            "expected_release_fingerprint": release["fingerprint"],
            "input": {"column": "quantity"},
            "request_key": "fixture-generated-run",
        },
    ).json()
    action(root, "worker")
    result = client.get(f"/api/internal/instances/{instance['id']}/runs/{job['run_id']}").json()
    assert result["status"] == "SUCCEEDED" and result["result"]["sum"] == "15"
    assert result["result_version"] == 1
    corrupt, _ = generate(browser_fixture, path, "only-corrupt-this-second-app")
    for denied in [
        None,
        info["initial_app"],
        info["derived_app"],
        info["registered_source_app"],
        info["registered_target_app"],
        info["empty_target_source_app"],
    ]:
        with pytest.raises(DomainError):
            FIXTURE.generation_corrupt(store, info, denied)
    with store.tx() as c:
        marker = c.execute(
            select(task_extractions.c.snapshot).where(task_extractions.c.app_id == corrupt["id"])
        ).scalar_one()
    action(root, "generation-corrupt", "--app-id", corrupt["id"])
    assert client.get(f"/api/apps/{corrupt['id']}").status_code == 409
    assert client.get(f"/api/apps/{created['id']}").status_code == 200
    with store.tx() as c:
        assert (
            marker
            == c.execute(
                select(task_extractions.c.snapshot).where(
                    task_extractions.c.app_id == corrupt["id"]
                )
            ).scalar_one()
        )
    assert (
        FIXTURE.generation_counts(store)["principal_fingerprint"]
        == baseline["principal_fingerprint"]
    )


@pytest.mark.parametrize("source", [False, True])
def test_revoke_only_existing_selected_runtime_grants_and_refuse_cached_generation(
    browser_fixture, source
):
    root, info, store, client = browser_fixture
    path = source_run(browser_fixture)
    created, body = generate(browser_fixture, path)
    before = FIXTURE.generation_counts(store)
    action(root, "generation-source-revoke" if source else "generation-revoke")
    prefix = "registered_source" if source else "registered_target"
    expected = []
    changed = 0
    for row in before["grant_rows"]:
        row = dict(row)
        if (
            row["principal_id"] == info[prefix + "_runtime"]
            and row["resource_id"] == info[prefix + "_resource"]
        ):
            row.update(revoked=True, revision=row["revision"] + 1)
            changed += 1
        expected.append(row)
    after = FIXTURE.generation_counts(store)
    assert changed == 2 and after["grant_rows"] == expected
    assert after["principal_fingerprint"] == before["principal_fingerprint"]
    assert client.get(f"/api/apps/{created['id']}").status_code == 403
    assert client.post(path + "/extract", json=body).status_code == 403
    options = client.get(path + "/extraction-options")
    assert options.json()["error"]["code"] == ("GRANT_REVOKED" if source else "NEEDS_INPUT")
    assert client.get(f"/api/apps/{info['derived_app']}").status_code == 200


def test_empty_target_project_is_distinct_and_requires_real_source_completion(browser_fixture):
    root, info, store, client = browser_fixture
    assert info["empty_target_project"] not in {info["project"], info["other_project"]}
    path = source_run(browser_fixture, empty=True)
    response = client.get(path + "/extraction-options")
    assert response.json()["error"]["code"] == "NEEDS_INPUT"
    before = FIXTURE.generation_counts(store)
    client.headers["Authorization"] = "Bearer synthetic-agent-ui-B"
    assert client.get(path).status_code == 403
    assert client.get(path + "/extraction-options").status_code == 403
    assert FIXTURE.generation_counts(store) == before

"""Whole two-app project, real isolated Workers, synthetic models only."""

import copy
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_natural_logic_patches import prepared
from test_natural_spec_apps import COLD, material, ready, transport
from test_pb_natural_specs import drive_to_success
from test_spec_app_operations import snapshot

from sim2act import natural_logic_patches as logic
from sim2act import project_natural_revalidation as project
from sim2act.api import create_app
from sim2act.db import (
    Store,
    grants,
    internal_instance_data,
    internal_instances,
    internal_releases,
    runs,
)
from sim2act.worker import Worker


def cohort(env):
    # Generate a separate existing app before freezing either project's graph.
    data, aid, release, inst, _, path, _, _ = prepared(env)
    rid, goal = material(data[2], data[4], COLD, "Separate peer Goal")
    peer_data = (*data[:5], rid, goal)
    _, peer, peer_release, peer_inst, _ = ready(peer_data, "sequential")
    peer_app = data[2].get("/api/apps/" + peer).json()
    response = data[2].post(
        f"/api/projects/{data[4]}/apps/{peer}/delivery-graph/derive",
        json=dict(
            request_key="peer-anchor", expected_candidate_fingerprint=peer_app["fingerprint"]
        ),
    )
    assert response.status_code == 201, response.text
    base = f"/api/projects/{data[4]}/natural-revalidation"
    response = data[2].get(base + "/options")
    assert response.status_code == 200, response.text
    body = dict(
        request_key="project-two",
        expected_options_fingerprint=response.json()["options_fingerprint"],
        selections=[
            dict(
                app_id=aid,
                instance_id=inst["id"],
                preview_key="logic-edit",
                expected_preview_fingerprint=data[2]
                .get(path + "/previews/logic-edit")
                .json()["preview_fingerprint"],
            ),
            dict(
                app_id=peer,
                instance_id=peer_inst["id"],
                preview_key=None,
                expected_preview_fingerprint=None,
            ),
        ],
    )
    return data, aid, release, inst, path, peer, peer_release, peer_inst, base, body


def freeze(values):
    data, _, _, _, _, _, _, _, base, body = values
    response = data[2].post(base + "/plans", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def start(values, plan, aid):
    response = values[0][2].post(
        values[8] + "/plans/project-two/applications/" + aid + "/checks",
        json=dict(expected_plan_fingerprint=plan["plan_fingerprint"], consent=project.CONSENT),
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_two_apps_partial_then_complete_checks_and_cold_account(env, tmp_path):
    values = cohort(env)
    data, aid, release, inst, path, peer, peer_release, peer_inst, base, body = values
    before_peer = copy.deepcopy(data[2].get("/api/apps/" + peer).json())
    plan = freeze(values)
    assert len(plan["membership"]) == 2 and plan["project_revalidation_completed"] is False
    assert data[2].post(base + "/plans", json=body).json() == plan
    before = snapshot(data[0])
    omitted = {**body, "request_key": "omitted", "selections": body["selections"][:1]}
    assert data[2].post(base + "/plans", json=omitted).status_code == 409
    assert snapshot(data[0]) == before
    selected = start(values, plan, aid)
    sent = []
    drive_to_success(data, selected["run_id"], transport(sent))
    assert len(sent) == 2
    response = data[2].get(base + "/plans/project-two")
    assert response.status_code == 200, response.text
    ledger = response.json()
    assert ledger["local_checks_status"] == "PARTIAL"
    local = next(x for x in ledger["applications"] if x["app_id"] == aid)
    assert local["status"] == "PASS"
    assert (
        data[2]
        .post(
            path + "/version-approvals",
            json=dict(
                request_key="logic-edit",
                expected_check_fingerprint=local["local_check_fingerprint"],
                consent=logic.VERSION_CONSENT,
            ),
        )
        .status_code
        == 409
    )
    assert (
        data[2]
        .post(
            base + "/plans/project-two/version-approvals",
            json=dict(
                expected_plan_fingerprint=plan["plan_fingerprint"],
                expected_check_fingerprint=local["local_check_fingerprint"],
                consent=logic.VERSION_CONSENT,
            ),
        )
        .status_code
        == 409
    )
    checked = start(values, plan, peer)
    sent = []
    drive_to_success(data, checked["run_id"], transport(sent, COLD))
    assert len(sent) == 2
    assert "prior_items" in json.loads(sent[1]["messages"][1]["content"])["current_inputs"]
    assert checked["check_instance_id"] not in {
        inst["id"],
        peer_inst["id"],
        selected["check_instance_id"],
    }
    cold = Store(data[1].database_url, test_only=True)
    try:
        with TestClient(create_app(cold, data[1])) as client:
            client.headers["Authorization"] = "Bearer synthetic-test-A"
            response = client.get(base + "/plans/project-two")
            assert response.status_code == 200, response.text
            ledger = response.json()
            assert (
                ledger["local_checks_status"] == "PASS"
                and ledger["dependency_completeness"] == "BLOCKED_UNKNOWN"
            )
            assert ledger["project_revalidation_completed"] is False
            response = client.post(
                base + "/plans/project-two/version-approvals",
                json=dict(
                    expected_plan_fingerprint=plan["plan_fingerprint"],
                    expected_check_fingerprint=local["local_check_fingerprint"],
                    consent=logic.VERSION_CONSENT,
                ),
            )
            assert response.status_code == 201, response.text
            approval = response.json()["approval"]
            response = client.post(
                "/api/internal/approvals/" + approval["id"] + "/commit",
                json=dict(fingerprint=approval["fingerprint"]),
            )
            assert response.status_code == 200, response.text
            version = response.json()
            assert version["snapshot"]["draft"] == release["snapshot"]["draft"]
            response = client.get(base + "/plans/project-two/version-approval")
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "COMMITTED"
            assert client.get("/api/apps/" + peer).json() == before_peer
            assert client.get("/api/internal/releases/" + peer_release["id"]).json() == peer_release
            for source in [inst, peer_inst]:
                response = client.get("/api/internal/instances/" + source["id"])
                assert response.status_code == 200, response.text
                assert (
                    response.json()["data_version"] == 0
                    and response.json()["release_id"] == source["release_id"]
                )
            before = snapshot(cold)
            again = client.post(
                base + "/plans/project-two/applications/" + peer + "/checks",
                json=dict(
                    expected_plan_fingerprint=plan["plan_fingerprint"], consent=project.CONSENT
                ),
            )
            assert again.status_code == 202, again.text
            assert again.json() == checked
            assert snapshot(cold) == before
    finally:
        cold.engine.dispose()
    (tmp_path / "project-proof.json").write_text(
        json.dumps(
            dict(
                plan=plan,
                ledger=ledger,
                selected=selected,
                peer=checked,
                version=version,
                peer_draft=before_peer,
            ),
            indent=2,
        )
        + "\n"
    )


@pytest.mark.parametrize(
    "fault", ["peer_revoke", "peer_version", "peer_lock", "member_add", "cancel"]
)
def test_late_project_change_no_partial_save(env, fault):
    values = cohort(env)
    data, aid, _, _, _, peer, _, peer_inst, base, _ = values
    plan = freeze(values)
    accepted = start(values, plan, aid)
    sent = []

    def mutate(raw, payload):
        if fault == "peer_lock":
            anchor = data[2].get(f"/api/projects/{data[4]}/apps/{peer}/delivery-graph").json()
            node = next(x for x in anchor["graph"]["nodes"] if x["kind"] == "ACTION")
            response = data[2].post(
                f"/api/projects/{data[4]}/apps/{peer}/delivery-graph/manual-locks",
                json=dict(
                    expected_graph_fingerprint=anchor["graph_fingerprint"],
                    expected_graph_revision=anchor["graph_revision"],
                    change=dict(
                        node_id=node["id"],
                        expected_revision=node["revision"],
                        expected_content_fingerprint=node["content_fingerprint"],
                    ),
                    expected_lock_revision=0,
                    locked=True,
                    request_key="late-peer-lock",
                    consent="CONFIRM_EXACT_PROJECT_EDIT_LOCK",
                ),
            )
            assert response.status_code == 201, response.text
        else:
            with data[0].tx() as c:
                if fault == "peer_revoke":
                    resource = next(
                        x for x in plan["applications"] if x["context"]["app_id"] == peer
                    )["context"]["source"]["resource_id"]
                    c.execute(
                        update(grants).where(grants.c.resource_id == resource).values(revoked=True)
                    )
                elif fault == "peer_version":
                    c.execute(
                        update(internal_instances)
                        .where(internal_instances.c.id == peer_inst["id"])
                        .values(revision=peer_inst["revision"] + 1)
                    )
                elif fault == "cancel":
                    c.execute(
                        update(runs)
                        .where(runs.c.id == accepted["run_id"])
                        .values(cancel_intent=True)
                    )
                else:
                    from sim2act.db import app_drafts

                    row = dict(
                        c.execute(select(app_drafts).where(app_drafts.c.id == peer))
                        .mappings()
                        .one()
                    )
                    row["id"] = "app_" + "e" * 32
                    c.execute(app_drafts.insert().values(**row))

    worker = Worker(data[0], data[1], goal_planner_transport=transport(sent, mutate=mutate))
    assert worker.once()
    with data[0].tx() as c:
        assert (
            c.execute(
                select(internal_instance_data).where(
                    internal_instance_data.c.instance_id == accepted["check_instance_id"]
                )
            ).first()
            is None
        )
        assert len(c.execute(select(internal_releases.c.id)).all()) == 2
    assert len(sent) == 1
    assert data[2].get(base + "/plans/project-two").status_code != 200 or fault == "cancel"

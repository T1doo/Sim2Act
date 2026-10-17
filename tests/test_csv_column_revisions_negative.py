"""Successive CSV corruption, drift and stale CAS, actual Worker/NoModel.

SQL writes are limited to two deliberate coordinated-corruption cases.
"""

import copy
import json

import pytest
from sqlalchemy import select, update
from test_csv_column_revisions import adopted, assert_preserved, immutable_rows, proposal
from test_csv_goal_revisions import approve, drive, start
from test_csv_goal_revisions import raw_trace as raw_trace
from test_internal_lifecycle import limits
from test_spec_app_operations import snapshot

from sim2act import app_jobs as jobs
from sim2act import csv_goal_revisions as revision
from sim2act.db import attempts, delivery_graph_requests, fingerprint, internal_instances


def _receipt(response):
    return {"status": response.status_code, "body": response.json()}


def _resign_preview_pair(data, iid, body, value, fault):
    """Forge both matching seals and all advertised ordinary payload hashes.

    The genuine parent Release, its real CHECK/result and its sealed original
    preview are intentionally untouched. A valid ordinary checksum therefore
    cannot substitute for reconstruction from that independent parent.
    """
    forged = copy.deepcopy(value)
    if fault == "parent-resigned":
        actual = forged["context"]["parent"]["effective_fingerprint"]
        fake = "0" * 64 if actual != "0" * 64 else "1" * 64
        forged["context"]["parent"]["effective_fingerprint"] = fake
        # Keep the locally advertised parent-graph alias coherent as well.
        forged["parent_graph"]["candidate_fingerprint"] = fake
    else:
        assert fault == "binding-revision-resigned"
        candidate = forged["effective_candidate"]
        assert candidate["manifest"]["revision"] == 3
        assert candidate["manifest"]["action_bindings"][0]["revision"] == 3
        candidate["manifest"]["action_bindings"][0]["revision"] = 2
        forged["effective_fingerprint"] = fingerprint(candidate)
        forged["effective_graph"]["candidate_fingerprint"] = forged["effective_fingerprint"]
    forged["preview_fingerprint"] = fingerprint(
        {key: val for key, val in forged.items() if key != "preview_fingerprint"}
    )
    kinds = [revision.PREVIEW, revision.PREVIEW + "_seal"]
    with data[0].tx() as connection:
        rows = connection.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == iid,
            delivery_graph_requests.c.principal_id == data[3],
            delivery_graph_requests.c.kind.in_(kinds),
            delivery_graph_requests.c.request_key == body["request_key"],
        )).mappings().all()
        assert len(rows) == 2
        for row in rows:
            assert row["snapshot"] == {"request": body, "response": value}
            payload = {"request": copy.deepcopy(body), "response": copy.deepcopy(forged)}
            connection.execute(update(delivery_graph_requests).where(
                delivery_graph_requests.c.app_id == row["app_id"],
                delivery_graph_requests.c.principal_id == row["principal_id"],
                delivery_graph_requests.c.kind == row["kind"],
                delivery_graph_requests.c.request_key == row["request_key"],
            ).values(snapshot=payload, fingerprint=fingerprint(payload),
                     request_fingerprint=fingerprint(body)))
    # Demonstrate that rejection is not merely an unrecomputed ordinary hash.
    with data[0].tx() as connection:
        rows = connection.execute(select(delivery_graph_requests).where(
            delivery_graph_requests.c.app_id == iid,
            delivery_graph_requests.c.principal_id == data[3],
            delivery_graph_requests.c.kind.in_(kinds),
            delivery_graph_requests.c.request_key == body["request_key"],
        )).mappings().all()
        assert len(rows) == 2
        assert rows[0]["snapshot"] == rows[1]["snapshot"]
        for row in rows:
            assert row["fingerprint"] == fingerprint(row["snapshot"])
            assert row["request_fingerprint"] == fingerprint(row["snapshot"]["request"])
            answer = row["snapshot"]["response"]
            assert answer["preview_fingerprint"] == fingerprint(
                {key: val for key, val in answer.items() if key != "preview_fingerprint"}
            )
    return forged


def _reject_without_writes(data, invoke, expected_status, evidence, label):
    before = snapshot(data[0])
    response = invoke()
    after = snapshot(data[0])
    evidence[label] = {
        **_receipt(response),
        "before_database_fingerprint": fingerprint(before),
        "after_database_fingerprint": fingerprint(after),
    }
    assert response.status_code == expected_status, response.text
    assert after == before, label


@pytest.mark.parametrize("fault", [
    "parent-resigned",
    "binding-revision-resigned",
    "goal-drift-after-check",
    "permission-revoked-after-check",
    "cas-data-version",
])
def test_successive_revision_rejects_independent_parent_drift_and_stale_cas(env, tmp_path, fault):
    data, aid, base, current, path, previous, v2, goal, second = adopted(env)
    old_rows = immutable_rows(data)
    body, value = proposal(data, current, path, key="negative-" + fault)
    evidence = {
        "fault": fault,
        "app_id": aid,
        "business_instance_id": current["id"],
        "business_release_id": v2["id"],
        "business_revision": current["revision"],
        "business_data_version": current["data_version"],
        "old_v1_run_id": data[2].csv_previous_run["run_id"],
        "old_v2_run_id": second["run_id"],
        "original_proposal": value,
    }
    try:
        assert current["revision"] == 2 and current["data_version"] == 2
        assert value["context"]["goal"]["version"] == 2
        assert value["context"]["parent"]["effective_fingerprint"] == previous["effective_fingerprint"]
        assert value["spec_revision"] == 3
        if fault in {"parent-resigned", "binding-revision-resigned"}:
            forged = _resign_preview_pair(data, current["id"], body, value, fault)
            evidence["coordinated_resigned_proposal"] = forged
            _reject_without_writes(data,
                lambda: data[2].get(path + "/previews/" + body["request_key"]),
                409, evidence, "recover_forged_preview")
            _reject_without_writes(data,
                lambda: data[2].post(path + "/checks", json={
                    "request_key": body["request_key"],
                    "expected_preview_fingerprint": forged["preview_fingerprint"],
                    "consent": revision.CHECK_CONSENT,
                }), 409, evidence, "reject_forged_check_before_run_creation")
        else:
            accepted = start(data, path, value)
            drive(data, accepted["run_id"])
            proof_response = data[2].get(path + "/checks/" + body["request_key"])
            evidence["actual_check_receipt"] = _receipt(proof_response)
            assert proof_response.status_code == 200, proof_response.text
            proof = proof_response.json()
            assert proof["status"] == "PASS" and proof["run_id"] == accepted["run_id"]
            evidence["actual_check_run"] = accepted
            if fault == "goal-drift-after-check":
                cid = value["context"]["goal"]["card_id"]
                changed = data[2].put("/api/goal-cards/" + cid, json={
                    **goal, "goal": "明确下一目标，拒绝继续采用先前冻结的 Goal 2", "expected_version": 2,
                })
                evidence["explicit_goal_change"] = _receipt(changed)
                assert changed.status_code == 200, changed.text
            elif fault == "permission-revoked-after-check":
                listed = data[2].get(f"/api/projects/{data[5]}/grants")
                assert listed.status_code == 200, listed.text
                matches = [row for row in listed.json()
                    if row["principal_id"] == current["runtime_id"]
                    and row["resource_id"] == data[6]
                    and row["tool_ref"] == "resource.read" and not row["revoked"]]
                assert len(matches) == 1, matches
                grant = matches[0]
                revoked = data[2].post("/api/grants/" + grant["id"] + "/revoke", json={
                    "command": "revoke", "version": grant["revision"],
                })
                evidence["explicit_grant_revocation"] = {"grant": grant, **_receipt(revoked)}
                assert revoked.status_code == 200, revoked.text
            else:
                assert fault == "cas-data-version"
                version = approve(data, path, value)
                preparation = data[2].post(path + "/adoption-approvals", json={
                    "request_key": body["request_key"], "expected_revision": current["revision"],
                    "target_release_id": version["id"],
                    "expected_target_fingerprint": version["fingerprint"],
                })
                evidence["adoption_preparation"] = _receipt(preparation)
                assert preparation.status_code == 201, preparation.text
                approval_response = data[2].get(path + "/adoption-approvals/" + body["request_key"])
                evidence["adoption_read"] = _receipt(approval_response)
                assert approval_response.status_code == 200, approval_response.text
                approval = approval_response.json()
                # A real successful current-v2 use changes only data version,
                # after the exact adoption approval has already been issued.
                intervening = jobs.enqueue(data[0], data[3], current["id"], current["revision"],
                    v2["fingerprint"], {"column": "quantity"}, "intervening-cas-data-version",
                    limits(data), csv_review="FREEZE_SUM_ONLY_WITHOUT_MD")
                drive(data, intervening["run_id"])
                result = jobs.inspect_job(data[0], data[3], intervening["run_id"])
                assert result["result"]["sum"] == "5" and result["result_version"] == 3
                evidence["intervening_actual_run"] = result
                _reject_without_writes(data,
                    lambda: data[2].post(
                        f"/api/internal/instances/{current['id']}/switch-approvals/{approval['id']}/commit",
                        json={"fingerprint": approval["fingerprint"]}),
                    409, evidence, "reject_stale_adoption_commit")
            if fault != "cas-data-version":
                _reject_without_writes(data,
                    lambda: data[2].post(path + "/version-approvals", json={
                        "request_key": body["request_key"],
                        "expected_check_fingerprint": proof["check_fingerprint"],
                        "consent": revision.VERSION_CONSENT,
                    }), 403 if fault == "permission-revoked-after-check" else 409,
                    evidence, "reject_checked_version_approval")
        with data[0].tx() as connection:
            actual = dict(connection.execute(select(internal_instances).where(
                internal_instances.c.id == current["id"])).mappings().one())
            assert connection.execute(select(attempts.c.id)).first() is None
        evidence["business_instance_after_rejection"] = actual
        assert actual["release_id"] == v2["id"] and actual["revision"] == 2
        assert actual["data_version"] == (3 if fault == "cas-data-version" else 2)
        assert_preserved(data, old_rows)
        evidence["old_raw_rows_preserved"] = True
        evidence["model_attempt_count"] = 0
    finally:
        (tmp_path / "actual-successive-negative.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )

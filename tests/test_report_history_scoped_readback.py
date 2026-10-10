"""Real multi-definition history proves each check against its own archived output."""

import copy

import pytest
from sqlalchemy import select, update
from test_conditional_run_bindings import env as bounded_env
from test_delivery_graph_apps import snapshot
from test_report_presentations import prepared

from sim2act.db import delivery_graph_requests as requests
from sim2act.db import fingerprint, grants


@pytest.fixture
def env(env):
    return bounded_env.__wrapped__(env)


@pytest.mark.parametrize("damage", ["coherent_check", "expired_owner_source"])
def test_multi_definition_cold_history_keeps_real_readback_and_fresh_authority(
    env, tmp_path, damage
):
    app, _, url, body, output, wires = prepared(env, tmp_path)
    expected = {}
    for key, count in [("first-text", 2), ("second-text", 1)]:
        definition = {**body, "request_key": key}
        proposed = env[2].post(url, json=definition)
        assert proposed.status_code == 201, proposed.text
        patch = proposed.json()
        expected[patch["patch_fingerprint"]] = []
        for n in range(count):
            checked = env[2].post(
                url + "/" + key + "/checks",
                json={
                    "expected_patch_fingerprint": patch["patch_fingerprint"],
                    "request_key": f"{key}-{n}",
                },
            )
            assert checked.status_code == 201, checked.text
            expected[patch["patch_fingerprint"]].append(checked.json()["check_fingerprint"])
    before = snapshot(env)
    cold = env[2].get(url)
    assert cold.status_code == 200, cold.text
    history = cold.json()
    assert len(history["items"]) == 2
    for item in history["items"]:
        assert [v["check_fingerprint"] for v in item["checks"]] == expected[
            item["patch"]["patch_fingerprint"]
        ]
        assert all(
            v["text"] == output["explanation"] and v["baseline_text"] == "ALLOW"
            for v in item["checks"]
        )
        assert all(v["result_binding"] == item["patch"]["result_binding"] for v in item["checks"])
    assert all(
        item["patch"]["project_revalidation_status"] == "BLOCKED_PARTIAL"
        for item in history["items"]
    )
    assert history["owner_acceptance"] == "PENDING" and history["semantic_status"] == "UNKNOWN"
    assert not history["formal_publication_enabled"]
    assert snapshot(env) == before
    with env[0].tx() as c:
        if damage == "coherent_check":
            rows = (
                c.execute(
                    select(requests).where(
                        requests.c.app_id == app["id"],
                        requests.c.request_key == "first-text-1",
                        requests.c.kind.in_(
                            ["report_presentation_check", "report_presentation_check_seal"]
                        ),
                    )
                )
                .mappings()
                .all()
            )
            assert len(rows) == 2
            for row in rows:
                value = copy.deepcopy(row["snapshot"])
                value["response"]["text"] = "coherently forged explanation"
                answer = value["response"]
                answer["check_fingerprint"] = fingerprint(
                    {k: v for k, v in answer.items() if k != "check_fingerprint"}
                )
                c.execute(
                    update(requests)
                    .where(
                        requests.c.app_id == row["app_id"],
                        requests.c.principal_id == row["principal_id"],
                        requests.c.kind == row["kind"],
                        requests.c.request_key == row["request_key"],
                    )
                    .values(snapshot=value, fingerprint=fingerprint(value))
                )
        else:
            source = app["candidate"]["report_proof"]["source_resource_id"]
            changed = c.execute(
                update(grants)
                .where(
                    grants.c.project_id == env[5],
                    grants.c.principal_id == env[3],
                    grants.c.resource_id == source,
                )
                .values(expires_at=0)
            )
            assert changed.rowcount > 0
    damaged = snapshot(env)
    rejected = env[2].get(url)
    assert rejected.status_code in (403, 409), rejected.text
    assert snapshot(env) == damaged and len(wires) == 4

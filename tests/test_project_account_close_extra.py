import copy

from sqlalchemy import select
from test_project_account_close import check, close, one

from sim2act.db import delivery_graph_locks


def test_closed_history_after_public_switch_new_key_freezes_current_revision(env):
    data, aid, release, inst, _, base, body, plan = one(env)
    client = data[2]
    response = close(client, base, plan)
    assert response.status_code == 200, response.text
    receipt = response.json()
    response = client.post(
        f"/api/internal/instances/{inst['id']}/switch-approvals",
        json=dict(
            target_release_id=release["id"],
            expected_target_fingerprint=release["fingerprint"],
            expected_revision=inst["revision"],
        ),
    )
    assert response.status_code == 201, response.text
    approval = response.json()
    response = client.post(
        f"/api/internal/instances/{inst['id']}/switch-approvals/{approval['id']}/commit",
        json=dict(fingerprint=approval["fingerprint"]),
    )
    assert response.status_code == 200, response.text
    adopted = response.json()
    assert adopted["revision"] == inst["revision"] + 1
    old = client.get(base + "/plans/" + plan["request_key"])
    assert old.status_code == 200, old.text
    assert old.json()["plan"] == plan and old.json()["close_receipt"] == receipt
    assert close(client, base, plan).json() == receipt
    options = client.get(base + "/options").json()
    next_body = copy.deepcopy(body)
    next_body.update(
        request_key="explicit-after-switch",
        expected_options_fingerprint=options["options_fingerprint"],
    )
    next_body["selections"][0].update(preview_key=None, expected_preview_fingerprint=None)
    response = client.post(base + "/plans", json=next_body)
    assert response.status_code == 201, response.text
    next_plan = response.json()
    assert next_plan["applications"][0]["context"]["instance_revision"] == adopted["revision"]
    assert next_plan["plan_fingerprint"] != plan["plan_fingerprint"]
    assert close(client, base, plan).json() == receipt
    assert (
        "project_source"
        in client.get("/api/internal/instances/" + inst["id"]).json()["switch_policy"]["roles"]
    )
    assert check(client, base, plan, aid).status_code == 409


def test_original_sixteen_historical_account_budget_is_not_refunded(env):
    data, _, _, _, _, base, body, plan = one(env)
    for index in range(1, 16):
        response = data[2].post(base + "/plans", json={**body, "request_key": f"history-{index}"})
        assert response.status_code == 201, response.text
    assert close(data[2], base, plan).status_code == 200
    response = data[2].post(base + "/plans", json={**body, "request_key": "seventeenth"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "BUDGET_EXCEEDED", (
        response.text
    )
    assert len(data[2].get(base + "/plans").json()["items"]) == 16


def test_preexisting_manual_lock_preserved_by_unmodified_account_close(env):
    data, aid, _, inst, _, base, body, _ = one(env)
    client = data[2]
    app = client.get("/api/apps/" + aid).json()
    anchor = client.get(f"/api/projects/{data[4]}/apps/{aid}/delivery-graph").json()
    node = next(n for n in anchor["graph"]["nodes"] if n["kind"] == "ACTION")
    response = client.post(
        f"/api/projects/{data[4]}/apps/{aid}/delivery-graph/manual-locks",
        json=dict(
            request_key="preexisting-lock",
            expected_graph_fingerprint=anchor["graph_fingerprint"],
            expected_graph_revision=anchor["graph_revision"],
            change=dict(
                node_id=node["id"],
                expected_revision=node["revision"],
                expected_content_fingerprint=node["content_fingerprint"],
            ),
            expected_lock_revision=0,
            locked=True,
            consent="CONFIRM_EXACT_PROJECT_EDIT_LOCK",
        ),
    )
    assert response.status_code == 201, response.text
    response = client.post(
        f"/api/projects/{data[4]}/apps/{aid}/delivery-graph/derive",
        json=dict(
            request_key="explicit-locked-derive", expected_candidate_fingerprint=app["fingerprint"]
        ),
    )
    assert response.status_code == 201, response.text
    graph = response.json()
    options = client.get(base + "/options").json()
    next_body = copy.deepcopy(body)
    next_body.update(
        request_key="locked-unmodified", expected_options_fingerprint=options["options_fingerprint"]
    )
    next_body["selections"][0].update(preview_key=None, expected_preview_fingerprint=None)
    response = client.post(base + "/plans", json=next_body)
    assert response.status_code == 201, response.text
    with data[0].tx() as c:
        before = [dict(x) for x in c.execute(select(delivery_graph_locks)).mappings()]
    assert close(client, base, response.json()).status_code == 200
    with data[0].tx() as c:
        after = [dict(x) for x in c.execute(select(delivery_graph_locks)).mappings()]
    assert before == after and before[0]["locked"]
    assert client.get(f"/api/projects/{data[4]}/apps/{aid}/delivery-graph").json() == graph
    assert (
        "project_source"
        in client.get("/api/internal/instances/" + inst["id"]).json()["switch_policy"]["roles"]
    )  # original stale unclosed account still protects


def test_rehashed_wrong_peer_closure_ref_never_releases_other_valid_source(env):
    from sqlalchemy import update
    from test_project_natural_revalidation import cohort, freeze

    from sim2act.db import delivery_graph_requests as markers
    from sim2act.db import fingerprint

    values = cohort(env)
    data, _, _, inst, _, _, _, peer_inst, base, _ = values
    plan = freeze(values)
    response = close(data[2], base, plan)
    assert response.status_code == 200, response.text
    forged = response.json()
    forged["released_sources"][1]["instance_id"] = "iinstance_" + "e" * 32
    forged["close_fingerprint"] = fingerprint(
        {k: v for k, v in forged.items() if k != "close_fingerprint"}
    )
    with data[0].tx() as c:
        rows = (
            c.execute(
                select(markers).where(
                    markers.c.kind.in_(
                        ["project-natural-check.v1.close", "project-natural-check.v1.close_seal"]
                    )
                )
            )
            .mappings()
            .all()
        )
        for row in rows:
            snap = copy.deepcopy(row["snapshot"])
            snap["response"] = forged
            c.execute(
                update(markers)
                .where(
                    markers.c.app_id == row["app_id"],
                    markers.c.kind == row["kind"],
                    markers.c.request_key == row["request_key"],
                )
                .values(snapshot=snap, fingerprint=fingerprint(snap))
            )
    for source in (inst, peer_inst):
        assert data[2].get("/api/internal/instances/" + source["id"]).status_code == 409
    assert data[2].get(base + "/plans/" + plan["request_key"]).status_code == 409


def test_closed_history_revocation_still_refuses_read_and_duplicate_close(env):
    from sqlalchemy import update

    from sim2act.db import grants

    data, _, _, inst, _, base, _, plan = one(env)
    assert close(data[2], base, plan).status_code == 200
    with data[0].tx() as c:
        c.execute(
            update(grants).where(grants.c.principal_id == inst["runtime_id"]).values(active=False)
        )
    response = data[2].get(base + "/plans/" + plan["request_key"])
    assert response.status_code in {400, 403}, response.text
    assert "source" not in response.json() and "plan" not in response.json()
    assert close(data[2], base, plan).status_code in {400, 403}


def test_rehashed_public_pointer_context_mismatch_rejects_before_plan_body(env, monkeypatch):
    from sqlalchemy import update

    from sim2act import project_natural_revalidation as project
    from sim2act.db import delivery_graph_requests as markers
    from sim2act.db import fingerprint

    data, _, release, _, _, base, _, plan = one(env)
    assert close(data[2], base, plan).status_code == 200
    response = data[2].post(
        f"/api/internal/releases/{release['id']}/instances",
        json=dict(
            expected_release_fingerprint=release["fingerprint"],
            request_key="authorized-alternative",
        ),
    )
    assert response.status_code == 201, response.text
    alternative = response.json()
    with data[0].tx() as c:
        rows = (
            c.execute(
                select(markers).where(markers.c.kind.in_([project.PLAN, project.PLAN + "_seal"]))
            )
            .mappings()
            .all()
        )
        for row in rows:
            snap = copy.deepcopy(row["snapshot"])
            snap["request"]["selections"][0]["instance_id"] = alternative["id"]
            # The published response context remains the original source.
            c.execute(
                update(markers)
                .where(
                    markers.c.app_id == row["app_id"],
                    markers.c.kind == row["kind"],
                    markers.c.request_key == row["request_key"],
                )
                .values(
                    snapshot=snap,
                    fingerprint=fingerprint(snap),
                    request_fingerprint=fingerprint(snap["request"]),
                )
            )
    pair = project.pair

    def guarded(*args, **kwargs):
        assert args[4] != project.PLAN, "No full PLAN body before public context identity guard"
        return pair(*args, **kwargs)

    monkeypatch.setattr(project, "pair", guarded)
    response = data[2].get(base + "/plans/" + plan["request_key"])
    assert response.status_code == 409, response.text

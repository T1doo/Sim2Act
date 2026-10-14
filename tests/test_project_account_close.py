"""Public SQLite unstarted-account closure, immutable history and actual CHECK use."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from test_natural_logic_patches import prepared
from test_natural_spec_apps import transport
from test_pb_natural_specs import drive_to_success
from test_project_natural_revalidation import cohort, freeze
from test_spec_app_operations import snapshot

from sim2act import natural_logic_patches as logic
from sim2act import project_natural_revalidation as project
from sim2act.api import create_app
from sim2act.db import (
    Store,
    grants,
    internal_instances,
    internal_run_bindings,
    runs,
)
from sim2act.db import (
    delivery_graph_requests as markers,
)
from sim2act.text_logic_reuse import remember


def one(env, key="close-original"):
    data, aid, release, inst, _, path, _, preview = prepared(env)
    client = data[2]
    base = f"/api/projects/{data[4]}/natural-revalidation"
    options = client.get(base + "/options").json()
    body = dict(
        request_key=key,
        expected_options_fingerprint=options["options_fingerprint"],
        selections=[
            dict(
                app_id=aid,
                instance_id=inst["id"],
                preview_key="logic-edit",
                expected_preview_fingerprint=preview["preview_fingerprint"],
            )
        ],
    )
    response = client.post(base + "/plans", json=body)
    assert response.status_code == 201, response.text
    return data, aid, release, inst, path, base, body, response.json()


def consent(plan):
    return dict(expected_plan_fingerprint=plan["plan_fingerprint"], consent=project.CLOSE_CONSENT)


def check(client, base, plan, aid):
    return client.post(
        base + f"/plans/{plan['request_key']}/applications/{aid}/checks",
        json=dict(expected_plan_fingerprint=plan["plan_fingerprint"], consent=project.CONSENT),
    )


def close(client, base, plan):
    return client.post(base + "/plans/" + plan["request_key"] + "/close", json=consent(plan))


def test_close_two_members_release_only_own_key_keep_history_and_next_real_worker(env):
    values = cohort(env)
    data, aid, release, inst, _, peer, _, peer_inst, base, body = values
    plan = freeze(values)
    client = data[2]
    original = snapshot(data[0])
    apps = {a: client.get("/api/apps/" + a).json() for a in (aid, peer)}
    before_graphs = {
        a: client.get(f"/api/projects/{data[4]}/apps/{a}/delivery-graph").json()
        for a in (aid, peer)
    }
    response = close(client, base, plan)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["account_status"] == "CLOSED_UNSTARTED"
    assert receipt["effect_known"] and receipt["executed_model_requests"] == 0
    assert receipt["isolated_check_instances_created"] == 0
    assert close(client, base, plan).json() == receipt
    after = snapshot(data[0])
    assert {k: v for k, v in after.items() if k != "delivery_graph_requests"} == {
        k: v for k, v in original.items() if k != "delivery_graph_requests"
    }
    assert all(
        row in after["delivery_graph_requests"] for row in original["delivery_graph_requests"]
    )
    assert len(after["delivery_graph_requests"]) == len(original["delivery_graph_requests"]) + 2
    for source in (inst, peer_inst):
        policy = client.get("/api/internal/instances/" + source["id"]).json()["switch_policy"]
        assert "project_source" not in policy["roles"]
    assert {a: client.get("/api/apps/" + a).json() for a in apps} == apps
    assert {
        a: client.get(f"/api/projects/{data[4]}/apps/{a}/delivery-graph").json() for a in apps
    } == before_graphs
    assert check(client, base, plan, aid).status_code == 409
    cold = Store(data[1].database_url, test_only=True)
    with TestClient(create_app(cold, data[1])) as reopened:
        reopened.headers["Authorization"] = "Bearer synthetic-test-A"
        ledger = reopened.get(base + "/plans/" + plan["request_key"]).json()
        assert ledger["plan"] == plan and ledger["close_receipt"] == receipt
        assert (
            ledger["local_checks_status"] == "NOT_RUN"
            and not ledger["project_revalidation_completed"]
        )
        assert (
            reopened.get(base + "/plans").json()["items"][0]["request_key"] == plan["request_key"]
        )
        current = reopened.get(base + "/options").json()
        new_body = {
            **body,
            "request_key": "explicit-next",
            "expected_options_fingerprint": current["options_fingerprint"],
        }
        response = reopened.post(base + "/plans", json=new_body)
        assert response.status_code == 201, response.text
        next_plan = response.json()
        assert next_plan["request_key"] != plan["request_key"]
        assert close(reopened, base, plan).json() == receipt
        assert (
            "project_source"
            in reopened.get("/api/internal/instances/" + inst["id"]).json()["switch_policy"][
                "roles"
            ]
        )
        result = check(reopened, base, next_plan, aid)
        assert result.status_code == 202, result.text
        sent = []
        drive_to_success(
            (cold, data[1], reopened, *data[3:]), result.json()["run_id"], transport(sent)
        )
        assert len(sent) == 2
        assert close(reopened, base, next_plan).status_code == 409
        assert (
            reopened.get(base + "/plans/" + plan["request_key"]).json()["close_receipt"] == receipt
        )
    cold.engine.dispose()


def test_other_account_stays_pinned_and_old_close_cannot_close_next(env):
    data, aid, _, inst, _, base, body, plan = one(env)
    client = data[2]
    other = client.post(base + "/plans", json={**body, "request_key": "other-open"}).json()
    assert close(client, base, plan).status_code == 200
    policy = client.get("/api/internal/instances/" + inst["id"]).json()["switch_policy"]
    assert "project_source" in policy["roles"]
    assert client.post(base + "/plans/other-open/close", json=consent(plan)).status_code == 409
    assert check(client, base, other, aid).status_code == 202
    assert close(client, base, plan).status_code == 200
    assert close(client, base, other).status_code == 409


@pytest.mark.parametrize(
    "fault", ["fingerprint", "consent", "identity", "revoke", "source_revision", "graph_lock"]
)
def test_close_exact_authority_version_and_lock_conflict_no_receipt(env, fault):
    data, aid, _, inst, _, base, _, plan = one(env)
    client = data[2]
    body = consent(plan)
    if fault == "fingerprint":
        body["expected_plan_fingerprint"] = "0" * 64
    elif fault == "consent":
        body["consent"] = "CANCEL"
    elif fault == "identity":
        client.headers["Authorization"] = "Bearer synthetic-test-B"
    elif fault == "revoke":
        with data[0].tx() as c:
            c.execute(
                update(grants)
                .where(grants.c.principal_id == inst["runtime_id"])
                .values(active=False)
            )
    elif fault == "source_revision":
        with data[0].tx() as c:
            c.execute(
                update(internal_instances)
                .where(internal_instances.c.id == inst["id"])
                .values(revision=2)
            )
    elif fault == "graph_lock":
        # Existing public lock API; source lock is never cleared by closure.
        graph = client.get(f"/api/projects/{data[4]}/apps/{aid}/delivery-graph").json()
        node = next(x for x in graph["graph"]["nodes"] if x["kind"] == "ACTION")
        response = client.post(
            f"/api/projects/{data[4]}/apps/{aid}/delivery-graph/manual-locks",
            json=dict(
                request_key="late-lock",
                expected_graph_fingerprint=graph["graph_fingerprint"],
                expected_graph_revision=graph["graph_revision"],
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
    before = snapshot(data[0])
    response = client.post(base + "/plans/" + plan["request_key"] + "/close", json=body)
    assert response.status_code in {403, 409, 422}, response.text
    assert snapshot(data[0]) == before
    with data[0].tx() as c:
        assert not c.execute(
            select(markers.c.request_key).where(
                markers.c.kind.in_([project.CLOSE, project.CLOSE + "_seal"])
            )
        ).first()


@pytest.mark.parametrize("remaining", ["all", "start_seal", "job_seal", "binding"])
def test_started_even_unclaimed_or_damaged_primary_indexes_cannot_close(env, remaining):
    data, aid, _, _, _, base, _, plan = one(env)
    accepted = check(data[2], base, plan, aid)
    assert accepted.status_code == 202, accepted.text
    if remaining != "all":
        with data[0].tx() as c:
            kinds = [project.START, project.START + "_seal", project.JOB, project.JOB + "_seal"]
            keep = {"start_seal": project.START + "_seal", "job_seal": project.JOB + "_seal"}.get(
                remaining
            )
            c.execute(delete(markers).where(markers.c.kind.in_([k for k in kinds if k != keep])))
            if remaining != "binding":
                bound = (
                    c.execute(
                        select(internal_run_bindings).where(
                            internal_run_bindings.c.run_id == accepted.json()["run_id"]
                        )
                    )
                    .mappings()
                    .one()
                )
                snap = copy.deepcopy(bound["snapshot"])
                snap.pop("project_check")
                c.execute(
                    update(internal_run_bindings)
                    .where(internal_run_bindings.c.run_id == bound["run_id"])
                    .values(snapshot=snap)
                )
    before = snapshot(data[0])
    assert close(data[2], base, plan).status_code == 409
    assert snapshot(data[0]) == before


@pytest.mark.parametrize("remaining", ["local_check", "local_job", "local_binding"])
def test_independent_local_check_consumption_survives_index_loss(env, remaining):
    data, _, _, _, path, base, _, plan = one(env)
    preview = data[2].get(path + "/previews/logic-edit").json()
    response = data[2].post(
        path + "/checks",
        json=dict(
            request_key="logic-edit",
            expected_preview_fingerprint=preview["preview_fingerprint"],
            consent=logic.CHECK_CONSENT,
        ),
    )
    assert response.status_code == 202, response.text
    if remaining != "local_check":
        with data[0].tx() as c:
            c.execute(
                delete(markers).where(markers.c.kind.in_([logic.CHECK, logic.CHECK + "_seal"]))
            )
            if remaining == "local_binding":
                c.execute(
                    delete(markers).where(markers.c.kind.in_([logic.JOB, logic.JOB + "_seal"]))
                )
            else:
                bound = (
                    c.execute(
                        select(internal_run_bindings).where(
                            internal_run_bindings.c.run_id == response.json()["run_id"]
                        )
                    )
                    .mappings()
                    .one()
                )
                snap = copy.deepcopy(bound["snapshot"])
                snap.pop("logic_check")
                c.execute(
                    update(internal_run_bindings)
                    .where(internal_run_bindings.c.run_id == bound["run_id"])
                    .values(snapshot=snap)
                )
    before = snapshot(data[0])
    assert close(data[2], base, plan).status_code == 409
    assert snapshot(data[0]) == before


@pytest.mark.parametrize(
    "fault", ["close_seal", "source_seal", "plan_seal", "wrong_sources", "contradictory_start"]
)
def test_closed_receipt_corruption_never_unlocks_or_reopens(env, fault):
    data, aid, _, inst, _, base, _, plan = one(env)
    assert close(data[2], base, plan).status_code == 200
    with data[0].tx() as c:
        if fault.endswith("_seal"):
            kind = {
                "close_seal": project.CLOSE,
                "source_seal": project.SOURCE,
                "plan_seal": project.PLAN,
            }[fault] + "_seal"
            c.execute(delete(markers).where(markers.c.kind == kind))
        elif fault == "wrong_sources":
            # Owned synthetic corruption: re-sealing one side is never sufficient.
            row = c.execute(select(markers).where(markers.c.kind == project.CLOSE)).mappings().one()
            snap = copy.deepcopy(row["snapshot"])
            snap["response"]["released_sources"][0]["instance_id"] = "iinstance_" + "f" * 32
            from sim2act.db import fingerprint

            c.execute(
                update(markers)
                .where(
                    (markers.c.app_id == row["app_id"])
                    & (markers.c.kind == row["kind"])
                    & (markers.c.request_key == row["request_key"])
                )
                .values(snapshot=snap, fingerprint=fingerprint(snap))
            )
        else:
            remember(
                c,
                data[3],
                data[4],
                project.START,
                plan["request_key"] + ":" + aid,
                project.Start(
                    expected_plan_fingerprint=plan["plan_fingerprint"], consent=project.CONSENT
                ),
                {},
            )
    assert data[2].get("/api/internal/instances/" + inst["id"]).status_code == 409
    assert data[2].get(base + "/plans/" + plan["request_key"]).status_code == 409
    assert check(data[2], base, plan, aid).status_code == 409


def test_close_vs_start_two_store_transactions_exactly_one_accepts(env, tmp_path):
    data, aid, _, inst, _, base, _, plan = one(env)
    with data[0].tx() as c:
        before_runs = set(c.execute(select(runs.c.id)).scalars())
    barrier = Barrier(2)

    def perform(action):
        store = Store(data[1].database_url, test_only=True)
        try:
            with TestClient(create_app(store, data[1])) as client:
                client.headers["Authorization"] = "Bearer synthetic-test-A"
                barrier.wait(timeout=10)
                response = (
                    close(client, base, plan)
                    if action == "close"
                    else check(client, base, plan, aid)
                )
                return action, response.status_code
        finally:
            store.engine.dispose()

    with ThreadPoolExecutor(2) as pool:
        results = dict(pool.map(perform, ["close", "start"]))
    assert sorted(results.values()) in ([200, 409], [202, 409]), results
    ledger = data[2].get(base + "/plans/" + plan["request_key"])
    assert ledger.status_code == 200, ledger.text
    with data[0].tx() as c:
        all_runs = set(c.execute(select(runs.c.id)).scalars()) - before_runs
    (tmp_path / "close-start-race.json").write_text(
        json.dumps(
            dict(
                results=results,
                new_run_ids=sorted(all_runs),
                account_status=ledger.json().get("account_status", "OPEN"),
            ),
            indent=2,
        )
        + "\n"
    )
    if results["close"] == 200:
        assert ledger.json()["account_status"] == "CLOSED_UNSTARTED"
        assert not all_runs
        assert (
            "project_source"
            not in data[2]
            .get("/api/internal/instances/" + inst["id"])
            .json()["switch_policy"]["roles"]
        )
    else:
        assert len(all_runs) == 1 and ledger.json()["applications"][0]["run_status"] == "QUEUED"
        assert close(data[2], base, plan).status_code == 409


def test_cancelled_accepted_check_still_cannot_close_account(env):
    data, aid, _, _, _, base, _, plan = one(env)
    response = check(data[2], base, plan, aid)
    assert response.status_code == 202, response.text
    accepted = response.json()
    run_path = f"/api/internal/instances/{accepted['check_instance_id']}/runs/{accepted['run_id']}"
    before = data[2].get(run_path).json()
    response = data[2].post(
        run_path + "/commands", json=dict(command="cancel", version=before["version"])
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED"
    before = snapshot(data[0])
    assert close(data[2], base, plan).status_code == 409
    assert snapshot(data[0]) == before

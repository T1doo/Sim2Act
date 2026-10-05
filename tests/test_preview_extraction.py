"""P-B engineering subset: trusted synthetic receipt -> fresh material -> cold result."""

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from test_goal_candidates import create_candidate, setup_card

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import (
    Store,
    app_drafts,
    app_previews,
    attempts,
    fingerprint,
    grants,
    operations,
    preview_extractions,
    principals,
    resources,
    runs,
)
from sim2act.errors import DomainError
from sim2act.extraction import exact_sum_oracle


def setup_source(env, client=None, extra=False):
    client = client or env[2]
    refs = [env[-1]]
    if extra:
        refs.append(
            client.post(
                f"/api/projects/{env[-2]}/resources",
                json={"name": "conditions.txt", "format": "txt", "content": "synthetic conditions"},
            ).json()["id"]
        )
    cid, goal = setup_card((*env[:2], client, *env[3:]), refs)
    aid = create_candidate((*env[:2], client, *env[3:]), cid).json()["id"]
    draft = client.get(f"/api/apps/{aid}").json()
    receipt = client.post(
        f"/api/apps/{aid}/previews", json={"input": {"column": "amount"}, "request_key": "source"}
    ).json()
    rid = client.post(
        f"/api/projects/{env[-2]}/resources",
        json={"name": "new.csv", "format": "csv", "content": "amount,quantity\n10,2\n30,3\n"},
    ).json()["id"]
    body = {
        "expected_source_fingerprint": draft["fingerprint"],
        "resource_id": rid,
        "name": "extracted",
        "request_key": "extract",
    }
    return aid, receipt, rid, body, goal


def counts(store):
    with store.engine.connect() as c:
        return {
            t.name: c.execute(select(func.count()).select_from(t)).scalar_one()
            for t in [
                app_drafts,
                app_previews,
                preview_extractions,
                principals,
                grants,
                runs,
                attempts,
                operations,
            ]
        }


def extract(client, receipt, body):
    return client.post(f"/api/previews/{receipt['id']}/extract", json=body)


def test_frozen_origin_and_cold_new_result_not_source_replay(env):
    store, settings, client, *_ = env
    aid, receipt, rid, body, goal = setup_source(env)
    before = counts(store)
    response = extract(client, receipt, body)
    assert response.status_code == 201, response.text
    extracted = response.json()["id"]
    draft = client.get(f"/api/apps/{extracted}").json()
    candidate = draft["candidate"]
    origin = candidate["extraction"]
    assert candidate["manifest"]["origin"] == "task_run"
    assert candidate["manifest"]["source_run_ref"] == receipt["id"]
    assert origin["namespace"] == "PREVIEW" and origin["source_app_id"] == aid
    assert origin["source_receipt"]["status"] == "SUCCEEDED"
    assert origin["source_receipt"]["output"]["sum"] == "4.00"
    assert origin["goal_acceptance"] == "NOT_RUN" and candidate["goal"] == goal
    assert origin["oracle"] == "csv.exact_integer_sum.v1" and origin["model_requests"] == 0
    assert origin["parameter_scope"] == {"creation": ["new_csv_resource"], "runtime": ["column"]}
    assert candidate["manifest"]["data_bindings"][0]["resource_ref"] == rid
    with store.engine.connect() as c:
        scopes = c.execute(
            select(grants.c.resource_id, grants.c.tool_ref).where(
                grants.c.principal_id == draft["runtime_id"]
            )
        ).all()
    assert set(scopes) == {(rid, "resource.read"), (rid, "data.aggregate_csv")}
    after = counts(store)
    assert after["app_drafts"] == before["app_drafts"] + 1
    assert (
        after["principals"] == before["principals"] + 1 and after["grants"] == before["grants"] + 2
    )
    assert after["runs"] == after["attempts"] == after["operations"] == 0
    with TestClient(create_app(store, settings)) as cold:
        cold.headers.update({"Authorization": "Bearer synthetic-test-A"})
        result = cold.post(
            f"/api/apps/{extracted}/previews",
            json={"input": {"column": "amount"}, "request_key": "cold"},
        ).json()
        assert result["status"] == "SUCCEEDED" and result["output"]["sum"] == "40"
        assert (
            result["output"]["resource_id"] == rid
            and result["output"]["source_hash"] != receipt["output"]["source_hash"]
        )
        other = cold.post(
            f"/api/apps/{extracted}/previews",
            json={"input": {"column": "quantity"}, "request_key": "other-column"},
        ).json()
        assert other["output"]["sum"] == "5"
        failure = cold.post(
            f"/api/apps/{extracted}/previews",
            json={"input": {"column": "missing"}, "request_key": "bad"},
        ).json()
        assert failure["status"] == "FAILED"
        assert [r["status"] for r in cold.get(f"/api/apps/{extracted}").json()["history"]] == [
            "FAILED",
            "SUCCEEDED",
            "SUCCEEDED",
        ]
        assert (
            extract(
                cold,
                result,
                {
                    **body,
                    "expected_source_fingerprint": draft["fingerprint"],
                    "resource_id": env[-1],
                },
            ).status_code
            == 400
        )


@pytest.mark.parametrize("status", ["FAILED", "UNKNOWN", "PARTIAL", "RUNNING", "CANCELLED"])
def test_ineligible_source_never_creates_candidate_or_authority(env, status):
    _, receipt, _, body, _ = setup_source(env)
    with env[0].tx() as c:
        c.execute(
            update(app_previews).where(app_previews.c.id == receipt["id"]).values(status=status)
        )
    before = counts(env[0])
    assert extract(env[2], receipt, body).status_code == 400
    assert counts(env[0]) == before


@pytest.mark.parametrize(
    "tamper",
    ["output", "input", "receipt_fp", "error", "source_hash", "source_content", "template"],
)
def test_source_tampering_blocks_extraction_without_side_effect(env, tamper):
    aid, receipt, _, body, _ = setup_source(env)
    with env[0].tx() as c:
        if tamper in {"output", "input", "receipt_fp", "error"}:
            value = {
                "output": {**receipt["output"], "sum": "999"},
                "input": {"column": "quantity"},
                "receipt_fp": "0" * 64,
                "error": {"code": "INVALID_INPUT"},
            }[tamper]
            c.execute(
                update(app_previews)
                .where(app_previews.c.id == receipt["id"])
                .values(**{("fingerprint" if tamper == "receipt_fp" else tamper): value})
            )
        elif tamper.startswith("source_"):
            c.execute(
                update(resources)
                .where(resources.c.id == env[-1])
                .values(**{("hash" if tamper == "source_hash" else "content"): "tampered"})
            )
        else:
            candidate = copy.deepcopy(
                c.execute(select(app_drafts.c.candidate).where(app_drafts.c.id == aid)).scalar_one()
            )
            candidate["manifest"]["workflow"][0]["inputs"]["column"] = {
                "source": "data",
                "ref": "source",
                "field": "resource_id",
            }
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == aid)
                .values(candidate=candidate, fingerprint=fingerprint(candidate))
            )
    before = counts(env[0])
    assert extract(env[2], receipt, body).status_code in [400, 409]
    assert counts(env[0]) == before


def test_cross_user_cross_project_original_input_and_f1_run_refused(env):
    _, receipt, _, body, _ = setup_source(env)
    client = env[2]
    other = client.post("/api/projects", json={"name": "other"}).json()["id"]
    foreign = client.post(
        f"/api/projects/{other}/resources",
        json={"name": "foreign.csv", "format": "csv", "content": "n\n9\n"},
    ).json()["id"]
    before = counts(env[0])
    assert extract(client, receipt, {**body, "resource_id": foreign}).status_code == 403
    assert extract(client, receipt, {**body, "resource_id": env[-1]}).status_code == 400
    client.headers.update({"Authorization": "Bearer synthetic-test-B"})
    assert extract(client, receipt, body).status_code == 403
    client.headers.update({"Authorization": "Bearer synthetic-test-A"})
    assert client.post("/api/previews/run_" + "a" * 32 + "/extract", json=body).status_code == 403
    assert counts(env[0]) == before


@pytest.mark.parametrize(
    "scope", ["user_source", "project_source", "app_source", "target", "source_extra"]
)
def test_withdrawal_blocks_extraction_and_readback(env, scope):
    aid, receipt, rid, body, goal = setup_source(env, extra=scope == "source_extra")
    extracted = extract(env[2], receipt, body).json()["id"]
    with env[0].tx() as c:
        source = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one()
        runtime = source["runtime_id"]
        who = (
            env[3]
            if scope in ["user_source", "target", "source_extra"]
            else runtime
            if scope == "app_source"
            else None
        )
        query = update(grants).where(
            grants.c.resource_id
            == (
                rid
                if scope == "target"
                else goal["resource_refs"][-1]
                if scope == "source_extra"
                else env[-1]
            ),
            grants.c.tool_ref == "resource.read",
        )
        if who:
            query = query.where(grants.c.principal_id == who)
        else:
            query = query.where(grants.c.principal_id.like("runtime_%"))
        c.execute(query.values(revoked=True))
    before = counts(env[0])
    assert extract(env[2], receipt, body).status_code == 403
    assert env[2].get(f"/api/apps/{extracted}").status_code == 403
    assert (
        env[2]
        .post(
            f"/api/apps/{extracted}/previews",
            json={"input": {"column": "amount"}, "request_key": "revoked"},
        )
        .status_code
        == 403
    )
    assert counts(env[0]) == before


@pytest.mark.parametrize(
    "tamper", ["provenance", "removed", "version", "wiring", "target_content", "receipt"]
)
def test_extracted_candidate_and_source_changes_refused_even_with_rehashed_candidate(env, tamper):
    _, receipt, rid, body, _ = setup_source(env)
    extracted = extract(env[2], receipt, body).json()["id"]
    with env[0].tx() as c:
        if tamper == "target_content":
            c.execute(
                update(resources).where(resources.c.id == rid).values(content="amount\n999\n")
            )
        elif tamper == "receipt":
            c.execute(
                update(app_previews)
                .where(app_previews.c.id == receipt["id"])
                .values(request_key="changed")
            )
        else:
            candidate = copy.deepcopy(
                c.execute(
                    select(app_drafts.c.candidate).where(app_drafts.c.id == extracted)
                ).scalar_one()
            )
            if tamper == "provenance":
                candidate["extraction"]["source_receipt"]["output"]["sum"] = "999"
            elif tamper == "removed":
                del candidate["extraction"]
            elif tamper == "version":
                candidate["manifest"]["dependency_lock"][1]["version"] = "99"
            else:
                candidate["manifest"]["outputs"]["sum"]["field"] = "column"
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == extracted)
                .values(candidate=candidate, fingerprint=fingerprint(candidate))
            )
    before = counts(env[0])
    assert env[2].get(f"/api/apps/{extracted}").status_code in [400, 409]
    assert env[2].post(
        f"/api/apps/{extracted}/previews",
        json={"input": {"column": "amount"}, "request_key": "bad"},
    ).status_code in [400, 409]
    assert counts(env[0]) == before


def test_idempotency_stale_version_and_concurrent_single_authority(env):
    _, receipt, rid, body, _ = setup_source(env)
    before = counts(env[0])

    def submit(_):
        with TestClient(create_app(env[0], env[1])) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            response = extract(client, receipt, body)
            assert response.status_code == 201, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(submit, [1, 2]))
    assert first == second
    after = counts(env[0])
    assert (
        after["app_drafts"] == before["app_drafts"] + 1 and after["grants"] == before["grants"] + 2
    )
    assert extract(env[2], receipt, body).json() == first
    assert extract(env[2], receipt, {**body, "name": "different"}).status_code == 409
    assert (
        extract(
            env[2],
            receipt,
            {**body, "expected_source_fingerprint": "0" * 64, "request_key": "stale"},
        ).status_code
        == 409
    )
    assert counts(env[0]) == after


@pytest.mark.parametrize(
    "extra", [{"executor": "shell"}, {"model": "live"}, {"source_run": "fake"}]
)
def test_closed_input_no_execution_or_model_options(env, extra):
    _, receipt, _, body, _ = setup_source(env)
    before = counts(env[0])
    assert extract(env[2], receipt, {**body, **extra}).status_code == 422
    assert counts(env[0]) == before


def test_independent_oracle_refuses_rounding_and_unbounded_numbers():
    exact_sum_oracle("n\n1.25\n2.75\n", "n", {"count": 2, "sum": "4.00"})
    for content, output in [
        ("n\n10000000000000000000000000000\n1\n", {"count": 2, "sum": "1E28"}),
        ("n\n1e1001\n", {"count": 1, "sum": "1e1001"}),
    ]:
        with pytest.raises(DomainError, match="源回执"):
            exact_sum_oracle(content, "n", output)


def test_direct_template_completed_receipt_is_supported_without_goal_card(env):
    client = env[2]
    source = client.post(
        f"/api/projects/{env[-2]}/apps/csv-preview",
        json={"name": "direct source", "resource_id": env[-1], "goal": "synthetic sum"},
    ).json()["id"]
    draft = client.get(f"/api/apps/{source}").json()
    receipt = client.post(
        f"/api/apps/{source}/previews",
        json={"input": {"column": "amount"}, "request_key": "source"},
    ).json()
    rid = client.post(
        f"/api/projects/{env[-2]}/resources",
        json={"name": "new.csv", "format": "csv", "content": "n\n42\n"},
    ).json()["id"]
    response = extract(
        client,
        receipt,
        {
            "expected_source_fingerprint": draft["fingerprint"],
            "resource_id": rid,
            "name": "direct extracted",
            "request_key": "direct",
        },
    )
    assert response.status_code == 201, response.text
    candidate = client.get(f"/api/apps/{response.json()['id']}").json()["candidate"]
    assert candidate["extraction"]["source_generation"] is None
    assert candidate["goal"] == draft["candidate"]["goal"]


def test_failure_after_candidate_authority_creation_rolls_back_entire_extraction(env, monkeypatch):
    from sim2act import extraction

    _, receipt, _, body, _ = setup_source(env)
    before = counts(env[0])
    original = extraction.persist_csv_candidate

    def fail(*args):
        original(*args)
        raise DomainError("VERIFICATION_FAILED", "synthetic persistence failure")

    monkeypatch.setattr(extraction, "persist_csv_candidate", fail)
    assert extract(env[2], receipt, body).status_code == 400
    assert counts(env[0]) == before


def test_pg_business_role_uses_explicit_migration_and_entire_extraction_path(env, runtime_role):
    store = Store(runtime_role)
    settings = Settings(runtime_role, env[1].data_dir, mode="mock")
    try:
        with TestClient(create_app(store, settings)) as client:
            client.headers.update({"Authorization": "Bearer synthetic-test-A"})
            _, receipt, _, body, _ = setup_source(env, client)
            first = extract(client, receipt, body)
            assert first.status_code == 201, first.text
            assert extract(client, receipt, body).json() == first.json()
            aid = first.json()["id"]
            assert client.get(f"/api/apps/{aid}").status_code == 200
            result = client.post(
                f"/api/apps/{aid}/previews",
                json={"input": {"column": "amount"}, "request_key": "role"},
            ).json()
            assert result["status"] == "SUCCEEDED" and result["output"]["sum"] == "40"
    finally:
        store.engine.dispose()

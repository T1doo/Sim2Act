"""Local synthetic browser fixture; initial authorization and explicit scoped faults only."""

import argparse
import asyncio
import copy
import json
import sys
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import select, update

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from test_bounded_agent_apps import (
    candidate,
    extract_agent_candidate,
    limits,
    replay,
    run,
    setup,
    verified_source,
)
from test_executor_family_provenance import effects

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.db import Store, app_drafts, fingerprint, grants, principals, task_extractions
from sim2act.errors import DomainError
from sim2act.worker import Worker


def context(root):
    url = "sqlite:///" + str(root / "fixture.db")
    return Store(url, test_only=True), Settings(url, root, mode="mock")


class NeverProvider:
    def request(self, *_):
        raise AssertionError("Browser fixture local worker must never call a model/provider")


def generation_counts(store):
    """Full authority comparison without emitting authentication token hashes."""
    with store.tx() as c:
        grant_rows = [dict(r) for r in c.execute(select(grants).order_by(grants.c.id)).mappings()]
        identities = [
            dict(r) for r in c.execute(select(principals).order_by(principals.c.id)).mappings()
        ]
    return {
        **effects(store),
        "principals": len(identities),
        "grant_rows": grant_rows,
        "grant_fingerprint": fingerprint(grant_rows),
        "grant_fingerprint_fields": [
            "id",
            "principal_id",
            "project_id",
            "resource_id",
            "tool_ref",
            "expires_at",
            "revision",
            "revoked",
        ],
        "principal_rows": [{"id": r["id"], "name": r["name"]} for r in identities],
        "principal_fingerprint": fingerprint(identities),
        "principal_fingerprint_fields": ["id", "name", "token_hash"],
    }


def generation_corrupt(store, info, app_id):
    """Only a server-generated registered candidate in this fixture's project."""
    if not isinstance(app_id, str):
        raise DomainError("INVALID_INPUT", "Explicit generated --app-id required")
    with store.tx() as c:
        draft = (
            c.execute(
                select(app_drafts).where(
                    app_drafts.c.id == app_id, app_drafts.c.project_id == info["project"]
                )
            )
            .mappings()
            .first()
        )
        marker = (
            c.execute(select(task_extractions).where(task_extractions.c.app_id == app_id))
            .mappings()
            .first()
        )
        if (
            not draft
            or not marker
            or marker["snapshot"].get("kind") != "registered_csv_source.v1"
            or draft["candidate"].get("task_proof", {}).get("proof", {}).get("kind")
            != "completed_registered_csv_apprun.v1"
        ):
            raise DomainError(
                "PERMISSION_DENIED", "Registered generated app in fixture project only"
            )
        candidate_value = copy.deepcopy(draft["candidate"])
        candidate_value["task_proof"]["proof"]["source_hash"] = "0" * 64
        c.execute(
            update(app_drafts)
            .where(app_drafts.c.id == app_id)
            .values(candidate=candidate_value, fingerprint=fingerprint(candidate_value))
        )


def generation_revoke(store, info, *, source=False):
    prefix = "registered_source" if source else "registered_target"
    with store.tx() as c:
        c.execute(
            update(grants)
            .where(
                grants.c.project_id == info["project"],
                grants.c.principal_id == info[prefix + "_runtime"],
                grants.c.resource_id == info[prefix + "_resource"],
                grants.c.tool_ref.in_(["resource.read", "data.aggregate_csv"]),
                grants.c.revoked.is_(False),
            )
            .values(revoked=True, revision=grants.c.revision + 1)
        )


def seed(root, port):
    root.mkdir(parents=True, exist_ok=True)
    store, settings = context(root)
    store.initialize()
    user = store.user("SYNTHETIC agent UI A", "synthetic-agent-ui-A")
    other = store.user("SYNTHETIC agent UI B", "synthetic-agent-ui-B")
    with TestClient(create_app(store, settings)) as client:
        client.headers.update({"Authorization": "Bearer synthetic-agent-ui-A"})
        pid = client.post("/api/projects", json={"name": "SYNTHETIC agent 当前项目"}).json()["id"]
        other_project = client.post("/api/projects", json={"name": "SYNTHETIC 无关项目"}).json()[
            "id"
        ]
        csv = client.post(
            f"/api/projects/{pid}/resources",
            json={"name": "fixture.csv", "format": "csv", "content": "amount\n1\n2\n"},
        ).json()["id"]
        env = (store, settings, client, user, other, pid, csv)
        runtime, ids, texts, aid, cand, rel, inst, value = setup(env)
        source, result = run(env, inst, rel, ids[0], value, key="preexisting-trusted-source")
        assert result["status"] == "SUCCEEDED"
        with store.tx() as c:
            proof = verified_source(store, c, user, source["run_id"], limits(env))
        derived = extract_agent_candidate(
            store,
            user,
            source["run_id"],
            fingerprint(proof),
            candidate(ids[1], texts[1]),
            runtime,
            "已完成任务的 agent 候选",
            "preexisting-extraction",
            limits(env),
        )
        from test_bounded_agent_apps import output

        new_value = output(ids[1], texts[1], "source_b")
        with store.tx() as c:
            drafts = list(c.execute(select(app_drafts)).mappings())
            csv_app = next(
                d["id"]
                for d in drafts
                if d["candidate"]["actions"][0]["executor"]["kind"] == "registered_tool"
            )
        # Only initial authenticated CSV apps and their already-authorized domains
        # are provisioned here. The browser must create the registered source Run
        # and call the real generation endpoint; no registered result/candidate seed.
        target_resource = client.post(
            f"/api/projects/{pid}/resources",
            json={
                "name": "generation-target.csv",
                "format": "csv",
                "content": "amount,quantity\n10,7\n20,8\n",
            },
        ).json()["id"]
        target_app = client.post(
            f"/api/projects/{pid}/apps/csv-preview",
            json={
                "name": "已有新 CSV 授权域",
                "resource_id": target_resource,
                "goal": "SYNTHETIC existing target authorization domain",
            },
        ).json()["id"]
        with store.tx() as c:
            target_runtime = c.execute(
                select(app_drafts.c.runtime_id).where(app_drafts.c.id == target_app)
            ).scalar_one()
            source_runtime = c.execute(
                select(app_drafts.c.runtime_id).where(app_drafts.c.id == csv_app)
            ).scalar_one()
        empty_project = client.post(
            "/api/projects", json={"name": "SYNTHETIC 无不同 CSV 授权域"}
        ).json()["id"]
        empty_resource = client.post(
            f"/api/projects/{empty_project}/resources",
            json={"name": "only-source.csv", "format": "csv", "content": "amount\n1\n2\n"},
        ).json()["id"]
        empty_app = client.post(
            f"/api/projects/{empty_project}/apps/csv-preview",
            json={
                "name": "仅有来源 CSV",
                "resource_id": empty_resource,
                "goal": "SYNTHETIC no distinct target domain",
            },
        ).json()["id"]
        with store.tx() as c:
            empty_runtime = c.execute(
                select(app_drafts.c.runtime_id).where(app_drafts.c.id == empty_app)
            ).scalar_one()
        info = {
            "port": port,
            "project": pid,
            "other_project": other_project,
            "initial_app": aid,
            "derived_app": derived["id"],
            "csv_app": csv_app,
            "registered_source_app": csv_app,
            "registered_source_resource": csv,
            "registered_source_runtime": source_runtime,
            "registered_target_app": target_app,
            "registered_target_resource": target_resource,
            "registered_target_runtime": target_runtime,
            "empty_target_project": empty_project,
            "empty_target_source_app": empty_app,
            "empty_target_source_resource": empty_resource,
            "empty_target_source_runtime": empty_runtime,
            "resource_a": ids[0],
            "resource_b": ids[1],
            "term_a": value["term"],
            "term_b": new_value["term"],
            "grant_count": effects(store)["grants"],
            "source_run": source["run_id"],
        }
        (root / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
        (root / "initial-replay.json").write_text(
            json.dumps(replay(ids[0], value).responses, ensure_ascii=False)
        )
        (root / "derived-replay.json").write_text(
            json.dumps(replay(ids[1], new_value).responses, ensure_ascii=False)
        )
    store.engine.dispose()
    from integration_fixture import seed_integration
    seed_integration(root)
    print("PASS synthetic fixture seeded; existing read Grants established before UI counters")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8073)
    parser.add_argument(
        "--action",
        choices=[
            "seed",
            "serve",
            "worker",
            "revoke",
            "corrupt",
            "counts",
            "generation-counts",
            "generation-corrupt",
            "generation-revoke",
            "generation-source-revoke",
            "integration-worker",
            "integration-counts",
        ],
        required=True,
    )
    parser.add_argument(
        "--app-id", help="Exact server-generated registered app for generation-corrupt"
    )
    parser.add_argument("--run-id", help="Exact oldest queued integration AppRun")
    args = parser.parse_args()
    root = args.root
    if args.action == "seed":
        seed(root, args.port)
        return
    if args.action in {"integration-worker", "integration-counts"}:
        from integration_fixture import integration_counts, integration_worker
        if args.action == "integration-worker":
            assert args.run_id, "Exact integration Run required"
            print(json.dumps(integration_worker(root, args.run_id)))
        else:
            print(json.dumps(integration_counts(root)))
        return
    store, settings = context(root)
    info = json.loads((root / "info.json").read_text())
    if args.action == "worker":
        assert Worker(store, settings, NeverProvider()).once(), "No accepted local Run to process"
        print("PASS new cold default worker processed local AppRun; provider forbidden")
    elif args.action == "generation-counts":
        print(json.dumps(generation_counts(store), ensure_ascii=False))
    elif args.action == "generation-corrupt":
        generation_corrupt(store, info, args.app_id)
        print("PASS exact registered generated candidate rehashed; independent marker retained")
    elif args.action == "generation-revoke":
        generation_revoke(store, info)
        print("PASS existing generation target runtime Grants revoked; other Grants retained")
    elif args.action == "generation-source-revoke":
        generation_revoke(store, info, source=True)
        print("PASS existing generation source runtime Grants revoked; other Grants retained")
    elif args.action == "revoke":
        with store.tx() as c:
            c.execute(
                update(grants)
                .where(grants.c.resource_id == info["resource_a"])
                .values(revoked=True)
            )
        print("PASS synthetic current-source Grants revoked")
    elif args.action == "corrupt":
        with store.tx() as c:
            cand = copy.deepcopy(
                c.execute(
                    select(app_drafts.c.candidate).where(app_drafts.c.id == info["derived_app"])
                ).scalar_one()
            )
            cand["agent_provenance"]["source_hash"] = "0" * 64
            c.execute(
                update(app_drafts)
                .where(app_drafts.c.id == info["derived_app"])
                .values(candidate=cand, fingerprint=fingerprint(cand))
            )
        print(
            "PASS synthetic candidate and mutable fingerprint changed; independent extraction anchor retained"
        )
    elif args.action == "counts":
        print(json.dumps(effects(store)))
    else:
        app = create_app(store, settings)

        @app.middleware("http")
        async def deliberate_delay(request, call_next):
            if (
                (root / "delay-app").exists()
                and request.method == "GET"
                and request.url.path == f"/api/apps/{info['initial_app']}"
            ):
                await asyncio.sleep(1)
            return await call_next(request)

        uvicorn.run(app, host="127.0.0.1", port=info["port"], access_log=False)


if __name__ == "__main__":
    main()

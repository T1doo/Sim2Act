"""Local synthetic HTTP/DOM/protected-browser fixture; no production route or Grant change."""

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
from sim2act.db import Store, app_drafts, fingerprint, grants
from sim2act.worker import Worker


def context(root):
    url = "sqlite:///" + str(root / "fixture.db")
    return Store(url, test_only=True), Settings(url, root, mode="mock")


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
        info = {
            "port": port,
            "project": pid,
            "other_project": other_project,
            "initial_app": aid,
            "derived_app": derived["id"],
            "csv_app": csv_app,
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
    print("PASS synthetic fixture seeded; existing read Grants established before UI counters")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8073)
    parser.add_argument(
        "--action",
        choices=["seed", "serve", "worker", "revoke", "corrupt", "counts"],
        required=True,
    )
    args = parser.parse_args()
    root = args.root
    if args.action == "seed":
        seed(root, args.port)
        return
    store, settings = context(root)
    info = json.loads((root / "info.json").read_text())
    if args.action == "worker":
        Worker(store, settings).once()
        print("PASS new cold default worker processed accepted frozen Replay")
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

"""Owned offline browser experiment: persistent gates, projected egress, Intern + MockTransport."""

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import httpx
import uvicorn
from fastapi.testclient import TestClient
from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
from test_protocol_http import envelope  # noqa: E402

from sim2act.api import create_app  # noqa: E402
from sim2act.config import Settings  # noqa: E402
from sim2act.db import (  # noqa: E402
    Store,
    attempts,
    events,
    fingerprint,
    grants,
    principals,
    protocol_jobs,
    runs,
)
from sim2act.model import InternModel  # noqa: E402
from sim2act.model_budget import ENDPOINT, BudgetedProvider, initialize_ledger  # noqa: E402
from sim2act.protocol_api import ProtocolAttemptRunner  # noqa: E402
from sim2act.protocol_experiment import (  # noqa: E402
    BINDING,
    advance,
    bind_run,
    initialize_experiment,
    inspect_experiment,
)
from sim2act.protocol_pool import initialize_pools  # noqa: E402
from sim2act.protocol_readiness import (  # noqa: E402
    EVENT as HANDOFF_EVENT,
)
from sim2act.protocol_readiness import (
    candidate_for as canonical_candidate_for,
)
from sim2act.protocol_readiness import (
    prepare_handoff,
)
from sim2act.protocol_reviews import contract_snapshot, evaluation_contract, review  # noqa: E402
from sim2act.worker import Worker  # noqa: E402


def context(root):
    url = "sqlite:///" + str(root / "fixture.db")
    return Store(url, test_only=True), Settings(
        url, root, mode="mock", max_requests=3, max_repairs=0
    )


def counts(store):
    with store.tx() as c:
        authorities = [dict(r) for r in c.execute(select(grants).order_by(grants.c.id)).mappings()]
        people = [
            dict(r) for r in c.execute(select(principals).order_by(principals.c.id)).mappings()
        ]
        return {
            "grants": len(authorities),
            "grant_fingerprint": fingerprint(authorities),
            "principal_fingerprint": fingerprint(people),
            "attempts": c.execute(select(func.count()).select_from(attempts)).scalar_one(),
            "jobs": c.execute(select(func.count()).select_from(protocol_jobs)).scalar_one(),
            "runs": c.execute(select(func.count()).select_from(runs)).scalar_one(),
            "attempt_states": [
                {k: row[k] for k in ("run_id", "status", "response_model")}
                for row in c.execute(select(attempts).order_by(attempts.c.id)).mappings()
            ],
        }


def seed(root, port):
    assert not (root / "fixture.db").exists(), "Owned fixture must not reset existing records"
    root.mkdir(parents=True, exist_ok=True)
    store, settings = context(root)
    store.initialize()
    initialize_pools(store, offline_limit=14)
    user = store.user("Synthetic protocol browser A", "synthetic-protocol-browser-A")
    other_user = store.user("Synthetic protocol browser B", "synthetic-protocol-browser-B")
    project = store.project(user, "Registered protocol source and cold material")
    other_project = store.project(user, "Other owned protocol project")
    repo = Path(__file__).resolve().parents[2]
    materials = repo / "docs/evidence/model-protocol-preparation-20261006/materials"
    with TestClient(
        create_app(store, settings),
        headers={"Authorization": "Bearer synthetic-protocol-browser-A"},
    ) as client:
        resources = {}
        for phase in ("source", "cold"):
            response = client.post(
                f"/api/projects/{project}/resources",
                json={
                    "name": phase + "-policy.txt",
                    "format": "txt",
                    "content": (materials / ("a-" + phase) / "policy.txt").read_text(),
                },
            )
            assert response.status_code == 201, "Synthetic material import failed"
            resources[phase] = response.json()["id"]
        imported = client.post(
            f"/api/projects/{other_project}/resources",
            json={
                "name": "other-policy.txt",
                "format": "txt",
                "content": (materials / "a-source/policy.txt").read_text(),
            },
        ).json()["id"]
        public = next(
            c
            for c in client.get(f"/api/projects/{other_project}/protocol/contracts").json()["items"]
            if c["contract_id"] == "protocol.synthetic.a-source.v1"
        )
        response = client.post(
            f"/api/projects/{other_project}/protocol/source",
            json={
                "contract_id": public["contract_id"],
                "goal": public["public_goal"],
                "inputs": public["public_inputs"],
                "resource_ids": [imported],
                "request_key": "other-project-negative",
            },
        )
        assert response.status_code == 202
        made = response.json()
        paused = client.post(
            f"/api/projects/{other_project}/protocol/runs/{made['run_id']}/recover",
            json={
                "expected_version": made["version"],
                "expected_fence": made["fence"],
                "request_key": "other-project-unsent-pause",
            },
        )
        assert paused.status_code == 200
    info = {
        "port": port,
        "project": project,
        "other_project": other_project,
        "other_run": made["run_id"],
        "user": user,
        "other_user": other_user,
        **resources,
        "bearer": "synthetic-protocol-browser-A",
        "other_bearer": "synthetic-protocol-browser-B",
        "source_contract": "protocol.synthetic.a-source.v1",
        "cold_contract": "protocol.synthetic.a-cold.v1",
    }
    info["initial_counts"] = counts(store)
    assert info["initial_counts"]["attempts"] == 0 and info["initial_counts"]["jobs"] == 1
    (root / "info.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    (root / "trusted-mock-clock.json").write_text(
        json.dumps({"kind": "protocol-browser-private-mock-clock.v1", "value": 1000}),
        encoding="utf-8",
    )
    store.engine.dispose()


class TrustedMockClock:
    """Private synthetic time persists across controller processes; never real provider time."""

    def __init__(self, root):
        self.path = root / "trusted-mock-clock.json"
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        assert saved["kind"] == "protocol-browser-private-mock-clock.v1"
        assert type(saved["value"]) in {int, float} and saved["value"] >= 1000
        self.value = float(saved["value"])

    def __call__(self):
        return self.value

    def tick(self):
        self.value += 7
        pending = self.path.with_suffix(".tmp")
        pending.write_text(
            json.dumps({"kind": "protocol-browser-private-mock-clock.v1", "value": self.value}),
            encoding="utf-8",
        )
        pending.replace(self.path)
        return self.value


def experiment(root, store, info):
    path = root / "experiment.json"
    if not path.exists():
        return None
    saved = json.loads(path.read_text(encoding="utf-8"))
    return inspect_experiment(store, info["user"], saved["experiment_id"])


def factory(root, info, settings, replies, seen, stage, clock):
    def build(worker, run, snapshot):
        scope = snapshot["scope"]
        ledger = root / (run["id"] + ".json")
        initialize_ledger(ledger, scope)
        holder = {}

        def handler(request):
            provider = holder["provider"]
            assert isinstance(request, httpx.Request) and str(request.url) == ENDPOINT
            assert request.headers["authorization"] == "Bearer synthetic-offline-browser"
            assert callable(provider.wire_guard), (
                "Gated experiment must install actual-byte/header guard"
            )
            provider.wire_guard(
                request
            )  # Actual transport boundary, not pre-reservation reconstruction.
            wire = json.loads(request.content)
            assert wire["stream"] is False and wire["max_tokens"] == 1024
            assert "gold" not in json.dumps(wire), "Private oracle appeared in model INPUT"
            seen.append(
                {
                    "run": run["id"],
                    "phase": snapshot["phase"],
                    "body_sha256": hashlib.sha256(request.content).hexdigest(),
                    "header_names": sorted(request.headers),
                    "guarded_actual_header_body": True,
                    "clock": clock(),
                }
            )
            clock.tick()  # Synthetic settled-response time, persisted before record/next request.
            return httpx.Response(200, json=replies.pop(0))

        model = InternModel(
            replace(settings, live_enabled=True, token="synthetic-offline-browser"),
            transport=httpx.MockTransport(handler),
        )

        def authorize(_):
            with worker.store.tx() as c:
                worker.store.lock_project(c, run["principal_id"], run["project_id"])
                worker.store.guard(c, run["id"], run["fence"])
                for ref in scope["resource_ids"]:
                    worker.store.authorize(
                        c,
                        run["principal_id"],
                        run["runtime_id"],
                        run["project_id"],
                        ref,
                        "resource.read",
                    )
            return True

        provider = BudgetedProvider(model, ledger, scope, stage, authorize=authorize, clock=clock)
        holder["provider"] = provider
        runner = ProtocolAttemptRunner(worker, run, snapshot, provider)
        actual_call = runner.call

        def timed_call(messages, tools):
            clock.tick()  # Explicit +7 before each model call; all real preflight/egress gates remain.
            return actual_call(messages, tools)

        runner.call = timed_call
        return runner

    return build


def action(root, name, rid=None):
    store, settings = context(root)
    try:
        info = json.loads((root / "info.json").read_text(encoding="utf-8"))
        clock = TrustedMockClock(root)
        clock.tick()  # Every explicit controller action advances the same private mock clock.
        if name == "counts":
            return {**counts(store), "experiment": experiment(root, store, info)}
        with store.tx() as c:
            run = (
                c.execute(
                    select(runs).where(runs.c.project_id == info["project"], runs.c.id == rid)
                )
                .mappings()
                .one()
            )
            job = (
                c.execute(select(protocol_jobs).where(protocol_jobs.c.run_id == rid))
                .mappings()
                .one()
            )
        if name == "review":
            assert job["kind"] == "source", (
                "Browser fixture review is source-only; cold owner remains pending"
            )
            result = review(
                store,
                info["user"],
                rid,
                {
                    "contract_id": job["accepted_snapshot"]["payload"]["contract_id"],
                    "expected_result_fingerprint": job["result_fingerprint"],
                    "expected_fence": run["fence"],
                    "expected_version": run["version"],
                    "request_key": "explicit-independent-browser-review-" + rid,
                },
            )
            summary = experiment(root, store, info)
            if job["kind"] == "source" and result["decision"] == "PASS":
                assert summary is not None
                summary = advance(store, info["user"], summary["experiment_id"], rid, clock=clock)
            return {
                "decision": result["decision"],
                "owner_semantic_acceptance": "PENDING",
                "experiment": summary,
            }
        assert run["status"] == "QUEUED", "Only exact newly accepted synthetic Run may execute"
        if name == "default-worker":
            before = counts(store)
            experiment_before = experiment(root, store, info)
            worker = Worker(store, settings, protocol_clock=clock)
            drained = []
            for _ in range(16):
                with store.tx() as c:
                    target = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
                    queued = set(
                        c.execute(select(runs.c.id).where(runs.c.status == "QUEUED")).scalars()
                    )
                if target != "QUEUED":
                    break
                with store.tx() as c:
                    protocol_ids = set(
                        c.execute(
                            select(protocol_jobs.c.run_id).where(protocol_jobs.c.run_id.in_(queued))
                        ).scalars()
                    )
                    controlled = c.execute(
                        select(events.c.id).where(
                            events.c.run_id.in_(queued), events.c.kind.in_([BINDING, HANDOFF_EVENT])
                        )
                    ).first()
                assert protocol_ids == queued and not controlled, (
                    "Default drain is limited to unbound protocol UI intents"
                )
                clock.tick()  # One real default-worker iteration; no provider clock/call exists.
                assert worker.once(), "Queued exact target requires real default-worker progress"
                after = counts(store)
                assert after["attempts"] == before["attempts"], (
                    "Default drain must not allocate a provider Attempt"
                )
                assert after["grant_fingerprint"] == before["grant_fingerprint"]
                assert after["principal_fingerprint"] == before["principal_fingerprint"]
                assert experiment(root, store, info) == experiment_before, (
                    "Default drain cannot advance or stop the experiment"
                )
                with store.tx() as c:
                    changed = list(
                        c.execute(
                            select(runs.c.id, runs.c.status).where(
                                runs.c.id.in_(queued), runs.c.status != "QUEUED"
                            )
                        ).mappings()
                    )
                assert len(changed) == 1 and changed[0]["status"] == "WAITING_RESOURCE", (
                    "Default worker must naturally wait for its unavailable protocol provider"
                )
                drained.append(changed[0]["id"])
            with store.tx() as c:
                target = c.execute(select(runs.c.status).where(runs.c.id == rid)).scalar_one()
            assert target == "WAITING_RESOURCE", (
                "Exact target did not leave QUEUED within bounded 16 default iterations"
            )
            return {
                "requests": 0,
                "run": rid,
                "status": target,
                "drained": len(drained),
                "drained_runs": drained,
                "experiment": experiment_before,
            }
        assert name == "worker"
        with store.tx() as c:
            queued = list(c.execute(select(runs.c.id).where(runs.c.status == "QUEUED")).scalars())
        assert queued == [rid], "Exact gated fixture Run must be the only queued work"
        prepare_handoff(
            store,
            info["user"],
            rid,
            {
                "expected_version": run["version"],
                "expected_fence": run["fence"],
                "request_key": "browser-gated-handoff-" + rid,
            },
        )
        summary = experiment(root, store, info)
        if summary is None:
            assert job["kind"] == "source", "First experiment stage must be source"
            genesis = initialize_experiment(
                store,
                info["user"],
                info["project"],
                "browser-offline-experiment",
                request_limit=14,
                clock=clock,
            )
            (root / "experiment.json").write_text(
                json.dumps({"experiment_id": genesis["experiment_id"]}), encoding="utf-8"
            )
            summary = inspect_experiment(store, info["user"], genesis["experiment_id"])
        bind_run(store, info["user"], summary["experiment_id"], rid, clock=clock)
        source, _ = evaluation_contract(info["source_contract"])
        cold, _ = evaluation_contract(info["cold_contract"])
        replies = {
            "source": [envelope(resource=info["source"]), envelope(source["expected_output"])],
            "extract": [
                envelope(
                    canonical_candidate_for(
                        contract_snapshot(info["source_contract"]), [info["source"]]
                    )
                )
            ],
            "cold": [envelope(cold["expected_output"])],
        }[job["kind"]]
        seen = []
        worker = Worker(
            store,
            settings,
            protocol_runner_factory=factory(
                root, info, settings, replies, seen, job["kind"] + "_a", clock
            ),
            protocol_clock=clock,
        )
        assert worker.once()
        with store.tx() as c:
            actual = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        expected_status = "SUCCEEDED" if job["kind"] == "extract" else "WAITING_APPROVAL"
        assert actual["status"] == expected_status, "Exact gated stage did not technically complete"
        assert len(seen) == {"source": 2, "extract": 1, "cold": 1}[job["kind"]]
        if job["kind"] == "extract":
            advance(store, info["user"], summary["experiment_id"], rid, clock=clock)
        # Cold remains pending; no review/advance/legacy fallback is authorized here.
        observations = root / "guarded-wire-observations.json"
        previous = (
            json.loads(observations.read_text(encoding="utf-8")) if observations.exists() else []
        )
        observations.write_text(json.dumps([*previous, *seen]), encoding="utf-8")
        return {
            "requests": len(seen),
            "run": rid,
            "phase": job["kind"],
            "transport": "httpx.MockTransport",
            "network_requests": 0,
            "experiment": experiment(root, store, info),
            "guarded_actual_header_body": all(v["guarded_actual_header_body"] for v in seen),
        }
    finally:
        store.engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--action",
        choices=["seed", "serve", "worker", "default-worker", "review", "counts"],
        required=True,
    )
    args = parser.parse_args()
    if args.action == "seed":
        assert args.port and 0 < args.port < 65536
        seed(args.root, args.port)
    elif args.action == "serve":
        store, settings = context(args.root)
        info = json.loads((args.root / "info.json").read_text(encoding="utf-8"))
        try:
            uvicorn.run(
                create_app(store, settings), host="127.0.0.1", port=info["port"], access_log=False
            )
        finally:
            store.engine.dispose()
    else:
        print(json.dumps(action(args.root, args.action, args.run_id), ensure_ascii=False))


if __name__ == "__main__":
    main()

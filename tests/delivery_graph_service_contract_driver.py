"""Thin real SQLite/HTTP adapter; never manufactures missing trusted receipts.

Fixture setup may use repository fixed-MOCK source producers. Public requests go
only through TestClient. Private mutation controls are attack fixtures, not API
inputs or production lock management. Unsupported lock controls remain explicit.
"""

import copy
import hashlib
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from sim2act.api import create_app
from sim2act.config import Settings
from sim2act.contracts import Limits
from sim2act.db import Store, app_drafts, fingerprint, grants, meta, resources
from sim2act.db import delivery_graph_requests as requests
from sim2act.db import delivery_graph_states as states
from sim2act.delivery_graph_apps import LockInput, set_lock


class ServiceDriver:
    def __init__(self, scenario="normal", shared=None):
        self.calls = []
        self.unsupported = []
        if shared is not None:
            self.root, self.settings, self.info, self.controls = shared
            self.info = copy.deepcopy(self.info)
            self._temporary = None
            self.store = Store(self.settings.database_url, test_only=True)
            self._client()
            return
        self._temporary = tempfile.TemporaryDirectory(prefix="delivery-service-contract-")
        self.root = Path(self._temporary.name)
        self.settings = Settings(
            "sqlite:///" + str(self.root / "fixture.db"), self.root, mode="mock"
        )
        self.store = Store(self.settings.database_url, test_only=True)
        try:
            self.store.initialize()
            user = self.store.user("synthetic graph owner A", "synthetic-test-A")
            other = self.store.user("synthetic graph owner B", "synthetic-test-B")
            self._client()
            pid = self._post("/api/projects", {"name": "synthetic graph contract"})["id"]
            foreign = self.store.project(other, "synthetic foreign graph contract")
            rid = self._post(
                f"/api/projects/{pid}/resources",
                {"name": "graph.csv", "format": "csv", "content": "amount,quantity\n1,2\n3,4\n"},
            )["id"]
            env = (self.store, self.settings, self.client, user, other, pid, rid)
            self.controls = {"pid": pid, "user": user, "resource": rid}
            if scenario.startswith("project"):
                from test_bounded_agent_apps import setup

                _, _, _, primary, _, _, _, _ = setup(env)
                with self.store.tx() as c:
                    related = c.execute(
                        select(app_drafts.c.id).where(
                            app_drafts.c.project_id == pid, app_drafts.c.id != primary
                        )
                    ).scalar_one()
                peer_resource = rid
                self.controls["fixture_family"] = "initial-declarative-bounded-agent-plus-CSV"
            else:
                if scenario == "report_partial":
                    from test_conditional_run_bindings import env as bounded_env
                    from test_report_manifest_apps import promoted

                    promoted_app, _, _, _, wires = promoted(bounded_env.__wrapped__(env), self.root)
                    primary = promoted_app["id"]
                    self.controls["fixed_mock_source_calls"] = len(wires)
                    self.controls["fixture_family"] = "fixed-MOCK-promoted-Report-partial"
                else:
                    primary = self._csv(pid, rid, "primary graph")
                    self.controls["fixture_family"] = "CSV"
                peer_resource = self._post(
                    f"/api/projects/{pid}/resources",
                    {
                        "name": "peer.csv",
                        "format": "csv",
                        "content": "amount,quantity\n10,20\n30,40\n",
                    },
                )["id"]
                related = self._csv(pid, peer_resource, "related graph")
            if scenario.startswith("project"):
                # Provision authority through the ordinary API before baseline.
                # Quarantine only membership, not any accepted graph/context seal.
                spare = self._csv(pid, peer_resource, "preauthorized membership fixture")
                self._derive(pid, spare)
                with self.store.tx() as c:
                    c.execute(
                        update(app_drafts)
                        .where(app_drafts.c.id == spare)
                        .values(project_id=foreign)
                    )
                self.controls["parked_related"] = spare
            first = self._derive(pid, primary)
            self._derive(pid, related)
            self.controls.update(primary=primary, related=related)
            if scenario == "target_locked":
                first = self._lock(primary)
            elif scenario == "project_locked":
                self._lock(related)
            source = next(n for n in first["graph"]["nodes"] if n["kind"] == "SOURCE")
            alternate = next(n for n in first["graph"]["nodes"] if n["id"] != source["id"])

            def change(n):
                return {
                    k: n[v]
                    for k, v in [
                        ("node_id", "id"),
                        ("expected_revision", "revision"),
                        ("expected_content_fingerprint", "content_fingerprint"),
                    ]
                }

            self.info = {
                "project_id": pid,
                "app_id": primary,
                "related_app_id": related,
                "foreign_project_id": foreign,
                "request": {
                    "project_id": pid,
                    "app_id": primary,
                    "expected_graph_fingerprint": first["graph_fingerprint"],
                    "request_key": "service-contract-plan",
                    "changes": [change(source)],
                },
                "alternate_changes": [change(alternate)],
            }
            self.controls.update(
                primary=primary,
                related=related,
                related_resource=peer_resource,
                primary_resource=first["graph"]["resource_ids"][0],
            )
            self.authority_baseline = self._authority()
        except BaseException:
            self.close()
            raise

    def _client(self):
        self.client = TestClient(create_app(self.store, self.settings))
        self.client.headers["Authorization"] = "Bearer synthetic-test-A"

    def _post(self, path, body):
        response = self.client.post(path, json=body)
        if response.status_code not in {200, 201, 202}:
            raise AssertionError("Real fixture HTTP setup rejected: " + str(response.status_code))
        return response.json()

    def _csv(self, pid, rid, name):
        return self._post(
            f"/api/projects/{pid}/apps/csv-preview",
            {"name": name, "resource_id": rid, "goal": "synthetic exact sum"},
        )["id"]

    def _derive(self, pid, aid):
        draft = self.client.get("/api/apps/" + aid)
        assert draft.status_code == 200
        return self._post(
            f"/api/projects/{pid}/apps/{aid}/delivery-graph/derive",
            {
                "expected_candidate_fingerprint": draft.json()["fingerprint"],
                "request_key": "fixture-real-derive-" + aid,
            },
        )

    def _lock(self, aid):
        pid = self.controls["pid"]
        current = self.client.get(f"/api/projects/{pid}/apps/{aid}/delivery-graph")
        assert current.status_code == 200
        graph = current.json()
        node = next(n for n in graph["graph"]["nodes"] if n["kind"] == "SOURCE")
        body = LockInput(
            expected_graph_fingerprint=graph["graph_fingerprint"],
            request_key="fixture-lock-" + aid,
            change={
                "node_id": node["id"],
                "expected_revision": node["revision"],
                "expected_content_fingerprint": node["content_fingerprint"],
            },
            locked=True,
        )
        limits = Limits(**{k: getattr(self.settings, k) for k in Limits.model_fields})
        set_lock(self.store, self.controls["user"], pid, aid, body, limits)
        draft = self.client.get("/api/apps/" + aid)
        assert draft.status_code == 200
        return self._post(
            f"/api/projects/{pid}/apps/{aid}/delivery-graph/derive",
            {
                "expected_candidate_fingerprint": draft.json()["fingerprint"],
                "request_key": "fixture-after-lock-" + aid,
            },
        )

    def _authority(self):
        with self.store.tx() as c:
            return fingerprint(
                [dict(r) for r in c.execute(select(grants).order_by(grants.c.id)).mappings()]
            )

    def observe(self):
        with self.store.tx() as c:
            snapshots = {
                t.name: sorted([dict(r) for r in c.execute(select(t)).mappings()], key=fingerprint)
                for t in meta.sorted_tables
            }
            count = c.execute(
                select(func.count()).select_from(requests).where(requests.c.kind == "plan")
            ).scalar_one()
        ledger_names = {"delivery_graph_requests", "delivery_graph_scope_jobs"}
        return {
            "domain_fingerprint": fingerprint(
                {k: v for k, v in snapshots.items() if k not in ledger_names}
            ),
            "ledger_fingerprint": fingerprint(
                {k: v for k, v in snapshots.items() if k in ledger_names}
            ),
            "receipt_count": count,
            "complete_database_fingerprint": fingerprint(snapshots),
            "authority_fingerprint": self._authority(),
        }

    def plan(self, body):
        public = copy.deepcopy(body)
        pid, aid = public.pop("project_id"), public.pop("app_id")
        response = self.client.post(
            f"/api/projects/{pid}/apps/{aid}/delivery-graph/plans", json=public
        )
        value = response.json()
        self.calls.append(
            {
                "http_status": response.status_code,
                "returned_fields": sorted(value) if isinstance(value, dict) else [],
            }
        )
        if response.status_code in {200, 201}:
            native = {k: v for k, v in value.items() if k != "cached"}
            assert native["native_outer_fingerprint"] == fingerprint(
                {k: v for k, v in native.items() if k != "native_outer_fingerprint"}
            ), "Native server receipt seal mismatch"
            data = {
                "core": native["receipt"],
                "expansion": native["expansion"],
                "outer_fingerprint": native["outer_fingerprint"],
            }
            assert data["outer_fingerprint"] == fingerprint(
                {k: v for k, v in data.items() if k != "outer_fingerprint"}
            ), "Server public receipt seal mismatch"
            assert native["scope_expansion"]["status"] != "BLOCKED_PARTIAL", (
                "Real service expansion is BLOCKED_PARTIAL; cannot claim complete contract"
            )
            return {"status": 200, "data": data}
        error = value.get("error", {}) if isinstance(value, dict) else {}
        code = error.get("code") if isinstance(error, dict) else error
        if response.status_code == 422:
            return {"status": 400, "error": code or "INVALID_MANIFEST"}
        return {
            "status": response.status_code,
            "error": "PERMISSION_DENIED" if code == "GRANT_REVOKED" else code,
        }

    def cold(self):
        return ServiceDriver(shared=(self.root, self.settings, self.info, self.controls))

    def transition(self, event):
        aid = self.controls["related"] if event.endswith("related") else self.controls["primary"]
        if event == "add_related":
            added = self.controls["parked_related"]
            with self.store.tx() as c:
                c.execute(
                    update(app_drafts)
                    .where(app_drafts.c.id == added)
                    .values(project_id=self.controls["pid"])
                )
            self._derive(self.controls["pid"], added)
            assert self._authority() == self.authority_baseline
            return
        if event == "lock_related":
            self._lock(aid)
            return
        with self.store.tx() as c:
            if event.startswith("revoke_"):
                draft = c.execute(select(app_drafts).where(app_drafts.c.id == aid)).mappings().one()
                c.execute(
                    update(grants)
                    .where(
                        grants.c.project_id == self.controls["pid"],
                        grants.c.principal_id == draft["runtime_id"],
                        grants.c.resource_id
                        == self.controls[
                            "related_resource" if event.endswith("related") else "primary_resource"
                        ],
                    )
                    .values(revoked=True)
                )
            elif event.startswith("bump_"):
                rid = self.controls[
                    "related_resource" if event.endswith("related") else "primary_resource"
                ]
                row = c.execute(select(resources).where(resources.c.id == rid)).mappings().one()
                value = row["content"] + "\n"
                c.execute(
                    update(resources)
                    .where(resources.c.id == rid)
                    .values(content=value, hash=hashlib.sha256(value.encode()).hexdigest())
                )
            elif event == "tamper_graph_revision":
                row = c.execute(select(states).where(states.c.app_id == aid)).mappings().one()
                value = copy.deepcopy(row["snapshot"])
                value["graph_revision"] = True
                c.execute(
                    update(states)
                    .where(states.c.app_id == aid)
                    .values(snapshot=value, fingerprint=fingerprint(value))
                )
            elif event.startswith("tamper_"):
                row = (
                    c.execute(
                        select(requests).where(requests.c.app_id == aid, requests.c.kind == "plan")
                    )
                    .mappings()
                    .one()
                )
                value = copy.deepcopy(row["snapshot"])
                if event == "tamper_core_receipt_types":
                    value["response"]["receipt"]["patch_executed"] = 0
                elif event == "tamper_outer_receipt_types":
                    value["response"]["expansion"]["applications"][0]["authorization_revision"] = (
                        True
                    )
                elif event == "tamper_outer_receipt":
                    value["response"]["scope_expansion"]["status"] = "TAMPERED"
                else:
                    raise ValueError("Unknown fixture mutation")
                c.execute(
                    update(requests)
                    .where(requests.c.app_id == aid, requests.c.kind == "plan")
                    .values(snapshot=value, fingerprint=fingerprint(value))
                )
            else:
                raise ValueError("Unknown fixture transition")

    def close(self):
        if hasattr(self, "client"):
            self.client.close()
        if hasattr(self, "store"):
            self.store.engine.dispose()
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None


def factory(scenario):
    return ServiceDriver(scenario)

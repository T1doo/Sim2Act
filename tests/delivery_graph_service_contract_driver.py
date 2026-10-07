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
from sim2act.db import Store, app_drafts, fingerprint, grants, meta, resources
from sim2act.db import delivery_graph_requests as requests
from sim2act.db import delivery_graph_states as states


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
                from test_conditional_run_bindings import env as bounded_env
                from test_report_manifest_apps import promoted

                promoted_app, _, _, _, wires = promoted(bounded_env.__wrapped__(env), self.root)
                primary = promoted_app["id"]
                self.controls["fixed_mock_source_calls"] = len(wires)
            else:
                primary = self._csv(pid, rid, "primary graph")
            peer_resource = self._post(
                f"/api/projects/{pid}/resources",
                {"name": "peer.csv", "format": "csv", "content": "amount,quantity\n10,20\n30,40\n"},
            )["id"]
            related = self._csv(pid, peer_resource, "related graph")
            first = self._derive(pid, primary)
            self._derive(pid, related)
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
            if scenario in {"target_locked", "project_locked"}:
                self.unsupported.append(
                    "No current service lock-control/consumption interface; initial lock not fabricated"
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
            # Status normalization only. Do not construct expansion or outer seals
            # from mutable observations: the server must persist/return them.
            return {"status": 200, "data": value}
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
            added = self._csv(self.controls["pid"], self.controls["related_resource"], "added peer")
            self._derive(self.controls["pid"], added)
            assert self._authority() == self.authority_baseline
            return
        if event == "lock_related":
            raise NotImplementedError("Service has no trusted lock transition interface")
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
                    value["response"]["authorization_revision"] = True
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

"""Contract-runner self-tests, using a synthetic memory-only service double.

This double is not a product adapter or persistent DB implementation. Its outer
scope envelope illustrates the contract missing from the single-app pure core.
Unsafe doubles demonstrate that the black-box runner detects adapter shortcuts.
"""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from delivery_graph_adapter_contract import check_selection_response, run_contract
from test_delivery_graph import digest, fixture, inputs, request, uid

from sim2act.delivery_graph import derive_manifest_graph, plan_change
from sim2act.errors import DomainError


class MemoryDriver:
    def __init__(self, scenario, snapshot=None):
        if snapshot is not None:
            self.state, self.info = copy.deepcopy(snapshot)
            return
        self.state = {"apps": {}, "ledger": {}}
        for label in ("primary", "related", "foreign"):
            candidate, limits = fixture("multi")
            versions, ids, context = inputs(candidate)
            if label == "foreign":
                context["project_id"] = uid("proj", 999)
            if label == "primary" and scenario.startswith("project"):
                context["unknown_dependencies"] = [
                    {
                        "node_id": ids["action:right"],
                        "scope": "PROJECT",
                        "reason": "Collection access not bounded",
                    }
                ]
            if (label == "primary" and scenario == "target_locked") or (
                label == "related" and scenario == "project_locked"
            ):
                context["locked_nodes"] = [ids["action:left"]]
            self.state["apps"][label] = {
                "candidate": candidate,
                "limits": limits.model_dump(),
                "versions": versions,
                "ids": ids,
                "context": context,
            }
            self._derive(label)
        first = self.state["apps"]["primary"]
        graph = first["graph"]
        body = request(graph, "action:left")
        body["expected_graph_fingerprint"] = graph["graph_fingerprint"]
        self.info = {
            "project_id": graph["project_id"],
            "app_id": graph["app_id"],
            "related_app_id": self.state["apps"]["related"]["graph"]["app_id"],
            "foreign_project_id": self.state["apps"]["foreign"]["graph"]["project_id"],
            "request": body,
            "alternate_changes": request(graph, "action:right")["changes"],
        }

    def _derive(self, label):
        app = self.state["apps"][label]
        app["context"]["graph_fingerprint"] = None
        graph = derive_manifest_graph(
            app["candidate"]["manifest"],
            app["candidate"]["actions"],
            app["versions"],
            app["ids"],
            app["context"],
            app["limits"],
        )
        app["graph"] = graph
        app["context"]["graph_fingerprint"] = graph["graph_fingerprint"]

    def observe(self):
        return {
            "domain_fingerprint": digest(self.state["apps"]),
            "receipt_count": len(self.state["ledger"]),
            "ledger_fingerprint": digest(self.state["ledger"]),
        }

    def cold(self):
        # JSON rehydration discards object identity; not an OS process or real DB restart.
        snapshot = json.loads(json.dumps((self.state, self.info)))
        return type(self)("normal", snapshot=snapshot)

    def close(self):
        pass

    def transition(self, event):
        label = "primary" if event.endswith("primary") else "related"
        app = self.state["apps"][label]
        if event.startswith("revoke"):
            app["context"]["authorized"] = False
            app["context"]["authorization_revision"] += 1
        elif event.startswith("bump"):
            key = "source:" + uid("res", 1)
            app["versions"][key]["revision"] += 1
            app["versions"][key]["content_fingerprint"] = digest(event)
            app["context"]["source_versions"] = copy.deepcopy(app["versions"])
            app["context"]["node_revisions"][key] += 1
            self._derive(label)
        elif event == "lock_related":
            app["context"]["locked_nodes"] = [app["ids"]["action:left"]]
            self._derive(label)
        elif event == "add_related":
            added = copy.deepcopy(app)
            added["candidate"]["manifest"]["app_id"] = uid("app", 9999)
            versions, ids, context = inputs(added["candidate"])
            added.update(versions=versions, ids=ids, context=context)
            self.state["apps"]["new_related"] = added
            self._derive("new_related")
        elif event == "tamper_graph_revision":
            self.state["apps"]["primary"]["graph"]["nodes"][0]["revision"] = True
        elif event in {"tamper_core_receipt_types", "tamper_outer_receipt_types"}:
            row = next(iter(self.state["ledger"].values()))
            if event == "tamper_core_receipt_types":
                row["core"]["patch_executed"] = 0
                row["core"]["plan_fingerprint"] = digest(
                    {k: v for k, v in row["core"].items() if k != "plan_fingerprint"}
                )
            else:
                row["expansion"]["applications"][0]["authorization_revision"] = True
                row["expansion"]["snapshot_fingerprint"] = digest(row["expansion"]["applications"])
            row["outer_fingerprint"] = digest(
                {k: v for k, v in row.items() if k != "outer_fingerprint"}
            )
        elif event == "tamper_outer_receipt":
            row = next(iter(self.state["ledger"].values()))
            row["expansion"]["applications"] = row["expansion"]["applications"][:1]
            row["expansion"]["snapshot_fingerprint"] = digest(row["expansion"]["applications"])
            row["outer_fingerprint"] = digest(
                {k: v for k, v in row.items() if k != "outer_fingerprint"}
            )
        else:
            raise AssertionError("Unknown fixture transition")

    def _expansion(self, core):
        if core["revalidation_scope"] == "PROJECT":
            apps = [
                app
                for app in self.state["apps"].values()
                if app["context"]["project_id"] == core["project_id"]
            ]
        else:
            apps = [self.state["apps"]["primary"]]
        records = []
        for app in apps:
            context = app["context"]
            if not context["authorized"]:
                raise DomainError("PERMISSION_DENIED")
            if core["revalidation_scope"] in {"APP", "PROJECT"} and context["locked_nodes"]:
                raise DomainError("LOCK_CONFLICT")
            records.append(
                {
                    "project_id": context["project_id"],
                    "app_id": context["app_id"],
                    "graph_fingerprint": context["graph_fingerprint"],
                    "authorization_revision": context["authorization_revision"],
                    "locked_nodes": sorted(context["locked_nodes"]),
                }
            )
        records.sort(key=lambda r: r["app_id"])
        return {
            "scope": core["revalidation_scope"],
            "applications": records,
            "snapshot_fingerprint": digest(records),
        }

    def plan(self, body):
        try:
            if set(body) != {
                "project_id",
                "app_id",
                "request_key",
                "changes",
                "expected_graph_fingerprint",
            }:
                raise DomainError("INVALID_MANIFEST")
            app = self.state["apps"]["primary"]
            key = body["project_id"] + ":" + body["app_id"] + ":" + body["request_key"]
            previous = self.state["ledger"].get(key)
            change = {k: v for k, v in body.items() if k != "expected_graph_fingerprint"}
            core = plan_change(
                app["graph"],
                body["expected_graph_fingerprint"],
                change,
                app["context"],
                previous["core"] if previous is not None else None,
            )
            expanded = self._expansion(core)
            row = {"core": core, "expansion": expanded}
            row["outer_fingerprint"] = digest(row)
            if previous is not None and digest(previous) != digest(row):
                raise DomainError("VERSION_CONFLICT")
            # Persist only after every scope gate succeeds, and return a deep copy.
            self.state["ledger"][key] = copy.deepcopy(row)
            return {"status": 200, "data": copy.deepcopy(row)}
        except DomainError as exc:
            return {
                "status": 403
                if exc.code == "PERMISSION_DENIED"
                else 400
                if exc.code == "INVALID_MANIFEST"
                else 409,
                "error": exc.code,
            }


class CachedFirst(MemoryDriver):
    def plan(self, body):
        previous = next(iter(self.state["ledger"].values()), None)
        if previous is not None:
            return {"status": 200, "data": copy.deepcopy(previous)}
        return super().plan(body)


class TargetOnly(MemoryDriver):
    def _expansion(self, core):
        narrow = copy.deepcopy(core)
        narrow["revalidation_scope"] = "NODES"
        result = super()._expansion(narrow)
        result["scope"] = core["revalidation_scope"]
        return result


class PartialSave(MemoryDriver):
    def _expansion(self, core):
        if any(app["context"]["locked_nodes"] for app in self.state["apps"].values()):
            self.state["ledger"]["unsafe-partial"] = {"core": copy.deepcopy(core)}
        return super()._expansion(core)


class TrustClientContext(MemoryDriver):
    def plan(self, body):
        if "current_context" in body:
            self.state["apps"]["primary"]["context"]["authorized"] = True
            self.state["apps"]["primary"]["context"]["authorization_revision"] -= 1
            body = {
                k: v for k, v in body.items() if k not in {"current_context", "previous_receipt"}
            }
        return super().plan(body)


class TrustOuterReceipt(MemoryDriver):
    def plan(self, body):
        reply = super().plan(body)
        if reply.get("error") == "VERSION_CONFLICT":
            previous = next(iter(self.state["ledger"].values()), None)
            if previous is not None:
                return {"status": 200, "data": copy.deepcopy(previous)}
        return reply


class DeniedLedgerOverwrite(MemoryDriver):
    def plan(self, body):
        reply = super().plan(body)
        if reply["status"] != 200 and self.state["ledger"]:
            next(iter(self.state["ledger"].values()))["outer_fingerprint"] = "0" * 64
        return reply


class PythonEqualOuterReplay(MemoryDriver):
    def plan(self, body):
        previous = next(iter(self.state["ledger"].values()), None)
        if previous is not None:
            app = previous["expansion"]["applications"][0]
            if type(app["authorization_revision"]) is bool:
                app["authorization_revision"] = 1
                previous["expansion"]["snapshot_fingerprint"] = digest(
                    previous["expansion"]["applications"]
                )
                previous["outer_fingerprint"] = digest(
                    {k: v for k, v in previous.items() if k != "outer_fingerprint"}
                )
        return super().plan(body)


class MissingOuterFingerprint(MemoryDriver):
    def plan(self, body):
        reply = super().plan(body)
        if reply["status"] == 200:
            del reply["data"]["outer_fingerprint"]
        return reply


class BoolAuthorizationRevision(MemoryDriver):
    def _expansion(self, core):
        expansion = super()._expansion(core)
        expansion["applications"][0]["authorization_revision"] = True
        expansion["snapshot_fingerprint"] = digest(expansion["applications"])
        return expansion


def test_reference_double_passes_adapter_contract_only():
    report = run_contract(MemoryDriver)
    assert report["status"] == "PASS", report
    assert len(report["results"]) == 17


@pytest.mark.parametrize(
    "factory,case",
    [
        (CachedFirst, "primary_revoke_before_replay"),
        (TargetOnly, "project_expansion_targets"),
        (PartialSave, "related_initial_lock_no_partial_receipt"),
        (TrustClientContext, "client_authority_injection_after_revoke"),
        (TrustOuterReceipt, "outer_receipt_tamper"),
        (DeniedLedgerOverwrite, "primary_version_before_replay"),
        (MissingOuterFingerprint, "cold_scoped_replay"),
        (BoolAuthorizationRevision, "cold_scoped_replay"),
        (PythonEqualOuterReplay, "stored_outer_receipt_type_tamper"),
    ],
)
def test_runner_rejects_unsafe_service_shortcuts(factory, case):
    report = run_contract(factory, [case])
    assert report["status"] == "FAIL"
    assert report["results"][0]["case"] == case


def test_selected_project_oracle_rejects_late_old_response_without_resubmission():
    driver = MemoryDriver("normal")
    body = driver.info["request"]
    reply = driver.plan(body)
    before = driver.observe()
    assert check_selection_response(body, reply, driver.info["project_id"], driver.info["app_id"])
    assert not check_selection_response(
        body, reply, driver.info["foreign_project_id"], driver.info["app_id"]
    )
    assert not check_selection_response(
        body, reply, driver.info["project_id"], driver.info["related_app_id"]
    )
    assert driver.observe() == before


@pytest.mark.parametrize(
    "reply", [{"status": 200}, {"status": 200, "data": None}, {"status": 200, "data": {"core": []}}]
)
def test_selection_oracle_rejects_missing_identity(reply):
    assert not check_selection_response({}, reply, None, None)


def test_cli_import_failure_does_not_print_exception_secret(tmp_path):
    (tmp_path / "broken_fixture.py").write_text("raise ValueError('SYNTHETIC_REVIEW_SECRET')")
    runner = Path(__file__).with_name("delivery_graph_adapter_contract.py")
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    result = subprocess.run(
        [sys.executable, str(runner), "--driver", "broken_fixture:factory"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 1
    assert result.stderr == ""
    assert "SYNTHETIC_REVIEW_SECRET" not in result.stdout
    assert json.loads(result.stdout)["error_type"] == "ValueError"

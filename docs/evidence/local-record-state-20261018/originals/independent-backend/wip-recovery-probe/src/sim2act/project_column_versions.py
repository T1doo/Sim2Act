"""Atomically materialize an accepted finite overlay into executable internal versions."""

import copy
import time
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import column_patches as columns
from . import csv_dag as dag
from . import csv_dag_instances as adapter
from . import lifecycle
from . import project_column_patches as patches
from .contracts import Limits
from .db import fingerprint, internal_approvals
from .errors import DomainError
from .project_revalidation import SafeInput

NAMESPACE = "finite-project-column-versions.v1"
KIND = "project_column_versions"
COMMIT = KIND + "_commit"
CANCEL = KIND + "_cancel"


class Preview(SafeInput):
    expected_receipt_fingerprint: str = Field(pattern=dag.graph.HASH)
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class Confirmation(SafeInput):
    expected_preview_fingerprint: str = Field(pattern=dag.graph.HASH)
    consent: Literal["CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


class Cancellation(SafeInput):
    expected_preview_fingerprint: str = Field(pattern=dag.graph.HASH)
    consent: Literal["CANCEL_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")


def checked(store, c, user, pid, aid, key, limits):
    value = patches.outcome(store, c, user, pid, aid, key, limits)
    _, saved = columns.read_pair(c, user, aid, patches.FINISH, key, patches.Confirmation)
    adapter.require(value["checks_status"] == "PASS" and fingerprint(saved) == fingerprint(patches.finished(value)),
                    "Read the exact saved, independently checked project overlay")
    return saved


def origin_for(saved, peer, user):
    return dict(namespace=NAMESPACE, project_id=saved["project_id"], principal_id=user,
                app_id=saved["app_id"], patch_key=saved["patch_key"],
                receipt_fingerprint=saved["receipt_fingerprint"], source_app_id=peer)


def snapshot_from_origin(store, c, user, origin, limits):
    adapter.require(isinstance(origin, dict) and origin.get("namespace") == NAMESPACE
                    and origin.get("principal_id") == user, "Missing exact project overlay origin")
    # Scope/authority before protected receipts, also on cold instance execution.
    dag.graph.current(store, c, user, origin["project_id"], origin["source_app_id"], limits)
    _, saved = columns.read_pair(c, user, origin["app_id"], patches.FINISH, origin["patch_key"], patches.Confirmation)
    adapter.require(fingerprint(origin) == fingerprint(origin_for(saved, origin["source_app_id"], user))
                    and saved["state"] == "CHECKED_PROJECT_CANDIDATE" and saved["checks_status"] == "PASS"
                    and saved["finite_revalidation_completed"] is True and saved["publishable"] is False
                    and saved["canonical_patch_executed"] is False)
    peers = [p for p in saved["affected"] if p["app_id"] == origin["source_app_id"]]
    jobs = [j for j in saved["jobs"] if j["app_id"] == origin["source_app_id"] and j["phase"] == "patched"]
    adapter.require(len(peers) == len(jobs) == 1)
    peer, job = peers[0], jobs[0]
    overlay = columns.build(store, c, user, origin["project_id"], origin["source_app_id"],
                            columns.DefinitionInput(**peer["request"]), limits)
    adapter.require(fingerprint(overlay) == fingerprint(peer["patch"]))
    snap = adapter.source_snapshot(store, c, user, job["run_id"], limits, fixed=True)
    proof = dag.inspect_job_tx(store, c, user, job["run_id"], limits)
    adapter.require(fingerprint(proof) == fingerprint(job["proof"]) and job["cancel_intent"] is False
                    and proof["result"]["output"]["column"] == overlay["definition"]["column_binding"]["value"])
    snap["execution_source"]["default_column"] = overlay["definition"]["column_binding"]["value"]
    snap["project_column_origin"] = copy.deepcopy(origin)
    snap["column_overlay"] = copy.deepcopy(overlay["definition"])
    snap["column_overlay_graph"] = copy.deepcopy(overlay["graph"])
    snap["publishable"] = False
    return snap


def source_evidence(store, c, user, snap, limits):
    adapter.require(snap.get("execution_source", {}).get("version") == adapter.FIXED_REPORT_VERSION)
    expected = snapshot_from_origin(store, c, user, snap.get("project_column_origin"), limits)
    adapter.require(fingerprint(snap) == fingerprint(expected))
    # Reconstruct from the actual Run, including its accepted fingerprint;
    # an approval or preview hash alone cannot prove that provenance.
    return dict(origin=expected["project_column_origin"], execution_source=expected["execution_source"])


def group_marker(pid, aid, key, receipt_fp):
    return dict(namespace=NAMESPACE, project_id=pid, app_id=aid, request_key=key, receipt_fingerprint=receipt_fp)


def approval_view(c, user, pid, info, snap, marker):
    a = c.execute(select(internal_approvals).where(internal_approvals.c.id == info["id"])).mappings().first()
    adapter.require(a is not None and a["principal_id"] == user and a["project_id"] == pid
                    and a["kind"] == "release" and fingerprint(a["payload"]) == a["fingerprint"] == info["fingerprint"])
    p = a["payload"]
    wanted = dict(snapshot=snap, project_column_group=marker, grant_version=lifecycle.grant_version(c, pid, user),
                  approval_id=a["id"], principal_id=user, project_id=pid, kind="release", expires_at=a["expires_at"])
    adapter.require(fingerprint(p) == fingerprint(wanted) and type(a["expires_at"]) in (int, float))
    adapter.validate_family(c, user, a["id"], snap)
    return a


def definition(store, c, user, pid, aid, key, limits):
    saved = checked(store, c, user, pid, aid, key, limits)
    body, preview = columns.read_pair(c, user, aid, KIND, key, Preview)
    adapter.require(body.request_key == key and body.expected_receipt_fingerprint == saved["receipt_fingerprint"])
    marker = group_marker(pid, aid, key, saved["receipt_fingerprint"])
    entries = []
    for item in saved["affected"]:
        snap = snapshot_from_origin(store, c, user, origin_for(saved, item["app_id"], user), limits)
        matches = [e for e in preview["entries"] if e["app_id"] == item["app_id"]]
        adapter.require(len(matches) == 1)
        info = matches[0]["approval"]
        a = approval_view(c, user, pid, info, snap, marker)
        entries.append(dict(app_id=item["app_id"], snapshot=snap, snapshot_fingerprint=fingerprint(snap),
                            approval=dict(id=a["id"], fingerprint=a["fingerprint"], expires_at=a["expires_at"])))
    wanted = preview_value(saved, entries, limits, user)
    adapter.require(fingerprint(preview) == fingerprint(wanted), "Project version preview changed")
    return preview


def preview_value(saved, entries, limits, user):
    issued_at = min(e["approval"]["expires_at"] for e in entries) - 300
    value = dict(namespace=NAMESPACE, project_id=saved["project_id"], app_id=saved["app_id"],
                 principal_id=user, request_key=saved["patch_key"],
                 receipt_fingerprint=saved["receipt_fingerprint"], patch_fingerprint=saved["patch_fingerprint"],
                 entries=entries, affected=saved["affected"], preserved=saved["preserved"], budget=saved["budget"],
                 issued_at=issued_at, expires_at=min(issued_at + limits.run_seconds,
                                                   *(e["approval"]["expires_at"] for e in entries)),
                 state="INTERNAL_VERSIONS_PREVIEW", **patches.flags())
    return {**value, "preview_fingerprint": fingerprint(value)}


@dag.graph.controlled
def propose(store, user, pid, aid, key, body, limits):
    with store.tx(wait_seconds=min(30, limits.run_seconds)) as c:
        saved = checked(store, c, user, pid, aid, key, limits)
        adapter.require(body.request_key == key and body.expected_receipt_fingerprint == saved["receipt_fingerprint"])
        if dag.graph.lookup(c, user, aid, KIND, key):
            original, _ = columns.read_pair(c, user, aid, KIND, key, Preview)
            adapter.require(original == body)
            return {**definition(store, c, user, pid, aid, key, limits), "cached": True}
        entries = []
        marker = group_marker(pid, aid, key, saved["receipt_fingerprint"])
        for peer in saved["affected"]:
            snap = snapshot_from_origin(store, c, user, origin_for(saved, peer["app_id"], user), limits)
            a = lifecycle.new_approval(c, user, pid, "release", dict(snapshot=snap,
                project_column_group=marker, grant_version=lifecycle.grant_version(c, pid, user)))
            origin = adapter.ReleaseOrigin(version=adapter.FIXED_REPORT_VERSION, request_key=a["id"],
                approval_id=a["id"], snapshot_fingerprint=fingerprint(snap), source_run_id=snap["execution_source"]["run_id"])
            patches.save_pair(c, user, peer["app_id"], "csv_dag_release_origin", a["id"], origin, origin.model_dump())
            expiry = c.execute(select(internal_approvals.c.expires_at).where(internal_approvals.c.id == a["id"])).scalar_one()
            entries.append(dict(app_id=peer["app_id"], snapshot=snap, snapshot_fingerprint=fingerprint(snap),
                                approval=dict(id=a["id"], fingerprint=a["fingerprint"], expires_at=expiry)))
        preview = preview_value(saved, entries, limits, user)
        patches.save_pair(c, user, aid, KIND, key, body, preview)
        definition(store, c, user, pid, aid, key, limits)
        ensure_live(c, user, aid, key, preview)
        return {**preview, "cached": False}


def ensure_live(c, user, aid, key, preview):
    if dag.graph.lookup(c, user, aid, CANCEL, key):
        raise DomainError("VERSION_CONFLICT", "Exact project version group cancelled")
    if time.time() >= preview["expires_at"]:
        raise DomainError("BUDGET_EXHAUSTED", "Project version approval expired; late results cannot commit")


def receipt_value(preview, entries):
    value = dict(namespace=NAMESPACE, project_id=preview["project_id"], app_id=preview["app_id"],
                 principal_id=preview["principal_id"], request_key=preview["request_key"],
                 preview_fingerprint=preview["preview_fingerprint"], receipt_fingerprint=preview["receipt_fingerprint"],
                 entries=entries, state="EXECUTABLE_INTERNAL_VERSIONS", **patches.flags())
    return {**value, "group_fingerprint": fingerprint(value)}


def read_committed(store, c, user, pid, aid, key, preview, limits):
    body, value = columns.read_pair(c, user, aid, COMMIT, key, Confirmation)
    adapter.require(body.request_key == key and body.expected_preview_fingerprint == preview["preview_fingerprint"])
    entries = []
    for expected in preview["entries"]:
        found = [e for e in value["entries"] if e["app_id"] == expected["app_id"]]
        adapter.require(len(found) == 1)
        entry = found[0]
        rel = lifecycle.read_release(store, c, user, entry["release_id"], limits)
        adapter.require(rel["approval_id"] == expected["approval"]["id"]
                        and rel["fingerprint"] == expected["snapshot_fingerprint"] == entry["release_fingerprint"])
        instance, _ = lifecycle.instance(store, c, user, entry["instance_id"], limits)
        adapter.validate_instance_history(c, instance)
        adapter.check_instance_records(store, c, user, instance, lifecycle.data_rows(c, instance["id"]), limits)
        initial = "iinstance_" + fingerprint(dict(user=user, release=rel["id"],
            key=patches.key_for(key, expected["app_id"], "internal-instance")))[:32]
        adapter.require(instance["id"] == initial and instance["source_app_id"] == expected["app_id"]
                        and instance["history"][0]["release_id"] == rel["id"])
        entries.append(dict(app_id=expected["app_id"], release_id=rel["id"], release_fingerprint=rel["fingerprint"],
                            instance_id=initial))
    adapter.require(fingerprint(value) == fingerprint(receipt_value(preview, entries)))
    return value


@dag.graph.controlled
def commit(store, user, pid, aid, key, body, limits):
    with store.tx(wait_seconds=min(30, limits.run_seconds)) as c:
        preview = definition(store, c, user, pid, aid, key, limits)
        adapter.require(body.request_key == key and body.expected_preview_fingerprint == preview["preview_fingerprint"])
        if dag.graph.lookup(c, user, aid, COMMIT, key):
            original, _ = columns.read_pair(c, user, aid, COMMIT, key, Confirmation)
            adapter.require(original == body)
            return {**read_committed(store, c, user, pid, aid, key, preview, limits), "cached": True}
        ensure_live(c, user, aid, key, preview)
        entries = []
        marker = group_marker(pid, aid, key, preview["receipt_fingerprint"])
        for item in preview["entries"]:
            a = item["approval"]
            rel = lifecycle.commit_release_tx(store, c, user, a["id"], a["fingerprint"], limits, project_group=marker)
            i = lifecycle.create_instance_tx(store, c, user, rel["id"], rel["fingerprint"], limits,
                                             request_key=patches.key_for(key, item["app_id"], "internal-instance"))
            entries.append(dict(app_id=item["app_id"], release_id=rel["id"], release_fingerprint=rel["fingerprint"], instance_id=i["id"]))
        value = receipt_value(preview, entries)
        patches.save_pair(c, user, aid, COMMIT, key, body, value)
        definition(store, c, user, pid, aid, key, limits)
        read_committed(store, c, user, pid, aid, key, preview, limits)
        ensure_live(c, user, aid, key, preview)
        return {**value, "cached": False}


@dag.graph.controlled
def cancel(store, user, pid, aid, key, body, limits):
    with store.tx(wait_seconds=min(30, limits.run_seconds)) as c:
        preview = definition(store, c, user, pid, aid, key, limits)
        adapter.require(body.request_key == key and body.expected_preview_fingerprint == preview["preview_fingerprint"])
        adapter.require(not dag.graph.lookup(c, user, aid, COMMIT, key), "An already created group cannot be cancelled")
        value = dict(namespace=NAMESPACE, request_key=key, preview_fingerprint=preview["preview_fingerprint"], state="CANCELLED")
        if dag.graph.lookup(c, user, aid, CANCEL, key):
            original, saved = columns.read_pair(c, user, aid, CANCEL, key, Cancellation)
            adapter.require(original == body and fingerprint(saved) == fingerprint(value))
        else:
            patches.save_pair(c, user, aid, CANCEL, key, body, value)
        return value


def mount(app, store, identity, limits, settings):
    base = "/api/projects/{pid}/apps/{aid}/project-column-patches/{key}/internal-versions"
    dependency = Depends(identity)

    def effective():
        return Limits(**{k: getattr(settings, k) for k in Limits.model_fields})

    def offline():
        if settings.mode != "mock" or settings.live_enabled:
            raise DomainError("PERMISSION_DENIED", "Offline internal versions only")

    @app.post(base, status_code=201)
    def prepare(pid: str, aid: str, key: str, body: Preview, user=dependency):
        offline()
        return propose(store, user, pid, aid, key, body, effective())

    @app.get(base + "/definition")
    def read_definition(pid: str, aid: str, key: str, user=dependency):
        with store.tx(wait_seconds=min(30, effective().run_seconds)) as c:
            return definition(store, c, user, pid, aid, key, effective())

    @app.get(base)
    def read(pid: str, aid: str, key: str, user=dependency):
        with store.tx(wait_seconds=min(30, effective().run_seconds)) as c:
            preview = definition(store, c, user, pid, aid, key, effective())
            if dag.graph.lookup(c, user, aid, COMMIT, key):
                return read_committed(store, c, user, pid, aid, key, preview, effective())
            if dag.graph.lookup(c, user, aid, CANCEL, key):
                body, value = columns.read_pair(c, user, aid, CANCEL, key, Cancellation)
                adapter.require(body.request_key == key and body.expected_preview_fingerprint == preview["preview_fingerprint"]
                    and fingerprint(value) == fingerprint(dict(namespace=NAMESPACE, request_key=key,
                        preview_fingerprint=preview["preview_fingerprint"], state="CANCELLED")))
                return value
            return preview

    @app.post(base + "/commit", status_code=201)
    def create(pid: str, aid: str, key: str, body: Confirmation, user=dependency):
        offline()
        return commit(store, user, pid, aid, key, body, effective())

    @app.post(base + "/cancel")
    def stop(pid: str, aid: str, key: str, body: Cancellation, user=dependency):
        offline()
        return cancel(store, user, pid, aid, key, body, effective())

    @app.get("/api/internal/releases/{rid}/project-column-origin")
    def peer_origin(rid: str, user=dependency):
        # Cold execution needs this peer's authorization, not access to other
        # project applications. Never return their source bytes or proof cells.
        with store.tx(wait_seconds=min(30, effective().run_seconds)) as c:
            rel = lifecycle.read_release(store, c, user, rid, effective())
            snap = rel["snapshot"]
            evidence = source_evidence(store, c, user, snap, effective())
            origin = evidence["origin"]
            _, saved = columns.read_pair(c, user, origin["app_id"], patches.FINISH, origin["patch_key"], patches.Confirmation)
            peer = origin["source_app_id"]
            return dict(namespace=NAMESPACE, release_id=rid, release_fingerprint=rel["fingerprint"], **evidence,
                        affected=next(p for p in saved["affected"] if p["app_id"] == peer),
                        source=next(j for j in saved["jobs"] if j["app_id"] == peer and j["phase"] == "patched"))

    @app.get("/api/internal/approvals/{approval_id}/project-column-origin")
    def approval_origin(approval_id: str, user=dependency):
        with store.tx(wait_seconds=min(30, effective().run_seconds)) as c:
            row = c.execute(select(internal_approvals).where(internal_approvals.c.id == approval_id)).mappings().first()
            if row is None or row["principal_id"] != user or row["kind"] != "release":
                raise DomainError("PERMISSION_DENIED")
            lifecycle.approval(c, user, approval_id, row["fingerprint"], "release", allow_consumed=True)
            snap = row["payload"]["snapshot"]
            evidence = source_evidence(store, c, user, snap, effective())
            adapter.validate_family(c, user, approval_id, snap)
            return dict(namespace=NAMESPACE, approval_id=approval_id, approval_fingerprint=row["fingerprint"], **evidence)

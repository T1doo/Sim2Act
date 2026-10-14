"""Receipt-only terminal recovery of expired, explicitly cancelled PROJECT CHECKs."""

import time

from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound

from . import natural_spec_runtime as model
from . import natural_specs as codec
from . import pa_spec_apps as spec
from . import pb_natural_uses as uses
from .contracts import AppManifest
from .db import (
    events,
    internal_app_runs,
    internal_releases,
    internal_run_bindings,
    operations,
    runs,
)
from .errors import DomainError


def known_receipts(c, job, meta):
    """Prove durable accounting; never replay protected source or interpret semantics."""
    manifest = c.execute(select(
        internal_releases.c.snapshot["draft"]["candidate"]["manifest"]
    ).where(internal_releases.c.id == meta.release_id)).scalar_one()
    rows = model.counters(c, job, AppManifest.model_validate(manifest))
    spec.require(bool(rows), "Recovery requires an actual returned model attempt")
    ops = c.execute(select(operations).where(operations.c.run_id == job["id"])).mappings().all()
    spec.require(all(op["status"] in {"VERIFIED", "REJECTED_KNOWN"} for op in ops))
    by_id = {op["id"]: op for op in ops}
    for op in ops:
        if op["tool_ref"] not in codec.MODEL_KINDS:
            spec.require(op["status"] == "VERIFIED" and isinstance(op["receipt"], dict))
            anchors = c.execute(select(events.c.data).where(events.c.run_id == job["id"],
                events.c.kind == "SPEC_STEP_VERIFIED",
                events.c.data["operation_id"].as_string() == op["id"])).scalars().all()
            spec.require(len(anchors) == 1 and anchors[0]["step_id"] == op["call_id"]
                and 1 <= anchors[0]["fence"] <= job["fence"])
    for row in rows:
        spec.require(row["status"] in {"VERIFIED", "REJECTED_KNOWN"}
            and isinstance(row["usage"], dict) and row["usage"].get("status") == "known")
        info = row["parameters"]["natural_spec"]
        op = by_id[info["operation_id"]]
        spec.require(op["tool_ref"] in codec.MODEL_KINDS
            and op["status"] == row["status"] and op["call_id"] == info["step_id"]
            and info["created_at"] == job["created_at"]
            and 1 <= info["fence"] <= job["fence"]
            and 1 <= info["run_version"] <= job["version"])
        received = model.anchor(c, job["id"], "NS_RECEIVED", row["id"])
        spec.require(received == dict(attempt_id=row["id"],
            response_fingerprint=model.fingerprint(row["response"]),
            reception_fingerprint=model.fingerprint({**dict(row), "status": "RECEIVED"})))
        kind = "NS_REJECTED" if row["status"] == "REJECTED_KNOWN" else "NS_SETTLED"
        settled = model.anchor(c, job["id"], kind, row["id"])
        expected = dict(attempt_id=row["id"], attempt_fingerprint=model.fingerprint(dict(row)),
            operation_id=op["id"])
        if kind == "NS_REJECTED":
            spec.require(set(settled) == {*expected, "error"} and isinstance(settled["error"], str)
                and op["receipt"] is None)
            expected["error"] = settled["error"]
        else:
            spec.require(isinstance(op["receipt"], dict))
        spec.require(settled == expected)
    return rows


SCAN_LIMIT = 16


def recover_cancelled_checks(store, *, scan=None):
    """A new worker may stop a known CHECK, but gains no execution authority."""
    scan = {} if scan is None else scan
    with store.tx() as c:
        query = select(runs.c.id).join(internal_run_bindings,
            internal_run_bindings.c.run_id == runs.c.id).where(
                runs.c.status == "RECONCILING", runs.c.cancel_intent.is_(True),
                runs.c.lease_until <= time.time(),
                internal_run_bindings.c.snapshot["project_check"]["project_id"].as_string().is_not(None)
            )
        if scan.get("after") is not None:
            query = query.where(runs.c.id > scan["after"])
        ids = c.execute(query.order_by(runs.c.id).limit(SCAN_LIMIT)).scalars().all()
    scan["after"] = ids[-1] if ids else None
    for rid in ids:
        with store.tx() as c:
            owner = c.execute(select(runs.c.principal_id, runs.c.project_id).where(
                runs.c.id == rid)).mappings().first()
            if owner is None:
                continue
            try:
                store.lock_project(c, owner["principal_id"], owner["project_id"])
            except DomainError:
                continue
            job = c.execute(select(runs).where(runs.c.id == rid)
                .with_for_update()).mappings().one()
            if (job["status"] != "RECONCILING" or not job["cancel_intent"]
                    or job["lease_until"] > time.time() or job["result"] is not None
                    or store.has_unknown(c, rid)
                    or any(job[k] != owner[k] for k in ("principal_id", "project_id"))):
                continue
            try:
                scope = uses.control_scope(store, c, job["principal_id"], rid, lock=True)
                spec.require(scope is not None)
                header, app_run = scope
                meta, sealed = uses.pair(c, job["principal_id"], rid, spec.RUN_META,
                    "accepted", uses.RunScopeInput)
                spec.require(meta.model_dump() == sealed)
                from .project_natural_revalidation import control_binding

                reference = control_binding(store, c, job["principal_id"], header, meta)
                spec.require(reference is not None)
                state = c.execute(select(internal_app_runs.c.status).where(
                    internal_app_runs.c.id == app_run["id"])).scalar_one()
                spec.require(state == "RECONCILING")
                receipts = known_receipts(c, job, meta)
            except (DomainError, ValueError, KeyError, TypeError, NoResultFound):
                # Incomplete/corrupted evidence is not terminal authority.
                continue
            effects = store.known_effects(c, rid)
            changed = c.execute(update(runs).where(runs.c.id == rid,
                runs.c.status == "RECONCILING", runs.c.cancel_intent.is_(True),
                runs.c.version == job["version"], runs.c.fence == job["fence"],
                runs.c.lease_until <= time.time()).values(status="CANCELLED",
                    version=job["version"] + 1, fence=job["fence"] + 1, lease_until=0))
            spec.require(changed.rowcount == 1)
            changed_app = c.execute(update(internal_app_runs).where(
                internal_app_runs.c.id == app_run["id"], internal_app_runs.c.status == state,
                internal_app_runs.c.instance_id == meta.instance_id,
                internal_app_runs.c.principal_id == meta.principal_id,
                internal_app_runs.c.release_id == meta.release_id).values(status="CANCELLED"))
            spec.require(changed_app.rowcount == 1)
            receipt = dict(status="CANCELLED", reason="KNOWN_CANCEL_AFTER_LEASE",
                run_id=rid, app_run_id=meta.app_run_id, instance_id=meta.instance_id,
                release_id=meta.release_id, project_check=reference,
                previous_version=job["version"], version=job["version"] + 1,
                previous_fence=job["fence"], fence=job["fence"] + 1,
                effect_known=True, receipts_preserved=True,
                attempts=[dict(id=r["id"], fingerprint=model.fingerprint(dict(r))) for r in receipts],
                known_effects=effects)
            store.event(c, rid, "PROJECT_CHECK_CANCEL_RECOVERED", receipt)
            store.event(c, rid, "STATE", dict(status="CANCELLED", error=job["error"]))
            return True
    return False

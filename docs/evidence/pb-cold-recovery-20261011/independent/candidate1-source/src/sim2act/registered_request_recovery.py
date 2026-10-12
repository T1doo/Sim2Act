"""Private bounded text extraction intent journal; recovery never dispatches effects."""

import math
import time

from pydantic import Field
from sqlalchemy import insert, select, update

from .contracts import Strict
from .db import (
    app_drafts,
    fingerprint,
    internal_app_runs,
    internal_run_bindings,
    runs,
    task_extractions,
)
from .db import (
    registered_extraction_requests as journal,
)
from .errors import DomainError
from .registered_run_extraction import (
    TEXT_PROOF,
    RegisteredExtractionInput,
    _request,
    _target,
    verified_source,
)

NAMESPACE = "registered-text-request-identity.v1"
MAX_REQUESTS = 64
META = tuple(column for column in journal.c if column.name != "request")


class PrepareRequestInput(RegisteredExtractionInput):
    expected_latest_key: str | None = Field(default=None, min_length=1, max_length=100)
    expected_latest_candidate_fingerprint: str | None = Field(
        default=None, pattern=r"^[a-f0-9]{64}$"
    )


class CloseRequestInput(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_request_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_latest_key: str = Field(min_length=1, max_length=100)


def _scope(store, c, user, iid, rid):
    # Owner/project gate before full Run, request payload or original private lineage.
    pid = c.execute(
        select(runs.c.project_id).where(
            runs.c.id == rid,
            runs.c.principal_id == user,
        )
    ).scalar_one_or_none()
    store.lock_project(c, user, pid)
    binding = c.execute(
        select(internal_app_runs.c.instance_id)
        .select_from(
            internal_run_bindings.join(
                internal_app_runs, internal_run_bindings.c.app_run_id == internal_app_runs.c.id
            )
        )
        .where(internal_run_bindings.c.run_id == rid, internal_app_runs.c.principal_id == user)
    ).scalar_one_or_none()
    if binding != iid:
        raise DomainError("PERMISSION_DENIED")
    return pid


def _rows(c, user, rid):
    rows = [
        dict(row)
        for row in c.execute(
            select(*META)
            .where(
                journal.c.source_run_id == rid,
                journal.c.principal_id == user,
            )
            .order_by(journal.c.sequence)
        ).mappings()
    ]
    if len(rows) > MAX_REQUESTS:
        raise DomainError("VERSION_CONFLICT")
    for position, row in enumerate(rows):
        expected_history = ["PREPARED"] + ([] if row["state"] == "PREPARED" else [row["state"]])
        if (
            row["sequence"] != position + 1
            or row["previous_key"] != (rows[position - 1]["request_key"] if position else None)
            or row["state"] not in {"PREPARED", "COMMITTED", "CLOSED"}
            or not isinstance(row["history"], list)
            or not all(
                isinstance(entry, dict)
                and set(entry) == {"state", "at"}
                and type(entry["at"]) in {int, float}
                and math.isfinite(entry["at"])
                for entry in row["history"]
            )
            or [entry.get("state") for entry in row["history"]] != expected_history
            or (row["state"] == "PREPARED" and position != len(rows) - 1)
        ):
            raise DomainError("VERSION_CONFLICT", "Request identity history differs")
        effect = (
            c.execute(
                select(task_extractions.c.app_id, task_extractions.c.request_fingerprint).where(
                    task_extractions.c.task_id == rid,
                    task_extractions.c.principal_id == user,
                    task_extractions.c.request_key == row["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if row["state"] == "COMMITTED":
            actual_fp = c.execute(
                select(app_drafts.c.fingerprint).where(
                    app_drafts.c.id == row["app_id"],
                    app_drafts.c.project_id == row["project_id"],
                )
            ).scalar_one_or_none()
            if (
                not effect
                or effect["app_id"] != row["app_id"]
                or effect["request_fingerprint"] != row["request_fingerprint"]
                or actual_fp != row["candidate_fingerprint"]
            ):
                raise DomainError("VERSION_CONFLICT")
        elif effect or row["app_id"] is not None or row["candidate_fingerprint"] is not None:
            raise DomainError("VERSION_CONFLICT")
    return rows


def _meta(row):
    return {
        "namespace": NAMESPACE,
        **{key: value for key, value in row.items() if key != "request"},
    }


def _source(store, c, user, iid, rid, limits):
    pid = _scope(store, c, user, iid, rid)
    source, proof = verified_source(store, c, user, iid, rid, limits)
    if proof["kind"] != TEXT_PROOF or source["project_id"] != pid:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Finite initial text extraction only")
    return source, proof


def _check(row, source, request):
    if (
        row["instance_id"] != request["instance_id"]
        or row["source_run_id"] != request["source_run_id"]
        or row["project_id"] != source["project_id"]
        or row["source_app_id"] != source["id"]
        or row["target_app_id"] != request["target_app_id"]
        or row["expected_proof_fingerprint"] != request["expected_proof_fingerprint"]
        or row["expected_target_draft_fingerprint"] != request["expected_target_draft_fingerprint"]
        or row["request_fingerprint"] != fingerprint(request)
        or row["state"] not in {"PREPARED", "COMMITTED", "CLOSED"}
    ):
        raise DomainError("VERSION_CONFLICT", "Original request identity differs")


def index(store, user, iid, rid, limits):
    with store.tx() as c:
        source, _ = _source(store, c, user, iid, rid, limits)
        rows = _rows(c, user, rid)
        if any(
            row["instance_id"] != iid
            or row["project_id"] != source["project_id"]
            or row["source_app_id"] != source["id"]
            for row in rows
        ):
            raise DomainError("VERSION_CONFLICT")
        return {
            "namespace": NAMESPACE,
            "items": [_meta(row) for row in rows],
            "latest": _meta(rows[-1]) if rows else None,
        }


def project_index(store, user, pid):
    """Owner-only opaque discovery/stop metadata, usable without material grants."""
    with store.tx() as c:
        store.lock_project(c, user, pid)
        rows = (
            c.execute(
                select(journal.c.source_run_id)
                .select_from(
                    journal.join(
                        runs,
                        journal.c.source_run_id == runs.c.id,
                    )
                )
                .where(
                    journal.c.project_id == pid,
                    journal.c.principal_id == user,
                    runs.c.project_id == pid,
                    runs.c.principal_id == user,
                )
                .distinct()
                .limit(65)
            )
            .scalars()
            .all()
        )
        if len(rows) > 64:
            raise DomainError("BUDGET_EXHAUSTED", "Bounded project recovery index exhausted")
        latest = [_meta(_rows(c, user, rid)[-1]) for rid in rows]
        return {"namespace": NAMESPACE, "project_id": pid, "principal_id": user, "items": latest}


def read(store, user, iid, rid, key, limits):
    with store.tx() as c:
        source, proof = _source(store, c, user, iid, rid, limits)
        # Scope metadata first, then authorize the actual target before selecting request/name.
        rows = _rows(c, user, rid)
        row = next((r for r in rows if r["request_key"] == key), None)
        if not row or row["instance_id"] != iid or row["project_id"] != source["project_id"]:
            raise DomainError("PERMISSION_DENIED")
        target, _ = _target(store, c, user, source, row["target_app_id"], limits)
        request = c.execute(
            select(journal.c.request).where(
                journal.c.source_run_id == rid,
                journal.c.principal_id == user,
                journal.c.request_key == key,
                journal.c.instance_id == iid,
                journal.c.project_id == source["project_id"],
            )
        ).scalar_one()
        _check(row, source, request)
        if (
            request["expected_proof_fingerprint"] != fingerprint(proof)
            or request["expected_target_draft_fingerprint"] != target["fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT", "Prepared source/target changed")
        return {
            **_meta(row),
            "request": {**request, "request_key": key},
            "latest_key": rows[-1]["request_key"],
        }


def prepare(store, user, iid, rid, body, limits):
    key = body.request_key
    with store.tx() as c:
        source, proof = _source(store, c, user, iid, rid, limits)
        target, _ = _target(store, c, user, source, body.target_app_id, limits)
        request = _request(
            iid,
            rid,
            body.expected_proof_fingerprint,
            body.target_app_id,
            body.expected_target_draft_fingerprint,
            body.name,
        )
        if (
            fingerprint(proof) != body.expected_proof_fingerprint
            or target["fingerprint"] != body.expected_target_draft_fingerprint
        ):
            raise DomainError("VERSION_CONFLICT")
        rows = _rows(c, user, rid)
        old = next((row for row in rows if row["request_key"] == key), None)
        latest = rows[-1] if rows else None
        if old:
            _check(old, source, request)
            persisted = c.execute(
                select(journal.c.request).where(
                    journal.c.source_run_id == rid,
                    journal.c.principal_id == user,
                    journal.c.request_key == key,
                )
            ).scalar_one()
            if persisted != request:
                raise DomainError("VERSION_CONFLICT", "Prepared request payload differs")
            if (
                old != latest
                or old["state"] == "CLOSED"
                or old["previous_key"] != body.expected_latest_key
            ):
                raise DomainError("VERSION_CONFLICT", "Superseded original request")
            return _meta(old)
        if c.execute(
            select(task_extractions.c.app_id).where(
                task_extractions.c.task_id == rid,
                task_extractions.c.principal_id == user,
                task_extractions.c.request_key == key,
            )
        ).first():
            raise DomainError("VERSION_CONFLICT", "Legacy committed original key is read-only")
        if body.expected_latest_key != (latest["request_key"] if latest else None) or (
            latest and latest["state"] == "PREPARED"
        ):
            raise DomainError(
                "VERSION_CONFLICT", "Reconcile or explicitly close the previous request"
            )
        if latest and latest["state"] == "COMMITTED":
            # The exact real candidate is revalidated by the ordinary current-key receipt path.
            # No browser installation is asserted by this server-side state.
            if latest["candidate_fingerprint"] != body.expected_latest_candidate_fingerprint:
                raise DomainError("VERSION_CONFLICT")
            from .apps import load_draft

            draft, _, _, _ = load_draft(store, c, user, latest["app_id"], limits)
            if draft["fingerprint"] != body.expected_latest_candidate_fingerprint:
                raise DomainError("VERSION_CONFLICT")
        elif body.expected_latest_candidate_fingerprint is not None:
            raise DomainError("VERSION_CONFLICT")
        if len(rows) >= MAX_REQUESTS:
            raise DomainError("BUDGET_EXHAUSTED", "Bounded extraction request history exhausted")
        row = dict(
            source_run_id=rid,
            principal_id=user,
            request_key=key,
            project_id=source["project_id"],
            instance_id=iid,
            source_app_id=source["id"],
            target_app_id=body.target_app_id,
            expected_proof_fingerprint=body.expected_proof_fingerprint,
            expected_target_draft_fingerprint=body.expected_target_draft_fingerprint,
            sequence=len(rows) + 1,
            previous_key=body.expected_latest_key,
            request_fingerprint=fingerprint(request),
            request=request,
            state="PREPARED",
            app_id=None,
            candidate_fingerprint=None,
            history=[{"state": "PREPARED", "at": time.time()}],
        )
        c.execute(insert(journal).values(**row))
        return _meta(row)


def guard(c, user, iid, rid, key, source, request):
    rows = _rows(c, user, rid)
    row = next((row for row in rows if row["request_key"] == key), None)
    if not row:
        raise DomainError(
            "VERSION_CONFLICT", "Persist an explicit original request before extraction"
        )
    _check(row, source, request)
    persisted = c.execute(
        select(journal.c.request).where(
            journal.c.source_run_id == rid,
            journal.c.principal_id == user,
            journal.c.request_key == key,
            journal.c.instance_id == iid,
            journal.c.project_id == source["project_id"],
        )
    ).scalar_one()
    if persisted != request:
        raise DomainError("VERSION_CONFLICT", "Prepared request payload differs")
    if row != rows[-1] or row["state"] == "CLOSED":
        raise DomainError("VERSION_CONFLICT", "Original request closed or superseded")
    return row


def committed(c, row, draft):
    if row["state"] == "COMMITTED":
        if row["app_id"] != draft["id"] or row["candidate_fingerprint"] != draft["fingerprint"]:
            raise DomainError("VERSION_CONFLICT")
        return
    c.execute(
        update(journal)
        .where(
            journal.c.source_run_id == row["source_run_id"],
            journal.c.principal_id == row["principal_id"],
            journal.c.request_key == row["request_key"],
            journal.c.state == "PREPARED",
        )
        .values(
            state="COMMITTED",
            app_id=draft["id"],
            candidate_fingerprint=draft["fingerprint"],
            history=[*row["history"], {"state": "COMMITTED", "at": time.time()}],
        )
    )


def close(store, user, iid, rid, body):
    with store.tx() as c:
        pid = _scope(store, c, user, iid, rid)
        rows = _rows(c, user, rid)
        row = next((row for row in rows if row["request_key"] == body.request_key), None)
        if not row or row["instance_id"] != iid or row["project_id"] != pid:
            raise DomainError("PERMISSION_DENIED")
        if (
            row != rows[-1]
            or body.expected_latest_key != row["request_key"]
            or body.expected_request_fingerprint != row["request_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        # No request JSON, original Run contents, target bytes or old candidate are read here.
        effect = (
            c.execute(
                select(task_extractions.c.app_id, task_extractions.c.request_fingerprint).where(
                    task_extractions.c.task_id == rid,
                    task_extractions.c.principal_id == user,
                    task_extractions.c.request_key == row["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if row["state"] == "COMMITTED":
            if (
                not effect
                or effect["app_id"] != row["app_id"]
                or effect["request_fingerprint"] != row["request_fingerprint"]
            ):
                raise DomainError("VERSION_CONFLICT")
            return _meta(row)
        if effect or row["state"] not in {"PREPARED", "CLOSED"}:
            raise DomainError("VERSION_CONFLICT")
        if row["state"] == "PREPARED":
            row["state"] = "CLOSED"
            row["history"] = [*row["history"], {"state": "CLOSED", "at": time.time()}]
            c.execute(
                update(journal)
                .where(
                    journal.c.source_run_id == rid,
                    journal.c.principal_id == user,
                    journal.c.request_key == row["request_key"],
                )
                .values(state=row["state"], history=row["history"])
            )
        return _meta(row)

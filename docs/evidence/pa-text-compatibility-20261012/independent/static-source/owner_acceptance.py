"""Explicit human declarations for exact generated text releases; never publication.

Only append records. Existing source validators and actual Worker proofs remain authoritative.
Stopping uses scoped owner metadata even after source authorization has been withdrawn.
"""

import copy
import time
from typing import Annotated, Literal

from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import insert, select

from . import app_jobs, lifecycle, text_run_checks
from .apps import load_draft
from .contracts import Strict
from .db import (
    fingerprint,
    goal_cards,
    internal_app_runs,
    internal_instances,
    internal_owner_records,
    internal_owner_seals,
    new_id,
    operations,
    run_contracts,
    runs,
)
from .errors import DomainError
from .goals import GoalCardInput

VERSION = "owner.generated-text.v1"
MAX_RECORDS = 256
META = [x for x in internal_owner_records.c if x.name != "payload"]


class Intent(Strict):
    request_key: str = Field(min_length=1, max_length=100)
    expected_sequence: int = Field(ge=0)


class Prepare(Intent):
    command: Literal["PREPARE"]
    expected_revision: int = Field(ge=1)
    expected_release_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    run_ids: list[str] = Field(min_length=1, max_length=8)


class Choice(Strict):
    item_id: str = Field(min_length=1, max_length=100)
    decision: Literal["ACCEPT", "REJECT"]
    reason: str = Field(min_length=1, max_length=500)


class Decide(Intent):
    command: Literal["DECIDE"]
    review_id: str
    review_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    choices: list[Choice] = Field(min_length=1, max_length=100)


class Stop(Intent):
    command: Literal["CANCEL", "REVOKE"]
    target_id: str
    target_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=1, max_length=500)


def scope(store, c, user, iid):
    i = (
        c.execute(
            select(internal_instances.c.project_id, internal_instances.c.principal_id).where(
                internal_instances.c.id == iid
            )
        )
        .mappings()
        .first()
    )
    if not i or i["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    store.lock_project(c, user, i["project_id"])
    return i["project_id"]


def ledger(c, user, iid):
    rows = [
        dict(r)
        for r in c.execute(
            select(*META)
            .where(internal_owner_records.c.instance_id == iid)
            .order_by(internal_owner_records.c.sequence)
        ).mappings()
    ]
    seals = {
        r["record_id"]: r
        for r in c.execute(
            select(internal_owner_seals).where(internal_owner_seals.c.instance_id == iid)
        ).mappings()
    }
    if len(rows) != len(seals) or len(rows) > MAX_RECORDS:
        raise DomainError("VERSION_CONFLICT", "Owner history/seal missing")
    previous = ""
    for sequence, row in enumerate(rows, 1):
        seal = seals.get(row["id"])
        if (
            not seal
            or row["principal_id"] != user
            or row["sequence"] != sequence
            or row["previous_fingerprint"] != previous
            or any(
                seal[k] != row[k] for k in ("principal_id", "project_id", "instance_id", "sequence")
            )
            or seal["metadata_fingerprint"] != fingerprint(row)
            or seal["payload_fingerprint"] != row["fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT", "Immutable owner sequence/seal changed")
        previous = row["fingerprint"]
    return rows


def payload(c, row):
    value = c.execute(
        select(internal_owner_records.c.payload).where(internal_owner_records.c.id == row["id"])
    ).scalar()
    if (
        not isinstance(value, dict)
        or fingerprint(value) != row["fingerprint"]
        or value.get("metadata") != {k: v for k, v in row.items() if k != "fingerprint"}
        or fingerprint(value.get("request")) != row["request_fingerprint"]
    ):
        raise DomainError("VERSION_CONFLICT", "Immutable owner payload changed")
    return value


def base(store, c, user, iid, limits):
    i, release = lifecycle.instance(store, c, user, iid, limits, lock=True)
    frozen = release["snapshot"]["draft"]
    candidate = frozen["candidate"]
    from . import app_owner_goals, text_logic_reuse

    if text_logic_reuse.independent(frozen):
        from .text_continuations import execution

        execution(store, c, user, i, release, limits)
        current, _, _, _ = load_draft(store, c, user, frozen["id"], limits, lock=True)
        if current["fingerprint"] != frozen["fingerprint"]:
            raise DomainError("VERSION_CONFLICT", "Current app differs from exact release")
        own = app_owner_goals.current(store, c, user, current, limits)
        goal = GoalCardInput.model_validate(own["snapshot"]["content"]).model_dump()
        items = [{"id": "title", "kind": "title", "text": goal["title"]},
                 {"id": "goal", "kind": "goal", "text": goal["goal"]}]
        for field in ("known", "assumptions", "unresolved", "constraints", "acceptance_checks"):
            items.extend({"id": f"{field}:{n}", "kind": field, "text": text} for n, text in enumerate(goal[field]))
        items.extend({"id": f"applicability:{n}", "kind": "applicability", "text": text}
                     for n, text in enumerate(own["applicability"]))
        items.append({"id": "resource_scope", "kind": "resource_scope",
                      "text": str(own["anchor"]["resource_id"]) + " @ " + own["anchor"]["source_hash"]})
        items.append({"id": "technical_scope", "kind": "technical_scope",
                      "text": "Only case-sensitive literal full-line retrieval: TXT/MD <=4096 bytes/64 lines; trimmed term <=80 characters, <=16 citations. Semantic verification UNKNOWN; formal publication disabled."})
        return dict(version=VERSION, principal_id=user, project_id=i["project_id"], instance_id=iid,
            instance_revision=i["revision"], data_version=i["data_version"],
            instance_history_fingerprint=fingerprint(i["history"]), app_id=frozen["id"],
            draft_fingerprint=frozen["fingerprint"], release_id=release["id"], release_fingerprint=release["fingerprint"],
            source_goal=dict(card_id=own["card_id"], version=own["goal_version"], fingerprint=own["goal_fingerprint"],
                             snapshot=own["snapshot"], origin="THIS_APPLICATION_OWNER_AUTHORED"),
            own_goal_binding_fingerprint=own["binding_fingerprint"], applicability=own["applicability"],
            independent_logic=own["anchor"], current_limits=limits.model_dump(), goal=goal, items=items,
            grant_version=lifecycle.grant_version(c, i["project_id"], user),
            sample_input_fingerprint=release["snapshot"]["check_evidence"]["input_fingerprint"],
            technical_semantic_status="UNKNOWN", formal_publication_enabled=False,
            declaration_scope="EXACT_OWN_GOAL_RELEASE_INSTANCE_WORKER_EVIDENCE")
    if (
        "execution_source" in release["snapshot"]
        or not candidate.get("goal_application")
        or candidate["actions"][0]["executor"]["ref"] != "text.literal_evidence"
    ):
        raise DomainError(
            "UNSUPPORTED_CAPABILITY", "Owner review requires a generated text GoalCard"
        )
    current, _, _, _ = load_draft(store, c, user, frozen["id"], limits, lock=True)
    if current["fingerprint"] != frozen["fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "Current app differs from exact release")
    origin = (
        c.execute(select(runs).where(runs.c.id == candidate["goal_application"]["run_id"]))
        .mappings()
        .one()
    )
    source = store.frozen_contract(c, origin).source_goal_card.model_dump()
    head = (
        c.execute(select(goal_cards).where(goal_cards.c.id == source["card_id"])).mappings().first()
    )
    if (
        not head
        or head["project_id"] != i["project_id"]
        or head["version"] != source["version"]
        or head["fingerprint"] != source["fingerprint"]
    ):
        raise DomainError(
            "VERSION_CONFLICT", "Goal source head changed; generate a current version"
        )
    goal = GoalCardInput.model_validate(candidate["goal"]).model_dump()
    if goal != source["snapshot"]["content"]:
        raise DomainError("VERSION_CONFLICT")
    items = [{"id": "goal", "kind": "goal", "text": goal["goal"]}]
    for field in ("known", "assumptions", "unresolved", "constraints", "acceptance_checks"):
        items.extend(
            {"id": f"{field}:{n}", "kind": field, "text": text}
            for n, text in enumerate(goal[field])
        )
    return {
        "version": VERSION,
        "principal_id": user,
        "project_id": i["project_id"],
        "instance_id": iid,
        "instance_revision": i["revision"],
        "data_version": i["data_version"],
        "instance_history_fingerprint": fingerprint(i["history"]),
        "app_id": frozen["id"],
        "draft_fingerprint": frozen["fingerprint"],
        "release_id": release["id"],
        "release_fingerprint": release["fingerprint"],
        "source_goal": source,
        "goal": goal,
        "items": items,
        "grant_version": lifecycle.grant_version(c, i["project_id"], user),
        "sample_input_fingerprint": release["snapshot"]["check_evidence"]["input_fingerprint"],
        "technical_semantic_status": "UNKNOWN",
        "formal_publication_enabled": False,
    }


def context(store, c, user, iid, limits, run_ids):
    value = base(store, c, user, iid, limits)
    if not run_ids or len(run_ids) != len(set(run_ids)):
        raise DomainError("INVALID_INPUT", "Select distinct actual new-input runs")
    active = c.execute(
        select(internal_app_runs.c.id).where(
            internal_app_runs.c.instance_id == iid,
            internal_app_runs.c.status.not_in(["SUCCEEDED", "FAILED", "CANCELLED"]),
        )
    ).first()
    if active:
        raise DomainError("VERSION_CONFLICT", "Unfinished instance run blocks owner review")
    evidence = []
    for rid in run_ids:
        # Authorized exact instance first; never query unscoped old Run private fields.
        from .db import internal_run_bindings

        job = (
            c.execute(
                select(runs)
                .join(internal_run_bindings, internal_run_bindings.c.run_id == runs.c.id)
                .join(
                    internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id
                )
                .where(
                    runs.c.id == rid,
                    runs.c.principal_id == user,
                    internal_app_runs.c.instance_id == iid,
                )
            )
            .mappings()
            .first()
        )
        if not job:
            raise DomainError("PERMISSION_DENIED")
        s, a = app_jobs.load_binding(store, c, user, job, limits)
        if "own_goal_binding_fingerprint" in value:
            from .app_owner_goals import check_run

            review_draft, _, _, _ = load_draft(store, c, user, value["app_id"], limits)
            check_run(store, c, user, review_draft, limits, s)
        if (
            job["status"] != "SUCCEEDED"
            or a["status"] != "SUCCEEDED"
            or job["cancel_intent"]
            or job["error"] is not None
            or a["error"] is not None
            or store.has_unknown(c, rid)
            or s["expected_revision"] != value["instance_revision"]
            or s["release_id"] != value["release_id"]
            or fingerprint(s["input"]) == value["sample_input_fingerprint"]
        ):
            raise DomainError(
                "VERIFICATION_FAILED", "A current successful new-input Worker run is required"
            )
        text_run_checks.verify(store, c, user, job, limits)
        contract = c.execute(
            select(run_contracts.c.fingerprint).where(run_contracts.c.run_id == rid)
        ).scalar()
        records = [dict(r) for r in lifecycle.data_rows(c, iid) if r["run_id"] == a["id"]]
        receipts = [
            dict(r)
            for r in c.execute(
                select(operations).where(
                    operations.c.run_id == rid, operations.c.call_id == "instance_result"
                )
            ).mappings()
        ]
        evidence.append(
            {
                "run_id": rid,
                "run_version": job["version"],
                "run_fingerprint": job["fingerprint"],
                "contract_fingerprint": contract,
                "binding_fingerprint": fingerprint(s),
                "app_run": dict(a),
                "input": s["input"],
                "output": a["output"],
                "result_records": records,
                "actual_operations": receipts,
                "result_version": a["result_version"],
                "check": "source.literal_evidence.v1",
                "technical_status": "PASS",
                "semantic_status": "UNKNOWN",
            }
        )
    value["evidence"] = evidence
    return value


def public_state(store, c, user, iid, limits, rows):
    out = {
        "version": VERSION,
        "instance_id": iid,
        "sequence": len(rows),
        "owner_acceptance": "PENDING",
        "content_access": False,
        "formal_publication_enabled": False,
        "technical_semantic_status": "UNKNOWN",
        "history": rows,
        "latest": rows[-1] if rows else None,
    }
    try:
        current = base(store, c, user, iid, limits)
        # Validate all append-only payloads once current content authorization is established.
        for row in rows:
            payload(c, row)
        out.update(content_access=True, current=current)
        if "own_goal_binding_fingerprint" in current:
            # A stale historical declaration cannot hide the separately authorized
            # current own goal. This preview enables a fresh PREPARE, never DECIDE.
            out["prepare_current"] = copy.deepcopy(current)
        if rows:
            last = rows[-1]
            p = payload(c, last)
            if last["kind"] in {"CANCEL", "REVOKE"}:
                out["owner_acceptance"] = last["status"]
            else:
                fresh = context(store, c, user, iid, limits, p["run_ids"])
                if fingerprint(fresh) != fingerprint(p["contract"]):
                    raise DomainError("VERSION_CONFLICT", "Exact owner evidence changed")
                out["owner_acceptance"] = last["status"]
                if last["kind"] == "PREPARE" and time.time() >= p["expires_at"]:
                    out["owner_acceptance"] = "EXPIRED"
                out["record"] = {**last, "payload": p}
    except DomainError as e:
        out.pop("current", None)
        out.pop("record", None)
        out.update(
            content_access=False,
            invalidation_reason=e.code,
            owner_acceptance=(
                rows[-1]["status"]
                if rows and rows[-1]["kind"] in {"CANCEL", "REVOKE"}
                else "STALE"
                if rows
                else "PENDING"
            ),
        )
    return out


def read(store, user, iid, limits, key=None):
    with store.tx() as c:
        pid = scope(store, c, user, iid)
        app_id = c.execute(
            select(internal_instances.c.source_app_id).where(internal_instances.c.id == iid)
        ).scalar_one()
        rows = ledger(c, user, iid)
        state = public_state(store, c, user, iid, limits, rows)
        # Owned-instance metadata binds even empty or redacted reads to the selected scope.
        state.update(principal_id=user, project_id=pid, app_id=app_id)
        if key is not None:
            row = next((r for r in rows if r["request_key"] == key), None)
            if not row:
                raise DomainError("OUTCOME_UNKNOWN", "No receipt for this original request key")
            recovered = dict(row)
            if state["content_access"]:
                p = payload(c, row)
                try:
                    if (
                        row["kind"] in {"CANCEL", "REVOKE"}
                        or fingerprint(context(store, c, user, iid, limits, p["run_ids"])) == fingerprint(p["contract"])
                    ):
                        recovered["payload"] = p
                except DomainError:
                    pass  # Original receipt metadata remains recoverable when its content is stale.
            state["recovered"] = recovered
        return state


def append(c, user, pid, iid, rows, body, status, **detail):
    # Leave space for an explicit stop; a full budget must not trap an active declaration.
    reserve = 2 if body["command"] == "PREPARE" else 1 if body["command"] == "DECIDE" else 0
    if len(rows) >= MAX_RECORDS - reserve:
        raise DomainError("BUDGET_EXHAUSTED", "Owner history limit reached")
    metadata = {
        "id": new_id("iorecord"),
        "principal_id": user,
        "project_id": pid,
        "instance_id": iid,
        "sequence": len(rows) + 1,
        "request_key": body["request_key"],
        "request_fingerprint": fingerprint(body),
        "kind": body["command"],
        "status": status,
        "previous_fingerprint": rows[-1]["fingerprint"] if rows else "",
        "created_at": time.time(),
    }
    value = {"metadata": metadata, "request": body, **copy.deepcopy(detail)}
    row = {**metadata, "fingerprint": fingerprint(value)}
    c.execute(insert(internal_owner_records).values(**row, payload=value))
    c.execute(
        insert(internal_owner_seals).values(
            record_id=row["id"],
            instance_id=iid,
            principal_id=user,
            project_id=pid,
            sequence=row["sequence"],
            metadata_fingerprint=fingerprint(row),
            payload_fingerprint=row["fingerprint"],
        )
    )
    return row


def submit(store, user, iid, limits, body):
    with store.tx() as c:
        pid = scope(store, c, user, iid)
        rows = ledger(c, user, iid)
        old = next((r for r in rows if r["request_key"] == body["request_key"]), None)
        if old:
            if old["request_fingerprint"] != fingerprint(body):
                raise DomainError("VERSION_CONFLICT", "Original key intent differs")
            return old  # Historical receipt only; never re-activate an old decision.
        if body["expected_sequence"] != len(rows):
            raise DomainError("VERSION_CONFLICT", "Owner history changed; read current state")
        command = body["command"]
        if command == "PREPARE":
            frozen = context(store, c, user, iid, limits, body["run_ids"])
            for row in rows:
                payload(c, row)
            if (
                frozen["instance_revision"] != body["expected_revision"]
                or frozen["release_fingerprint"] != body["expected_release_fingerprint"]
            ):
                raise DomainError("VERSION_CONFLICT")
            return append(
                c,
                user,
                pid,
                iid,
                rows,
                body,
                "PENDING",
                contract=frozen,
                run_ids=body["run_ids"],
                expires_at=time.time() + 900,
            )
        if not rows:
            raise DomainError("VERSION_CONFLICT")
        last = rows[-1]
        if command in {"CANCEL", "REVOKE"}:
            allowed = last["kind"] == "PREPARE" if command == "CANCEL" else last["kind"] == "DECIDE"
            if (
                not allowed
                or body["target_id"] != last["id"]
                or body["target_fingerprint"] != last["fingerprint"]
                or not body["reason"].strip()
            ):
                raise DomainError("VERSION_CONFLICT")
            return append(
                c, user, pid, iid, rows, body, "CANCELLED" if command == "CANCEL" else "REVOKED"
            )
        if (
            last["kind"] != "PREPARE"
            or last["id"] != body["review_id"]
            or last["fingerprint"] != body["review_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        # Validate authority before accessing criteria/outputs, then re-check exact sources/evidence.
        base(store, c, user, iid, limits)
        for row in rows:
            payload(c, row)
        p = payload(c, last)
        fresh = context(store, c, user, iid, limits, p["run_ids"])
        if fingerprint(fresh) != fingerprint(p["contract"]) or time.time() >= p["expires_at"]:
            raise DomainError("VERSION_CONFLICT", "Owner preview is stale or expired")
        choices = body["choices"]
        if [x["item_id"] for x in choices] != [x["id"] for x in fresh["items"]] or any(
            not x["reason"].strip() for x in choices
        ):
            raise DomainError(
                "INVALID_INPUT",
                "Explicit ordered decision and reason for every frozen item required",
            )
        status = "ACCEPTED" if all(x["decision"] == "ACCEPT" for x in choices) else "REJECTED"
        return append(
            c,
            user,
            pid,
            iid,
            rows,
            body,
            status,
            contract=fresh,
            run_ids=p["run_ids"],
            choices=choices,
            review_id=last["id"],
        )


def mount(app, store, limits, identity):
    user_dependency = Depends(identity)

    @app.get("/api/internal/instances/{iid}/owner-review")
    def state(iid: str, request_key: str | None = None, user=user_dependency):
        try:
            return read(store, user, iid, limits, request_key)
        except DomainError as error:
            if error.code != "OUTCOME_UNKNOWN":
                raise
            return JSONResponse({"error": error.public()}, status_code=409)

    @app.post("/api/internal/instances/{iid}/owner-review-requests", status_code=201)
    def command(
        iid: str,
        body: Annotated[Prepare | Decide | Stop, Field(discriminator="command")],
        user=user_dependency,
    ):
        return {
            "formal_publication_enabled": False,
            "record": submit(store, user, iid, limits, body.model_dump()),
        }

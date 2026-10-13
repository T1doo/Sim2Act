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
    events,
    fingerprint,
    goal_cards,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_owner_records,
    internal_owner_seals,
    internal_run_bindings,
    local_effects,
    natural_owner_records,
    natural_owner_seals,
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

    @app.get("/api/internal/instances/{iid}/runs/{rid}/spec-owner-review")
    def natural_state(iid: str, rid: str, request_key: str | None = None, user=user_dependency):
        try:
            return natural_read(store, user, iid, rid, limits, request_key)
        except DomainError as error:
            if error.code != "OUTCOME_UNKNOWN":
                raise
            return JSONResponse({"error": error.public()}, status_code=409)

    @app.post("/api/internal/instances/{iid}/runs/{rid}/spec-owner-review-requests", status_code=201)
    def natural_command(iid: str, rid: str,
        body: Annotated[NaturalPrepare | Decide | Stop, Field(discriminator="command")],
        user=user_dependency):
        return dict(formal_publication_enabled=False,
            record=natural_submit(store, user, iid, rid, limits, body.model_dump()))

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


# Natural artifacts use a separate per-Run ledger. Generic text history is unchanged.
NATURAL_VERSION = "owner.natural-spec.v1"
NATURAL_META = [x for x in natural_owner_records.c if x.name != "payload"]


class NaturalPrepare(Intent):
    command: Literal["PREPARE"]
    expected_contract_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


def natural_scope(store, c, user, iid, rid):
    pid = scope(store, c, user, iid)
    linked = c.execute(select(internal_app_runs.c.id)
        .join(internal_run_bindings, internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
        .where(internal_run_bindings.c.run_id == rid, internal_app_runs.c.instance_id == iid,
            internal_app_runs.c.principal_id == user)).scalar()
    if not linked:
        raise DomainError("PERMISSION_DENIED")
    return pid


def natural_ledger(c, user, iid, rid):
    rows = [dict(r) for r in c.execute(select(*NATURAL_META)
        .where(natural_owner_records.c.run_id == rid)
        .order_by(natural_owner_records.c.sequence)).mappings()]
    seals = {r["record_id"]: r for r in c.execute(select(natural_owner_seals)
        .where(natural_owner_seals.c.run_id == rid)).mappings()}
    previous = ""
    if len(rows) != len(seals) or len(rows) > MAX_RECORDS:
        raise DomainError("VERSION_CONFLICT", "Natural owner seal missing")
    for n, row in enumerate(rows, 1):
        seal = seals.get(row["id"])
        if (not seal or row["principal_id"] != user or row["instance_id"] != iid
            or row["run_id"] != rid or row["sequence"] != n
            or row["previous_fingerprint"] != previous
            or seal["metadata_fingerprint"] != fingerprint(row)
            or seal["payload_fingerprint"] != row["fingerprint"]):
            raise DomainError("VERSION_CONFLICT", "Natural owner immutable metadata changed")
        previous = row["fingerprint"]
    return rows


def natural_payload(c, row):
    value = c.execute(select(natural_owner_records.c.payload)
        .where(natural_owner_records.c.id == row["id"])).scalar()
    if (not isinstance(value, dict) or fingerprint(value) != row["fingerprint"]
        or value.get("metadata") != {k: v for k, v in row.items() if k != "fingerprint"}
        or fingerprint(value.get("request")) != row["request_fingerprint"]):
        raise DomainError("VERSION_CONFLICT", "Natural owner immutable payload changed")
    return value


def natural_context(store, c, user, iid, rid, limits):
    from . import natural_specs
    from . import pa_spec_apps as spec
    spec.require(spec.job_scope_gate(store, c, user, rid))
    # Authorize saved artifact BEFORE full Run, AppRun, typed body or owner payload.
    header = c.execute(select(runs.c.runtime_id, runs.c.project_id, runs.c.status)
        .where(runs.c.id == rid, runs.c.principal_id == user)).mappings().one()
    committed = c.execute(select(events.c.data["artifact_resource"].as_string())
        .where(events.c.run_id == rid, events.c.kind == "SPEC_COMMITTED")).scalars().all()
    effects = c.execute(select(local_effects.c.resource_id)
        .join(operations, operations.c.id == local_effects.c.operation_id)
        .where(operations.c.run_id == rid, operations.c.tool_ref == spec.SAVE,
            operations.c.status == "VERIFIED")).scalars().all()
    # JSON scalar identifiers are public scope metadata; never select output/data bodies here.
    linked = c.execute(select(internal_app_runs.c.id,
        internal_app_runs.c.output["resource_id"].as_string().label("artifact"))
        .join(internal_run_bindings, internal_run_bindings.c.app_run_id == internal_app_runs.c.id)
        .where(internal_run_bindings.c.run_id == rid,
            internal_app_runs.c.instance_id == iid, internal_app_runs.c.principal_id == user)).mappings().one()
    accepted = c.execute(select(events.c.data["instance_id"].as_string().label("iid"),
        events.c.data["app_run_id"].as_string().label("aid"))
        .where(events.c.run_id == rid, events.c.kind == "ACCEPTED",
            events.c.data["namespace"].as_string() == app_jobs.KIND)).mappings().all()
    spec.require(len(accepted) == 1 and accepted[0]["iid"] == iid
        and accepted[0]["aid"] == linked["id"], "Route differs from independently accepted Run scope")
    typed_artifacts = c.execute(select(internal_instance_data.c.data["result"]["resource_id"].as_string())
        .where(internal_instance_data.c.instance_id == iid,
            internal_instance_data.c.run_id == linked["id"])).scalars().all()
    spec.require(header["status"] == "SUCCEEDED" and len(committed) == 1
        and committed == effects == typed_artifacts == [linked["artifact"]],
        "Exact successful saved artifact required")
    store.authorize(c, user, header["runtime_id"], header["project_id"], committed[0], "resource.read")
    job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    binding, _, proved = spec.verify_job(store, c, user, job, limits)
    a, snap, release = binding["app_run"], binding["snapshot"], binding["release"]
    spec.require(natural_specs.is_candidate(binding["draft"]["candidate"])
        and a["instance_id"] == iid and a["output"]["resource_id"] == committed[0])
    i = dict(c.execute(select(internal_instances).where(internal_instances.c.id == iid)).mappings().one())
    spec.require(i["revision"] == snap["expected_revision"] and i["release_id"] == release["id"]
        and i["data_version"] == a["result_version"], "Selected result is no longer current")
    spec.require(c.execute(select(internal_app_runs.c.id).where(
        internal_app_runs.c.instance_id == iid,
        internal_app_runs.c.status.not_in(["SUCCEEDED", "FAILED", "CANCELLED"]))).first() is None,
        "A new result is still in progress")
    typed = dict(c.execute(select(internal_instance_data).where(
        internal_instance_data.c.instance_id == iid, internal_instance_data.c.run_id == a["id"])).mappings().one())
    goal = binding["goal"]
    head = c.execute(select(goal_cards.c.version, goal_cards.c.fingerprint).where(
        goal_cards.c.id == goal["card_id"], goal_cards.c.project_id == i["project_id"])).mappings().first()
    spec.require(head is not None and head["version"] == goal["version"] and head["fingerprint"] == goal["fingerprint"],
        "This Run Goal version is no longer current")
    content = goal["snapshot"]["content"]
    items = [dict(id="goal", text=content["goal"])]
    for name in ("known", "assumptions", "unresolved", "constraints", "acceptance_checks"):
        items.extend(dict(id=f"{name}.{n}", text=text) for n, text in enumerate(content[name], 1))
    items.append(dict(id="source-and-result", text="核对原文、成果的条件、例外、关系与未决项；引用 PASS 不证明语义正确"))
    spec.require(len(items) <= 100)
    return dict(version=NATURAL_VERSION, principal_id=user, project_id=i["project_id"],
        instance_id=iid, app_id=i["source_app_id"], run_id=rid, app_run_id=a["id"],
        instance_revision=i["revision"], release_id=release["id"], release_fingerprint=release["fingerprint"],
        effective_plan_fingerprint=fingerprint(binding["draft"]["candidate"]),
        source_goal=goal, goal=content, items=items, material=binding["source"],
        result_version=a["result_version"], typed_fingerprint=typed["fingerprint"],
        output_fingerprint=fingerprint(a["output"]), output=a["output"],
        actual_operations=proved, grant_version=lifecycle.grant_version(c, i["project_id"], user),
        technical_semantic_status="UNKNOWN", formal_publication_enabled=False)


def natural_append(c, user, pid, iid, rid, rows, body, status, **details):
    reserve = 2 if body["command"] == "PREPARE" else 1 if body["command"] == "DECIDE" else 0
    if len(rows) + 1 + reserve > MAX_RECORDS:
        raise DomainError("BUDGET_EXCEEDED")
    row = dict(id=new_id("nowner"), run_id=rid, principal_id=user, project_id=pid,
        instance_id=iid, sequence=len(rows)+1, request_key=body["request_key"],
        request_fingerprint=fingerprint(body), kind=body["command"], status=status,
        previous_fingerprint=rows[-1]["fingerprint"] if rows else "", created_at=time.time())
    value = dict(metadata=copy.deepcopy(row), request=copy.deepcopy(body), **copy.deepcopy(details))
    row["fingerprint"] = fingerprint(value)
    c.execute(insert(natural_owner_records).values(**row, payload=value))
    c.execute(insert(natural_owner_seals).values(record_id=row["id"], run_id=rid,
        metadata_fingerprint=fingerprint(row), payload_fingerprint=row["fingerprint"]))
    return row


def natural_read(store, user, iid, rid, limits, key=None):
    with store.tx() as c:
        pid = natural_scope(store, c, user, iid, rid)
        rows = natural_ledger(c, user, iid, rid)
        app_id = c.execute(select(internal_instances.c.source_app_id)
            .where(internal_instances.c.id == iid)).scalar()
        last = rows[-1] if rows else None
        out = dict(version=NATURAL_VERSION, principal_id=user, project_id=pid, instance_id=iid,
            app_id=app_id, run_id=rid, sequence=len(rows), history=rows, latest=last,
            owner_acceptance=last["status"] if last else "PENDING", content_access=False,
            technical_semantic_status="UNKNOWN", formal_publication_enabled=False)
        recovered = next((r for r in rows if r["request_key"] == key), None) if key else None
        if key and not recovered:
            raise DomainError("OUTCOME_UNKNOWN", "Original human declaration key not found")
        try:
            fresh = natural_context(store, c, user, iid, rid, limits)
            values = {r["id"]: natural_payload(c, r) for r in rows}
            if last and last["kind"] in {"PREPARE", "DECIDE"}:
                p = values[last["id"]]
                if fingerprint(fresh) != fingerprint(p["contract"]):
                    raise DomainError("VERSION_CONFLICT", "Exact human review context changed")
                out["record"] = dict(last, payload=p)
                if last["kind"] == "PREPARE" and time.time() >= p["expires_at"]:
                    out["owner_acceptance"] = "EXPIRED"
            out.update(content_access=True, current=fresh)
            if recovered and fingerprint(values[recovered["id"]].get("contract", fresh)) == fingerprint(fresh):
                recovered = dict(recovered, payload=values[recovered["id"]])
        except DomainError as error:
            out.pop("record", None)
            out["invalidation_reason"] = error.code
            if last and last["kind"] not in {"CANCEL", "REVOKE"}:
                out["owner_acceptance"] = "STALE"
        if recovered:
            out["recovered"] = recovered
        return out



def natural_final_gate(store, c, user, iid, rid, fresh, *, expires_at=None):
    """Last precommit metadata/permission check; full proof was verified in this locked tx."""
    from . import pa_spec_apps as spec
    spec.require(spec.job_scope_gate(store, c, user, rid))
    runtime = c.execute(select(runs.c.runtime_id).where(runs.c.id == rid)).scalar_one()
    for resource in [fresh["material"]["resource_id"], fresh["output"]["resource_id"]]:
        store.authorize(c, user, runtime, fresh["project_id"], resource, "resource.read")
    head = c.execute(select(goal_cards.c.version, goal_cards.c.fingerprint)
        .where(goal_cards.c.id == fresh["source_goal"]["card_id"],
            goal_cards.c.project_id == fresh["project_id"])).mappings().first()
    instance = c.execute(select(internal_instances.c.revision, internal_instances.c.data_version,
        internal_instances.c.release_id).where(internal_instances.c.id == iid)).mappings().one()
    spec.require(head is not None and head["version"] == fresh["source_goal"]["version"]
        and head["fingerprint"] == fresh["source_goal"]["fingerprint"]
        and instance["revision"] == fresh["instance_revision"]
        and instance["data_version"] == fresh["result_version"]
        and instance["release_id"] == fresh["release_id"]
        and lifecycle.grant_version(c, fresh["project_id"], user) == fresh["grant_version"]
        and (expires_at is None or time.time() < expires_at), "Human review changed before commit")


def natural_submit(store, user, iid, rid, limits, body):
    guard = {}
    with app_jobs.submission_tx(store, guard) as c:
        pid = natural_scope(store, c, user, iid, rid)
        rows = natural_ledger(c, user, iid, rid)
        old = next((r for r in rows if r["request_key"] == body["request_key"]), None)
        if old:
            if old["request_fingerprint"] != fingerprint(body):
                raise DomainError("VERSION_CONFLICT", "Original declaration key differs")
            return old
        guard["proof"] = dict(namespace="natural-owner-submission-rejection.v1",
            principal_id=user, project_id=pid, instance_id=iid, run_id=rid,
            request_key=body["request_key"], request_fingerprint=fingerprint(body),
            acceptance="NOT_ACCEPTED", previous_request="ABSENT", phase="TRANSACTION_ROLLED_BACK")
        if body["expected_sequence"] != len(rows):
            raise DomainError("VERSION_CONFLICT", "Human declaration sequence changed")
        last = rows[-1] if rows else None
        command = body["command"]
        if command in {"CANCEL", "REVOKE"}:
            if (not last or last["kind"] != ("PREPARE" if command == "CANCEL" else "DECIDE")
                or last["id"] != body["target_id"] or last["fingerprint"] != body["target_fingerprint"]
                or not body["reason"].strip()):
                raise DomainError("VERSION_CONFLICT")
            return natural_append(c, user, pid, iid, rid, rows, body,
                "CANCELLED" if command == "CANCEL" else "REVOKED")
        fresh = natural_context(store, c, user, iid, rid, limits)
        values = {r["id"]: natural_payload(c, r) for r in rows}
        if command == "PREPARE":
            if fingerprint(fresh) != body["expected_contract_fingerprint"]:
                raise DomainError("VERSION_CONFLICT", "Selected result preview changed")
            row = natural_append(c, user, pid, iid, rid, rows, body, "PENDING",
                contract=fresh, expires_at=time.time()+900)
            natural_final_gate(store, c, user, iid, rid, fresh)
            return row
        if (not last or last["kind"] != "PREPARE" or last["id"] != body["review_id"]
            or last["fingerprint"] != body["review_fingerprint"]):
            raise DomainError("VERSION_CONFLICT")
        p = values[last["id"]]
        if fingerprint(fresh) != fingerprint(p["contract"]) or time.time() >= p["expires_at"]:
            raise DomainError("VERSION_CONFLICT", "Human preview stale or expired")
        choices = body["choices"]
        if ([v["item_id"] for v in choices] != [v["id"] for v in fresh["items"]]
            or any(not v["reason"].strip() for v in choices)):
            raise DomainError("INVALID_INPUT", "Explicit ordered choices and reasons required")
        row = natural_append(c, user, pid, iid, rid, rows, body,
            "ACCEPTED" if all(v["decision"] == "ACCEPT" for v in choices) else "REJECTED",
            contract=fresh, choices=choices, review_id=last["id"])
        natural_final_gate(store, c, user, iid, rid, fresh, expires_at=p["expires_at"])
        return row

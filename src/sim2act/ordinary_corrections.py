"""One explicit new ordinary Run from an exact rejected result; never auto repair."""

from typing import Literal

from fastapi import Depends
from sqlalchemy import insert, select

from . import ordinary_owner_review as human
from .contracts import (
    OrdinaryCorrection,
    OrdinaryCorrectionFeedback,
    OrdinaryCorrectionIssue,
    OrdinaryCorrectionRequest,
)
from .db import (
    events,
    fingerprint,
    local_effects,
    operations,
    ordinary_correction_links,
    run_contracts,
    runs,
)
from .errors import DomainError

VERSION: Literal["ordinary-goal-correction.v1"] = "ordinary-goal-correction.v1"
CONSENT = "RUN_NEW_CORRECTION_KEEP_GOAL_CRITERIA_AND_HISTORY"


def require(value, message="Exact rejected ordinary result required"):
    if not value:
        raise DomainError("VERSION_CONFLICT", message)


def parent_hint(c, rid):
    saved = c.execute(
        select(
            run_contracts.c.snapshot["ordinary_correction"]["feedback"]["parent_run_id"].as_string()
        ).where(run_contracts.c.run_id == rid)
    ).scalar()
    accepted = (
        c.execute(
            select(
                events.c.data["ordinary_correction"]["feedback"]["parent_run_id"].as_string()
            ).where(events.c.run_id == rid, events.c.kind == "ACCEPTED")
        )
        .scalars()
        .all()
    )
    marker = c.execute(
        select(runs.c.context["ordinary_correction_parent"].as_string()).where(runs.c.id == rid)
    ).scalar()
    linked = c.execute(
        select(ordinary_correction_links.c.parent_run_id).where(
            ordinary_correction_links.c.run_id == rid
        )
    ).scalar()
    if (
        saved is None
        and marker is None
        and linked is None
        and not any(v is not None for v in accepted)
    ):
        return None
    require(
        isinstance(saved, str)
        and accepted == [saved]
        and marker == saved
        and linked == saved
        and saved != rid,
        "Correction source markers differ",
    )
    return saved


def evidence_scope(store, c, rid, header, *, completed_parent):
    frozen = (
        c.execute(
            select(
                run_contracts.c.snapshot["resources"].label("materials"),
                run_contracts.c.snapshot["source_goal_card"]["snapshot"]["content"][
                    "resource_refs"
                ].label("refs"),
                run_contracts.c.snapshot["human_review"]["version"].as_string().label("version"),
            ).where(run_contracts.c.run_id == rid)
        )
        .mappings()
        .one()
    )
    require(
        isinstance(frozen["materials"], list)
        and 1 <= len(frozen["materials"]) <= 8
        and all(
            isinstance(v, dict) and isinstance(v.get("resource_id"), str)
            for v in frozen["materials"]
        )
        and all(
            isinstance(refs, list) and all(isinstance(v, str) for v in refs)
            for refs in (header["resource_refs"], frozen["refs"])
        )
        and frozen["version"] in (human.VERSION, human.MD_VERSION),
        "Invalid evidence identifier projections",
    )
    material_ids = [v["resource_id"] for v in frozen["materials"]]
    for material in set(header["resource_refs"] + frozen["refs"] + material_ids):
        store.authorize(
            c,
            header["principal_id"],
            header["runtime_id"],
            header["project_id"],
            material,
            "resource.read",
        )
    require(
        header["resource_refs"] == frozen["refs"] and set(material_ids) == set(frozen["refs"]),
        "Parent material identifier projections differ",
    )
    effects = (
        c.execute(
            select(local_effects.c.resource_id)
            .join(operations, operations.c.id == local_effects.c.operation_id)
            .where(
                operations.c.run_id == rid,
                operations.c.tool_ref == "artifact.save_text",
                operations.c.status == "VERIFIED",
            )
        )
        .scalars()
        .all()
    )
    receipt_ids = (
        c.execute(
            select(operations.c.receipt["artifact_refs"]).where(
                operations.c.run_id == rid,
                operations.c.tool_ref == "artifact.save_text",
                operations.c.status == "VERIFIED",
            )
        )
        .scalars()
        .all()
    )
    # A damaged receipt cannot hide the independently committed resource from authority checks.
    for artifact in effects:
        store.authorize(
            c,
            header["principal_id"],
            header["runtime_id"],
            header["project_id"],
            artifact,
            "resource.read",
        )
    require(
        (
            (len(effects) == 1 if completed_parent else len(effects) <= 1)
            and receipt_ids == [[artifact] for artifact in effects]
        )
        if frozen["version"] == human.MD_VERSION
        else not effects and not receipt_ids,
        "Parent MD effect/receipt identifiers differ",
    )


def scope_gate(store, c, rid):
    """Identifier projections and current source/output authority before feedback bodies."""
    parent = parent_hint(c, rid)
    if parent is None:
        return
    child = (
        c.execute(
            select(
                runs.c.id,
                runs.c.principal_id,
                runs.c.project_id,
                runs.c.runtime_id,
                runs.c.resource_refs,
            ).where(runs.c.id == rid)
        )
        .mappings()
        .one()
    )
    header = (
        c.execute(
            select(
                runs.c.id,
                runs.c.principal_id,
                runs.c.project_id,
                runs.c.runtime_id,
                runs.c.resource_refs,
            ).where(runs.c.id == parent)
        )
        .mappings()
        .first()
    )
    link = (
        c.execute(
            select(ordinary_correction_links).where(ordinary_correction_links.c.run_id == rid)
        )
        .mappings()
        .one()
    )
    require(
        header is not None
        and all(header[k] == child[k] for k in ("principal_id", "project_id", "runtime_id"))
        and all(link[k] == child[k] for k in ("principal_id", "project_id"))
        and parent_hint(c, parent) is None,
        "Only one ordinary correction edge is supported",
    )
    from .goal_applications import source_scope_gate

    evidence_scope(store, c, parent, header, completed_parent=True)
    evidence_scope(store, c, rid, child, completed_parent=False)
    source_scope_gate(store, c, parent)
    store.authorize_receipts(c, header)


def stable(value):
    # Current authority is always checked separately. A child MD legitimately creates
    # two read Grants; that must not invalidate its own frozen parent evidence.
    return {k: v for k, v in value.items() if k != "grant_version"}


def feedback(store, c, user, rid, *, admission):
    require(parent_hint(c, rid) is None, "Corrections of corrections are outside this slice")
    fresh = human.context(store, c, user, rid, _lock_project=admission)
    rows = human.ledger(c, user, rid)
    last = rows[-1] if rows else None
    if last is None:
        raise DomainError("VERSION_CONFLICT", "The latest declaration must be an explicit rejection")
    require(
        last["kind"] == "DECIDE" and last["status"] == "REJECTED",
        "The latest declaration must be an explicit rejection",
    )
    value = human.payload(c, last)
    require(
        fingerprint(fresh if admission else stable(fresh))
        == fingerprint(value["contract"] if admission else stable(value["contract"])),
        "Rejected result evidence changed",
    )
    choices = value["choices"]
    require([v["item_id"] for v in choices] == [v["id"] for v in fresh["items"]])
    issues = [
        OrdinaryCorrectionIssue(item_id=item["id"], criterion=item["text"], reason=choice["reason"])
        for item, choice in zip(fresh["items"], choices, strict=True)
        if choice["decision"] == "REJECT"
    ]
    parent = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
    contract = store.frozen_contract(c, parent)
    require(
        contract.mode == "mock" and contract.human_review is not None,
        "Ordinary correction has zero real model allowance",
    )
    result = OrdinaryCorrectionFeedback(
        version=VERSION,
        parent_run_id=rid,
        parent_contract_fingerprint=fresh["contract_fingerprint"],
        parent_result_version=fresh["result_version"],
        parent_output_fingerprint=fresh["output_fingerprint"],
        stable_parent_fingerprint=fingerprint(stable(fresh)),
        declaration_id=last["id"],
        declaration_fingerprint=last["fingerprint"],
        declaration_sequence=last["sequence"],
        materials=contract.resources,
        issues=issues,
        previous_output=fresh["output"],
        previous_artifacts=fresh.get("artifacts", []),
    ).model_dump()
    return result, fresh, contract


def preview_value(details, source, contract, limits, authority):
    value = dict(
        version=VERSION,
        principal_id=source["principal_id"],
        project_id=source["project_id"],
        parent_run_id=details["parent_run_id"],
        feedback=details,
        source_goal=source["source_goal"],
        human_review=contract.human_review.model_dump(),
        limits=limits,
        mode="mock",
        request_model="intern-s2",
        authority_version=authority,
        consent=CONSENT,
        real_model_allowance=0,
        owner_acceptance="PENDING",
        automatic_goal_acceptance="NOT_RUN",
        semantic_status="UNKNOWN",
        formal_publication_enabled=False,
        **(
            {"artifact_delivery": contract.artifact_delivery.model_dump()}
            if contract.artifact_delivery
            else {}
        ),
    )
    return {**value, "preview_fingerprint": fingerprint(value)}


def make_preview(store, c, user, rid, limits):
    details, fresh, contract = feedback(store, c, user, rid, admission=True)
    proposed = {k: min(v, contract.limits.model_dump()[k]) for k, v in limits.model_dump().items()}
    proposed["max_repairs"] = 0
    return preview_value(details, fresh, contract, proposed, fresh["grant_version"])


def validate(store, c, run, contract, *, raw):
    selected = contract.ordinary_correction
    if selected is None:
        require(parent_hint(c, run["id"]) is None, "Correction policy was removed")
        return
    require(raw is not None and fingerprint(raw) == fingerprint(selected.model_dump()))
    parent = parent_hint(c, run["id"])
    require(
        parent == selected.feedback.parent_run_id
        and contract.mode == "mock"
        and contract.limits.max_repairs == 0
        and contract.source_goal_card is not None
        and not any(
            getattr(contract, k) is not None
            for k in ("natural_planning", "application_generation", "ordinary_csv_report")
        )
    )
    current, fresh, original = feedback(store, c, run["principal_id"], parent, admission=False)
    require(
        current == selected.feedback.model_dump()
        and contract.source_goal_card.model_dump() == fresh["source_goal"]
        and contract.resources == original.resources
        and contract.human_review == original.human_review
        and contract.artifact_delivery == original.artifact_delivery
        and all(
            v <= original.limits.model_dump()[k] for k, v in contract.limits.model_dump().items()
        ),
        "Frozen correction differs from exact original Goal, materials or rejection",
    )
    proposed = preview_value(
        current, fresh, original, contract.limits.model_dump(), selected.authority_version
    )
    request = selected.request
    link = (
        c.execute(
            select(ordinary_correction_links).where(ordinary_correction_links.c.run_id == run["id"])
        )
        .mappings()
        .one()
    )
    require(
        request.expected_preview_fingerprint == proposed["preview_fingerprint"]
        and request.declaration_id == current["declaration_id"]
        and request.declaration_fingerprint == current["declaration_fingerprint"]
        and request.expected_sequence == current["declaration_sequence"]
        and request.request_key == run["request_key"]
        and link["request_fingerprint"] == fingerprint(request.model_dump())
    )


def receipt(store, c, user, parent, run):
    scope_gate(store, c, run["id"])
    contract = store.frozen_contract(c, run)
    require(
        contract.ordinary_correction is not None
        and contract.ordinary_correction.feedback.parent_run_id == parent
    )
    selected = contract.ordinary_correction
    return dict(
        version=VERSION,
        status="ACCEPTED",
        run_id=run["id"],
        parent_run_id=parent,
        principal_id=user,
        project_id=run["project_id"],
        request_key=run["request_key"],
        request_fingerprint=fingerprint(selected.request.model_dump()),
        feedback_fingerprint=fingerprint(selected.feedback.model_dump()),
        contract_fingerprint=fingerprint(contract.model_dump(exclude_none=True)),
        owner_acceptance="PENDING",
        automatic_goal_acceptance="NOT_RUN",
        semantic_status="UNKNOWN",
        real_model_allowance=0,
        formal_publication_enabled=False,
    )


def scoped_request_run(store, c, user, pid, parent, key):
    rid = c.execute(
        select(runs.c.id).where(
            runs.c.principal_id == user, runs.c.project_id == pid, runs.c.request_key == key
        )
    ).scalar()
    if rid is None:
        return None
    require(parent_hint(c, rid) == parent, "Original key belongs to a different correction source")
    from .goal_applications import source_scope_gate

    source_scope_gate(store, c, rid)
    return c.execute(select(runs).where(runs.c.id == rid)).mappings().one()


def submit(store, user, parent, body, limits):
    from .app_jobs import submission_tx

    guard: dict[str, dict[str, str]] = {}
    with submission_tx(store, guard) as c:
        pid = human.scope(store, c, user, parent)
        old = scoped_request_run(store, c, user, pid, parent, body["request_key"])
        if old:
            current = store.frozen_contract(c, old)
            require(
                current.ordinary_correction is not None
                and current.ordinary_correction.request.model_dump() == body,
                "Original key belongs to different input",
            )
            return receipt(store, c, user, parent, old)
        guard["proof"] = dict(
            namespace="ordinary-correction-submission-rejection.v1",
            principal_id=user,
            project_id=pid,
            parent_run_id=parent,
            request_key=body["request_key"],
            request_fingerprint=fingerprint(body),
            acceptance="NOT_ACCEPTED",
            previous_request="ABSENT",
            phase="TRANSACTION_ROLLED_BACK",
        )
        value = make_preview(store, c, user, parent, limits)
        require(
            body["expected_preview_fingerprint"] == value["preview_fingerprint"]
            and body["declaration_id"] == value["feedback"]["declaration_id"]
            and body["declaration_fingerprint"] == value["feedback"]["declaration_fingerprint"]
            and body["expected_sequence"] == value["feedback"]["declaration_sequence"]
        )
        # Independent accepted/snapshot/context identifiers keep the one-child slot.
        sibling = c.execute(
            select(runs.c.id)
            .join(run_contracts, run_contracts.c.run_id == runs.c.id)
            .where(
                runs.c.project_id == pid,
                (
                    (
                        run_contracts.c.snapshot["ordinary_correction"]["feedback"][
                            "parent_run_id"
                        ].as_string()
                        == parent
                    )
                    | (runs.c.context["ordinary_correction_parent"].as_string() == parent)
                    | runs.c.id.in_(
                        select(events.c.run_id).where(
                            events.c.kind == "ACCEPTED",
                            events.c.data["ordinary_correction"]["feedback"][
                                "parent_run_id"
                            ].as_string()
                            == parent,
                        )
                    )
                ),
            )
        ).first()
        require(
            not sibling
            and not c.execute(
                select(ordinary_correction_links.c.run_id).where(
                    ordinary_correction_links.c.parent_run_id == parent
                )
            ).first(),
            "This rejected result already has its one accepted correction",
        )
        selected = OrdinaryCorrection(
            feedback=value["feedback"],
            authority_version=value["authority_version"],
            request=body,
            real_model_allowance=0,
        ).model_dump()
        source = value["source_goal"]
        rid = store.submit_tx(
            c,
            user,
            pid,
            "",
            [],
            body["request_key"],
            policy=dict(
                limits=value["limits"],
                mode="mock",
                request_model="intern-s2",
                human_review=value["human_review"],
                ordinary_correction=selected,
                **(
                    {"artifact_delivery": value["artifact_delivery"]}
                    if "artifact_delivery" in value
                    else {}
                ),
            ),
            goal_source={k: source[k] for k in ("card_id", "version", "fingerprint")},
        )
        c.execute(
            insert(ordinary_correction_links).values(
                parent_run_id=parent,
                run_id=rid,
                principal_id=user,
                project_id=pid,
                request_fingerprint=fingerprint(body),
            )
        )
        require(
            make_preview(store, c, user, parent, limits) == value,
            "Rejection changed before acceptance commit",
        )
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        return receipt(store, c, user, parent, run)


def mount(app, store, limits, identity, settings):
    dependency = Depends(identity)

    def mock_only():
        if settings.mode != "mock" or settings.live_enabled:
            raise DomainError(
                "PERMISSION_DENIED", "Ordinary correction is Mock-only; real model allowance 0"
            )

    @app.get("/api/runs/{rid}/correction-preview")
    def preview(rid: str, user=dependency):
        mock_only()
        with store.tx() as c:
            return make_preview(store, c, user, rid, limits)

    @app.post("/api/runs/{rid}/correction-runs", status_code=202)
    def create(rid: str, body: OrdinaryCorrectionRequest, user=dependency):
        mock_only()
        return submit(store, user, rid, body.model_dump(), limits)

    @app.get("/api/runs/{rid}/correction-requests/{key}")
    def recover(rid: str, key: str, user=dependency):
        if not 1 <= len(key) <= 100:
            raise DomainError("INVALID_INPUT")
        with store.tx() as c:
            pid = human.scope(store, c, user, rid)
            run = scoped_request_run(store, c, user, pid, rid, key)
            if run is None:
                raise DomainError("OUTCOME_UNKNOWN", "Original correction key not accepted")
            return receipt(store, c, user, rid, run)

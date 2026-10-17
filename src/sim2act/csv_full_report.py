"""Explicit saved complete CSV report recipe; existing ordinary Run, no new executor.

The saved recipe is immutable v1, not an AppRelease or an implicit project Grant.
Every use freezes and separately confirms a new original CSV report contract.
"""

import time
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import insert, select, update

from .contracts import Limits, Strict
from .db import (
    csv_report_workflow_uses as uses,
)
from .db import (
    csv_report_workflows as workflows,
)
from .db import (
    events,
    fingerprint,
    new_id,
    projects,
    resources,
    run_contracts,
    runs,
)
from .errors import DomainError

VERSION = "csv-full-report-workflow.v1"
FAMILY = "CSV_FULL_REPORT"
EVENT = "CSV_FULL_REPORT_USE"


class ExtractInput(Strict):
    name: str = Field(min_length=1, max_length=100)
    expected_definition_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)
    consent: Literal["SAVE_READ_SUM_COMPLETE_MD_WORKFLOW"]


class UseInput(Strict):
    expected_version: int = Field(strict=True, ge=1, le=1)
    expected_definition_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    column: str = Field(min_length=1, max_length=32768)
    request_key: str = Field(min_length=1, max_length=100)
    consent: Literal["PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY"]


def require(value):
    if not value:
        raise DomainError("VERSION_CONFLICT", "完整CSV报告流程的来源、定义或逐次绑定已改变")


def source_definition(store, c, user, rid, limits):
    from .ordinary_csv import GOAL, RULES, TOOLS
    from .ordinary_csv import VERSION as CONTRACT
    from .ordinary_csv_extraction import source, source_scope
    from .tools import definitions

    header = source_scope(store, c, user, rid)
    # Keep provenance finite: extract only original complete ordinary reports,
    # never relabel a SUM_ONLY app or recursively extract a workflow use.
    require(not c.execute(select(uses.c.run_id).where(uses.c.run_id == rid)).first())
    require(
        not c.execute(
            select(events.c.id).where(events.c.run_id == rid, events.c.kind == EVENT)
        ).first()
    )
    require(
        c.execute(
            select(runs.c.context["csv_full_report_use"]).where(runs.c.id == rid)
        ).scalar_one()
        is None
    )
    if limits is None:
        limits = Limits.model_validate(
            c.execute(
                select(run_contracts.c.snapshot["limits"]).where(run_contracts.c.run_id == rid)
            ).scalar_one()
        )
    _, proof = source(store, c, user, rid, limits)
    require(
        fingerprint(c.execute(select(runs.c.result).where(runs.c.id == rid)).scalar_one())
        == proof["result_fingerprint"]
    )
    contract = c.execute(
        select(run_contracts.c.snapshot).where(run_contracts.c.run_id == rid)
    ).scalar_one()
    return dict(
        version=VERSION,
        definition_version=1,
        scope="READ_SUM_SAVE_COMPLETE_MD",
        source={
            key: proof[key]
            for key in (
                "source_run_id",
                "source_run_version",
                "run_fingerprint",
                "contract_fingerprint",
                "confirmation_fingerprint",
                "source_goal_id",
                "source_goal_fingerprint",
                "result_fingerprint",
                "receipts_fingerprint",
                "source_task_acceptance",
                "source_resource_id",
                "source_hash",
                "source_report_hash",
            )
        },
        project_id=header["project_id"],
        runtime_id=header["runtime_id"],
        goal=GOAL,
        contract_version=CONTRACT,
        rules=list(RULES),
        tools=dict(TOOLS),
        tool_definitions_fingerprint=fingerprint(definitions()),
        limits=contract["limits"],
        formatter="ordinary_csv.report_text.v1",
        variable_inputs=["authorized_csv_resource_id", "numeric_column"],
        execution="EXISTING_ORDINARY_CSV_REPORT_RUN",
        model_requests=0,
        semantic_acceptance="NOT_RUN",
        owner_acceptance="PENDING",
        publishable=False,
    )


def header(store, c, user, aid):
    row = (
        c.execute(
            select(
                workflows.c.id,
                workflows.c.principal_id,
                workflows.c.project_id,
                workflows.c.runtime_id,
                workflows.c.source_run_id,
            ).where(workflows.c.id == aid, workflows.c.principal_id == user)
        )
        .mappings()
        .first()
    )
    if row is None:
        raise DomainError("PERMISSION_DENIED")
    project = store.lock_project(c, user, row["project_id"])
    require(project["runtime_id"] == row["runtime_id"])
    from .ordinary_csv_extraction import source_scope

    source_scope(store, c, user, row["source_run_id"])
    store.authorize(
        c, user, row["runtime_id"], row["project_id"], row["project_id"], "artifact.save_text"
    )
    return row


def checked(store, c, user, aid, limits):
    h = header(store, c, user, aid)
    definition = source_definition(store, c, user, h["source_run_id"], limits)
    row = dict(c.execute(select(workflows).where(workflows.c.id == aid)).mappings().one())
    require(fingerprint(row["definition"]) == row["fingerprint"] == fingerprint(definition))
    return row


def summary(row):
    return {key: row[key] for key in ("id", "name", "project_id")} | dict(
        use_family=FAMILY,
        definition_version=1,
        csv_instance_candidate=False,
        state="SAVED_WORKFLOW",
        publishable=False,
    )


def summaries(c, user):
    return [
        summary(row)
        for row in c.execute(
            select(workflows.c.id, workflows.c.name, workflows.c.project_id)
            .join(projects, projects.c.id == workflows.c.project_id)
            .where(workflows.c.principal_id == user, projects.c.owner_id == user)
            .order_by(workflows.c.created_at.desc())
        ).mappings()
    ]


def extract(store, user, rid, body, limits):
    with store.tx() as c:
        definition = source_definition(store, c, user, rid, limits)
        p = store.lock_project(c, user, definition["project_id"])
        store.authorize(c, user, p["runtime_id"], p["id"], p["id"], "artifact.save_text")
        require(fingerprint(definition) == body.expected_definition_fingerprint)
        previous = (
            c.execute(
                select(workflows).where(
                    workflows.c.principal_id == user,
                    workflows.c.source_run_id == rid,
                    workflows.c.request_key == body.request_key,
                )
            )
            .mappings()
            .first()
        )
        request_fp = fingerprint(body.model_dump())
        if previous:
            require(previous["request_fingerprint"] == request_fp)
            row = checked(store, c, user, previous["id"], limits)
        else:
            row = dict(
                id=new_id("app"),
                principal_id=user,
                project_id=p["id"],
                runtime_id=p["runtime_id"],
                source_run_id=rid,
                request_key=body.request_key,
                request_fingerprint=request_fp,
                name=body.name,
                definition=definition,
                fingerprint=fingerprint(definition),
                created_at=time.time(),
            )
            c.execute(insert(workflows).values(**row))
        return summary(row) | dict(fingerprint=row["fingerprint"])


def inspect(store, user, aid, limits):
    with store.tx() as c:
        row = checked(store, c, user, aid, limits)
        materials = []
        for material in c.execute(
            select(resources.c.id, resources.c.name, resources.c.hash).where(
                resources.c.project_id == row["project_id"], resources.c.format == "csv"
            )
        ).mappings():
            try:
                for tool in ("resource.read", "data.aggregate_csv"):
                    store.authorize(
                        c, user, row["runtime_id"], row["project_id"], material["id"], tool
                    )
            except DomainError:
                continue
            materials.append(dict(material))
        history = [
            dict(r)
            for r in c.execute(
                select(uses.c.run_id, uses.c.request_key).where(
                    uses.c.workflow_id == aid, uses.c.principal_id == user
                )
            ).mappings()
        ]
        return summary(row) | dict(
            fingerprint=row["fingerprint"],
            definition=row["definition"],
            input_guidance={"mode": FAMILY},
            materials=materials,
            history=history,
        )


def scope_gate(store, c, rid):
    """Reauthorize scalar identity/material union before protected Run/recipe bodies."""
    link = (
        c.execute(
            select(
                uses.c.workflow_id, uses.c.principal_id, uses.c.project_id, uses.c.resource_id
            ).where(uses.c.run_id == rid)
        )
        .mappings()
        .first()
    )
    hint = (
        c.execute(
            select(
                runs.c.principal_id,
                runs.c.project_id,
                runs.c.runtime_id,
                runs.c.context["csv_full_report_use"]["workflow_id"].as_string().label("aid"),
                runs.c.context["csv_full_report_use"]["fingerprint"].as_string().label("fp"),
            ).where(runs.c.id == rid)
        )
        .mappings()
        .first()
    )
    anchored = (
        c.execute(
            select(events.c.data["workflow_id"].as_string()).where(
                events.c.run_id == rid, events.c.kind == EVENT
            )
        )
        .scalars()
        .all()
    )
    if (
        link is None
        and not anchored
        and (hint is None or hint["aid"] is None and hint["fp"] is None)
    ):
        return
    require(
        link is not None
        and hint is not None
        and anchored == [link["workflow_id"]]
        and hint["aid"] == link["workflow_id"]
        and link["principal_id"] == hint["principal_id"]
        and link["project_id"] == hint["project_id"]
    )
    h = header(store, c, link["principal_id"], link["workflow_id"])
    require(h["project_id"] == hint["project_id"] and h["runtime_id"] == hint["runtime_id"])
    frozen = (
        c.execute(
            select(
                run_contracts.c.fingerprint,
                run_contracts.c.snapshot["ordinary_csv_report"]["resource_id"]
                .as_string()
                .label("resource"),
                run_contracts.c.snapshot["goal"]["resource_refs"].label("refs"),
                run_contracts.c.snapshot["resources"][0]["resource_id"]
                .as_string()
                .label("material"),
            ).where(run_contracts.c.run_id == rid)
        )
        .mappings()
        .first()
    )
    refs = c.execute(select(runs.c.resource_refs).where(runs.c.id == rid)).scalar_one()
    require(frozen is not None and isinstance(refs, list) and isinstance(frozen["refs"], list))
    from .db import local_effects, operation_intents, operations

    intents = (
        c.execute(
            select(operation_intents.c.request["args"]["resource_id"].as_string())
            .join(operations, operations.c.id == operation_intents.c.operation_id)
            .where(
                operations.c.run_id == rid,
                operations.c.tool_ref.in_(["resource.read", "data.aggregate_csv"]),
            )
        )
        .scalars()
        .all()
    )
    ids = (
        refs
        + frozen["refs"]
        + [frozen["resource"], frozen["material"], link["resource_id"]]
        + intents
    )
    require(all(isinstance(resource, str) for resource in ids))
    for resource in set(ids):
        for tool in ("resource.read", "data.aggregate_csv"):
            store.authorize(
                c, link["principal_id"], hint["runtime_id"], hint["project_id"], resource, tool
            )
    require(
        refs
        == frozen["refs"]
        == [link["resource_id"]]
        == [frozen["resource"]]
        == [frozen["material"]]
        and all(resource == link["resource_id"] for resource in intents)
    )
    effects = (
        c.execute(
            select(local_effects.c.resource_id)
            .join(operations, operations.c.id == local_effects.c.operation_id)
            .where(operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text")
        )
        .scalars()
        .all()
    )
    receipt_refs = (
        c.execute(
            select(operations.c.receipt["artifact_refs"]).where(
                operations.c.run_id == rid, operations.c.tool_ref == "artifact.save_text"
            )
        )
        .scalars()
        .all()
    )
    for output in effects:
        store.authorize(
            c, link["principal_id"], hint["runtime_id"], hint["project_id"], output, "resource.read"
        )
    if effects:
        require(len(effects) == 1 and receipt_refs == [effects])
    else:
        require(all(refs in (None, []) for refs in receipt_refs))
    # Source limits reconstruct provenance only; new uses independently bound current limits.
    row = checked(store, c, link["principal_id"], link["workflow_id"], None)
    saved = c.execute(select(uses).where(uses.c.run_id == rid)).mappings().one()
    binding = saved["binding"]
    require(saved["fingerprint"] == fingerprint(binding) == hint["fp"])
    require(
        fingerprint(binding)
        == fingerprint(
            dict(
                version=VERSION,
                workflow_id=row["id"],
                definition_version=1,
                definition_fingerprint=row["fingerprint"],
                run_id=rid,
                principal_id=hint["principal_id"],
                project_id=hint["project_id"],
                runtime_id=hint["runtime_id"],
                resource_id=link["resource_id"],
                request_key=saved["request_key"],
                request_fingerprint=saved["request_fingerprint"],
                contract_fingerprint=frozen["fingerprint"],
            )
        )
    )
    event_bindings = (
        c.execute(select(events.c.data).where(events.c.run_id == rid, events.c.kind == EVENT))
        .scalars()
        .all()
    )
    require(len(event_bindings) == 1 and fingerprint(event_bindings[0]) == fingerprint(binding))


def accepted(store, c, user, aid, key, limits):
    row = checked(store, c, user, aid, limits)
    link = c.execute(
        select(uses.c.run_id).where(
            uses.c.workflow_id == aid, uses.c.principal_id == user, uses.c.request_key == key
        )
    ).scalar_one_or_none()
    if link is None:
        raise DomainError("RESOURCE_NOT_FOUND", "尚无该原请求的接受回执")
    scope_gate(store, c, link)
    return dict(
        workflow_id=aid,
        definition_version=1,
        definition_fingerprint=row["fingerprint"],
        run_id=link,
        mode="DETERMINISTIC",
        model_requests=0,
    )


def use(store, user, aid, body, limits, policy):
    from .ordinary_csv import PrepareInput, prepare_tx

    with store.tx() as c:
        row = checked(store, c, user, aid, limits)
        require(body.expected_definition_fingerprint == row["fingerprint"])
        request_fp = fingerprint(body.model_dump())
        previous = c.execute(
            select(uses.c.request_fingerprint).where(
                uses.c.workflow_id == aid,
                uses.c.principal_id == user,
                uses.c.request_key == body.request_key,
            )
        ).scalar_one_or_none()
        if previous is not None:
            require(previous == request_fp)
            return accepted(store, c, user, aid, body.request_key, limits)
        bounded = {
            key: min(value, limits.model_dump()[key])
            for key, value in row["definition"]["limits"].items()
        }
        prepared = prepare_tx(
            store,
            c,
            user,
            row["project_id"],
            PrepareInput(
                resource_id=body.resource_id,
                column=body.column,
                request_key="full-report-" + fingerprint([user, aid, body.request_key])[:64],
            ),
            {**policy, "limits": bounded},
        )
        rid = prepared["run_id"]
        contract_fp = c.execute(
            select(run_contracts.c.fingerprint).where(run_contracts.c.run_id == rid)
        ).scalar_one()
        binding = dict(
            version=VERSION,
            workflow_id=aid,
            definition_version=1,
            definition_fingerprint=row["fingerprint"],
            run_id=rid,
            principal_id=user,
            project_id=row["project_id"],
            runtime_id=row["runtime_id"],
            resource_id=body.resource_id,
            request_key=body.request_key,
            request_fingerprint=request_fp,
            contract_fingerprint=contract_fp,
        )
        seal = fingerprint(binding)
        c.execute(
            insert(uses).values(
                run_id=rid,
                workflow_id=aid,
                principal_id=user,
                project_id=row["project_id"],
                resource_id=body.resource_id,
                request_key=body.request_key,
                request_fingerprint=request_fp,
                binding=binding,
                fingerprint=seal,
            )
        )
        context = c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar_one()
        require("csv_full_report_use" not in context)
        c.execute(
            update(runs)
            .where(runs.c.id == rid)
            .values(
                context={
                    **context,
                    "csv_full_report_use": {"workflow_id": aid, "fingerprint": seal},
                }
            )
        )
        store.event(c, rid, EVENT, binding)
        scope_gate(store, c, rid)
        return accepted(store, c, user, aid, body.request_key, limits)


def mount(app, store, limits, identity, settings):
    dependency = Depends(identity)

    @app.get("/api/runs/{rid}/csv-full-report-workflow-options")
    def options(rid: str, user=dependency):
        with store.tx() as c:
            definition = source_definition(store, c, user, rid, limits)
            return dict(definition=definition, fingerprint=fingerprint(definition))

    @app.post("/api/runs/{rid}/csv-full-report-workflows", status_code=201)
    def save(rid: str, body: ExtractInput, user=dependency):
        return extract(store, user, rid, body, limits)

    @app.get("/api/runs/{rid}/csv-full-report-workflow-requests/{key}")
    def recover_extraction(rid: str, key: str, user=dependency):
        with store.tx() as c:
            source_definition(store, c, user, rid, limits)
            aid = c.execute(
                select(workflows.c.id).where(
                    workflows.c.principal_id == user,
                    workflows.c.source_run_id == rid,
                    workflows.c.request_key == key,
                )
            ).scalar_one_or_none()
            if aid is None:
                raise DomainError("RESOURCE_NOT_FOUND")
            row = checked(store, c, user, aid, limits)
            return summary(row) | dict(fingerprint=row["fingerprint"])

    @app.post("/api/apps/{aid}/csv-full-report-uses", status_code=202)
    def prepare_use(aid: str, body: UseInput, user=dependency):
        return use(
            store, user, aid, body, limits, {"mode": settings.mode, "request_model": settings.model}
        )

    @app.get("/api/apps/{aid}/csv-full-report-use-requests/{key}")
    def recover_use(aid: str, key: str, user=dependency):
        with store.tx() as c:
            return accepted(store, c, user, aid, key, limits)

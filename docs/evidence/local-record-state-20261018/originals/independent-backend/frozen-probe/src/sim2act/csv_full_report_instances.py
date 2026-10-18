"""Bounded internal delivery of the existing complete CSV report recipe.

This is a lifecycle adapter, not an executor. Every use is an ordinary prospective
CSV contract; its existing confirmation, three tools and complete MD check own execution.
"""

import copy
from typing import Literal

from fastapi import Depends
from pydantic import Field, ValidationError
from sqlalchemy import insert, select, update

from . import csv_full_report as workflow
from . import lifecycle
from .contracts import Strict, validate_value
from .db import (
    csv_report_workflow_uses,
    csv_report_workflows,
    events,
    fingerprint,
    new_id,
    run_contracts,
    runs,
)
from .db import (
    delivery_graph_requests as journal,
)
from .db import (
    internal_app_runs as app_runs,
)
from .db import (
    internal_approvals as approvals,
)
from .db import (
    internal_instance_data as data,
)
from .db import (
    internal_instances as instances,
)
from .db import (
    internal_releases as releases,
)
from .errors import DomainError

VERSION = "csv-full-report-instances.v1"
RELEASE = VERSION + ".release"
SWITCH = VERSION + ".switch"
JOB = VERSION + ".use"
EVENT = "CSV_FULL_REPORT_INSTANCE_USE"
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "PARTIAL"}
require = workflow.require


def checked_recipe(store, c, user, aid):
    """Reuse an unchanged proof only inside this transaction and write epoch."""
    tx, epoch = c.get_transaction(), c.info.get("source_proof_write_epoch", 0)
    cached = c.info.get("complete_report_recipe_proofs")
    if cached is None or cached["tx"] is not tx or cached["epoch"] != epoch:
        cached = dict(tx=tx, epoch=epoch, values={})
        c.info["complete_report_recipe_proofs"] = cached
    key = (user, aid)
    old = cached["values"].get(key)
    if old is not None:
        store.recheck_proof_authorities(c, old)
        require(c.info.get("source_proof_write_epoch", 0) == epoch)
        return copy.deepcopy(old["row"])
    with store.proof_authorities(c) as authorities:
        row = workflow.checked(store, c, user, aid, None)
    if c.get_transaction() is tx and c.info.get("source_proof_write_epoch", 0) == epoch:
        cached["values"][key] = dict(
            row=copy.deepcopy(dict(row)), _call_authorities=tuple(authorities)
        )
    return row


class ApprovalInput(Strict):
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReleaseInput(Strict):
    expected_definition_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)
    consent: Literal["FREEZE_COMPLETE_MD_RECIPE_AND_CHECK"]


class UseInput(Strict):
    expected_revision: int = Field(ge=1)
    expected_release_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    column: str = Field(min_length=1, max_length=32768)
    request_key: str = Field(min_length=1, max_length=100)
    consent: Literal["PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY"]


class SwitchInput(Strict):
    target_release_id: str = Field(min_length=1, max_length=100)
    expected_target_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_revision: int = Field(ge=1)
    request_key: str = Field(min_length=1, max_length=100)


def is_snapshot(snapshot):
    return isinstance(snapshot, dict) and snapshot.get("namespace") == VERSION


def pair(c, user, scope, kind, key):
    rows = (
        c.execute(
            select(journal).where(
                journal.c.app_id == scope,
                journal.c.principal_id == user,
                journal.c.kind.in_([kind, kind + "_seal"]),
                journal.c.request_key == key,
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None
    require(len(rows) == 2)
    left, right = rows
    value = left["snapshot"]
    require(
        isinstance(value, dict)
        and set(value) == {"namespace", "request", "response"}
        and value["namespace"] == VERSION
        and isinstance(value["request"], dict)
        and isinstance(value["response"], dict)
    )
    require(
        fingerprint(left["snapshot"]) == fingerprint(right["snapshot"])
        and fingerprint(left["snapshot"]) == left["fingerprint"] == right["fingerprint"]
        and left["request_fingerprint"]
        == right["request_fingerprint"]
        == fingerprint(left["snapshot"]["request"])
    )
    return copy.deepcopy(left["snapshot"])


def record(c, user, scope, kind, key, request, response):
    value = dict(namespace=VERSION, request=request, response=response)
    for tag in (kind, kind + "_seal"):
        c.execute(
            insert(journal).values(
                app_id=scope,
                principal_id=user,
                kind=tag,
                request_key=key,
                request_fingerprint=fingerprint(request),
                snapshot=value,
                fingerprint=fingerprint(value),
            )
        )


def snapshot(row):
    # No AppManifest is invented to stand in for the three-tool workflow.
    fields = dict(
        ordinary_run_id="string",
        contract_fingerprint="string",
        result_fingerprint="string",
        report_resource_id="string",
        report_hash="string",
        source_resource_id="string",
        column="string",
        count="integer",
        sum="string",
    )
    result_schema = dict(
        type="object",
        required=list(fields),
        additionalProperties=False,
        properties={k: dict(type=v) for k, v in fields.items()},
    )
    return dict(
        namespace=VERSION,
        draft=dict(
            id=row["id"],
            project_id=row["project_id"],
            runtime_id=row["runtime_id"],
            candidate=dict(namespace=VERSION),
            fingerprint=row["fingerprint"],
        ),
        definition=copy.deepcopy(row["definition"]),
        definition_version=1,
        data_schema=dict(
            type="object",
            required=["result", "release_ref"],
            additionalProperties=False,
            properties=dict(result=result_schema, release_ref=dict(type="string")),
        ),
        data_schema_version=1,
        check_evidence=dict(
            status="PASS",
            ref="csv.complete-md-contract.v1",
            source=copy.deepcopy(row["definition"]["source"]),
            definition_fingerprint=row["fingerprint"],
            semantic_acceptance="NOT_RUN",
            owner_acceptance="PENDING",
        ),
        model_requests=0,
        formal_publication_enabled=False,
    )


def release_gate(store, c, user, *, release_id=None, approval_id=None):
    """Authorize independent scalar family hints before any lifecycle private body."""
    hints = set()
    if release_id is not None:
        header = (
            c.execute(
                select(
                    releases.c.approval_id,
                    releases.c.snapshot["draft"]["id"].as_string().label("app_id"),
                ).where(releases.c.id == release_id, releases.c.principal_id == user)
            )
            .mappings()
            .first()
        )
        if header:
            approval_id = header["approval_id"]
            hints.add(header["app_id"])
    if approval_id is not None:
        hints.add(
            c.execute(
                select(approvals.c.payload["snapshot"]["draft"]["id"].as_string()).where(
                    approvals.c.id == approval_id, approvals.c.principal_id == user
                )
            ).scalar_one_or_none()
        )
        hints.update(
            c.execute(
                select(journal.c.app_id).where(
                    journal.c.principal_id == user,
                    journal.c.kind.in_([RELEASE, RELEASE + "_seal"]),
                    journal.c.snapshot["response"]["id"].as_string() == approval_id,
                )
            )
            .scalars()
            .all()
        )
    known = []
    for aid in hints - {None}:
        if c.execute(
            select(csv_report_workflows.c.id).where(csv_report_workflows.c.id == aid)
        ).first():
            known.append(checked_recipe(store, c, user, aid))
    if not known:
        return None
    require(len(known) == 1 and hints - {None} == {known[0]["id"]})
    return known[0]


def validate_approval(store, c, user, aid, *, commit=False):
    row = release_gate(store, c, user, approval_id=aid)
    require(row is not None)
    a = (
        c.execute(select(approvals).where(approvals.c.id == aid, approvals.c.principal_id == user))
        .mappings()
        .one()
    )
    lifecycle.approval(c, user, aid, a["fingerprint"], "release", allow_consumed=True)
    p = a["payload"]
    require(
        set(p)
        == {
            "snapshot",
            "grant_version",
            "approval_id",
            "principal_id",
            "project_id",
            "kind",
            "expires_at",
        }
    )
    require(fingerprint(p["snapshot"]) == fingerprint(snapshot(row)))
    keys = (
        c.execute(
            select(journal.c.request_key).where(
                journal.c.app_id == row["id"],
                journal.c.principal_id == user,
                journal.c.kind.in_([RELEASE, RELEASE + "_seal"]),
                journal.c.snapshot["response"]["id"].as_string() == aid,
            )
        )
        .scalars()
        .all()
    )
    require(len(set(keys)) == 1)
    entry = pair(c, user, row["id"], RELEASE, keys[0])
    require(
        entry is not None
        and entry["response"]
        == dict(
            id=aid, fingerprint=a["fingerprint"], snapshot_fingerprint=fingerprint(p["snapshot"])
        )
        and entry["request"]["expected_definition_fingerprint"] == row["fingerprint"]
    )
    if commit:
        require(p["grant_version"] == lifecycle.grant_version(c, row["project_id"], user))
    return a


def validate_release(store, c, user, r):
    row = release_gate(store, c, user, release_id=r["id"])
    require(row is not None)
    a = validate_approval(store, c, user, r["approval_id"])
    require(
        a["consumed"]
        and r["project_id"] == row["project_id"]
        and fingerprint(r["snapshot"])
        == fingerprint(a["payload"]["snapshot"])
        == fingerprint(snapshot(row))
        and r["fingerprint"] == fingerprint(r["snapshot"])
    )
    return r


def prepare_release(store, user, aid, body):
    with store.tx() as c:
        row = checked_recipe(store, c, user, aid)
        require(row["fingerprint"] == body.expected_definition_fingerprint)
        old = pair(c, user, aid, RELEASE, body.request_key)
        if old:
            require(old["request"] == body.model_dump())
            return dict(validate_approval(store, c, user, old["response"]["id"]))
        snap = snapshot(row)
        accepted = lifecycle.new_approval(
            c,
            user,
            row["project_id"],
            "release",
            dict(snapshot=snap, grant_version=lifecycle.grant_version(c, row["project_id"], user)),
        )
        record(
            c,
            user,
            aid,
            RELEASE,
            body.request_key,
            body.model_dump(),
            dict(
                id=accepted["id"],
                fingerprint=accepted["fingerprint"],
                snapshot_fingerprint=fingerprint(snap),
            ),
        )
        return dict(validate_approval(store, c, user, accepted["id"]))


def commit_release_tx(store, c, user, a):
    validate_approval(store, c, user, a["id"], commit=True)
    row = dict(
        id=new_id("irelease"),
        project_id=a["project_id"],
        principal_id=user,
        approval_id=a["id"],
        snapshot=a["payload"]["snapshot"],
        fingerprint=fingerprint(a["payload"]["snapshot"]),
    )
    c.execute(insert(releases).values(**row))
    c.execute(update(approvals).where(approvals.c.id == a["id"]).values(consumed=True))
    validate_release(store, c, user, row)
    return row


def owned_instance(store, c, user, iid):
    meta = (
        c.execute(
            select(instances.c.source_app_id, instances.c.project_id).where(
                instances.c.id == iid, instances.c.principal_id == user
            )
        )
        .mappings()
        .first()
    )
    if not meta:
        raise DomainError("PERMISSION_DENIED")
    row = checked_recipe(store, c, user, meta["source_app_id"])
    require(row["project_id"] == meta["project_id"])
    i, r = lifecycle.instance(store, c, user, iid, None, lock=True)
    return i, r


def validate_instance_history(c, user, i, r):
    iid = i["id"]
    require(is_snapshot(r["snapshot"]))
    require(
        type(i["revision"]) is int
        and i["revision"] >= 1
        and type(i["data_version"]) is int
        and i["data_version"] >= 0
        and isinstance(i["history"], list)
        and len(i["history"]) == i["revision"]
    )
    first = i["history"][0]
    require(
        set(first) == {"revision", "release_id", "kind"}
        and type(first["revision"]) is int
        and first["revision"] == 1
        and first["kind"] == "created"
    )
    previous = first["release_id"]
    for revision, step in enumerate(i["history"][1:], 2):
        require(
            set(step) == {"revision", "release_id", "previous_release_id", "approval_id", "kind"}
            and type(step["revision"]) is int
            and step["revision"] == revision
            and step["kind"] == "switch"
            and step["previous_release_id"] == previous
        )
        a = (
            c.execute(
                select(approvals).where(
                    approvals.c.id == step["approval_id"],
                    approvals.c.principal_id == user,
                    approvals.c.project_id == i["project_id"],
                )
            )
            .mappings()
            .first()
        )
        require(a is not None)
        lifecycle.approval(c, user, a["id"], a["fingerprint"], "switch", allow_consumed=True)
        p = a["payload"]
        require(
            a["consumed"]
            and p["instance_id"] == iid
            and p["revision"] == revision - 1
            and p["from_release_id"] == previous
            and p["target_release_id"] == step["release_id"]
        )
        previous = step["release_id"]
    require(previous == i["release_id"])


def active_runs(c, user, iid):
    # Ordinary Run state is authoritative, including after cancellation or lease recovery.
    return (
        c.execute(
            select(runs.c.id, runs.c.status, runs.c.version)
            .join(app_runs, app_runs.c.input["run_id"].as_string() == runs.c.id)
            .where(
                app_runs.c.principal_id == user,
                app_runs.c.instance_id == iid,
                runs.c.status.not_in(TERMINAL),
            )
        )
        .mappings()
        .all()
    )


def switch_preflight(store, c, user, i, old, target, *, state_out=None):
    if not (is_snapshot(old["snapshot"]) or is_snapshot(target["snapshot"])):
        return None
    require(is_snapshot(old["snapshot"]) and is_snapshot(target["snapshot"]))
    validate_release(store, c, user, old)
    validate_release(store, c, user, target)
    require(
        target["project_id"] == old["project_id"] == i["project_id"]
        and target["snapshot"]["draft"] == old["snapshot"]["draft"]
        and target["snapshot"]["draft"]["id"] == i["source_app_id"]
        and target["snapshot"]["draft"]["runtime_id"] == i["runtime_id"]
        and not active_runs(c, user, i["id"])
    )
    verified_i, _ = owned_instance(store, c, user, i["id"])
    records = lifecycle.data_rows(c, i["id"], store=store, user=user)
    verify_records(store, c, user, verified_i, records)
    state = dict(
        instance=dict(i),
        current=dict(release_id=old["id"], fingerprint=old["fingerprint"]),
        target=dict(release_id=target["id"], fingerprint=target["fingerprint"]),
        target_id=target["id"],
        target_fingerprint=target["fingerprint"],
        definition_fingerprint=old["snapshot"]["draft"]["fingerprint"],
        retained_fingerprint=fingerprint([dict(x) for x in records]),
        active_runs=[],
    )
    if state_out is not None:
        state_out.update(state)
    return fingerprint(state)


def scope_gate(store, c, rid):
    # Independent scalar indexes mean stripping a context marker cannot downgrade a use.
    ids = (
        c.execute(
            select(app_runs.c.id, app_runs.c.principal_id, app_runs.c.instance_id).where(
                app_runs.c.input["run_id"].as_string() == rid
            )
        )
        .mappings()
        .all()
    )
    hint = (
        c.execute(
            select(
                runs.c.principal_id,
                runs.c.project_id,
                runs.c.runtime_id,
                runs.c.status,
                runs.c.context["csv_full_report_instance"]["app_run_id"]
                .as_string()
                .label("app_run_id"),
            ).where(runs.c.id == rid)
        )
        .mappings()
        .first()
    )
    links = c.execute(
        select(journal.c.principal_id, journal.c.request_key).where(
            journal.c.app_id == rid, journal.c.kind.in_([JOB, JOB + "_seal"])
        )
    ).all()
    marked = c.execute(
        select(events.c.id).where(events.c.run_id == rid, events.c.kind == EVENT)
    ).first()
    if not ids and not links and not marked and (not hint or hint["app_run_id"] is None):
        return None
    require(
        len(ids) == 1
        and hint is not None
        and hint["app_run_id"] == ids[0]["id"]
        and ids[0]["principal_id"] == hint["principal_id"]
    )
    user, iid = hint["principal_id"], ids[0]["instance_id"]
    i, _ = owned_instance(store, c, user, iid)
    workflow.scope_gate(store, c, rid)
    resource_ids = set(
        c.execute(
            select(app_runs.c.input["resource_id"].as_string()).where(app_runs.c.id == ids[0]["id"])
        )
        .scalars()
        .all()
    )
    resource_ids.update(
        c.execute(
            select(journal.c.snapshot["request"]["resource_id"].as_string()).where(
                journal.c.app_id == rid,
                journal.c.principal_id == user,
                journal.c.kind.in_([JOB, JOB + "_seal"]),
            )
        )
        .scalars()
        .all()
    )
    for resource_id in resource_ids - {None}:
        for tool in ("resource.read", "data.aggregate_csv"):
            store.authorize(c, user, i["runtime_id"], i["project_id"], resource_id, tool)
    accepted = pair(c, user, rid, JOB, ids[0]["id"])
    require(accepted is not None)
    try:
        request = UseInput.model_validate(accepted["request"])
    except ValidationError as exc:
        raise DomainError("VERSION_CONFLICT", "Invalid accepted complete-report request") from exc
    binding = accepted["response"]
    require(
        set(binding)
        == {
            "namespace",
            "run_id",
            "app_run_id",
            "workflow_id",
            "definition_fingerprint",
            "instance_id",
            "release_id",
            "release_fingerprint",
            "revision",
            "data_version",
            "principal_id",
            "project_id",
            "runtime_id",
            "resource_id",
            "request_key",
            "request_fingerprint",
            "contract_fingerprint",
        }
    )
    a = c.execute(select(app_runs).where(app_runs.c.id == ids[0]["id"])).mappings().one()
    release = lifecycle.read_release(store, c, user, a["release_id"], None)
    event = (
        c.execute(select(events.c.data).where(events.c.run_id == rid, events.c.kind == EVENT))
        .scalars()
        .all()
    )
    context = c.execute(
        select(runs.c.context["csv_full_report_instance"]).where(runs.c.id == rid)
    ).scalar_one()
    contract_fp = c.execute(
        select(run_contracts.c.fingerprint).where(run_contracts.c.run_id == rid)
    ).scalar_one()
    spec = c.execute(
        select(run_contracts.c.snapshot["ordinary_csv_report"]).where(run_contracts.c.run_id == rid)
    ).scalar_one()
    require(
        fingerprint(binding) == fingerprint(a["input"]) == a["fingerprint"]
        and context == dict(app_run_id=a["id"], fingerprint=a["fingerprint"])
        and event == [binding]
        and binding["namespace"] == VERSION
        and binding["run_id"] == rid
        and binding["app_run_id"] == a["id"]
        and binding["instance_id"] == iid
        and binding["release_id"] == a["release_id"]
        and binding["release_fingerprint"] == release["fingerprint"]
        and binding["workflow_id"] == i["source_app_id"] == release["snapshot"]["draft"]["id"]
        and binding["definition_fingerprint"] == release["snapshot"]["draft"]["fingerprint"]
        and binding["principal_id"] == user
        and binding["project_id"] == hint["project_id"] == i["project_id"]
        and binding["runtime_id"] == hint["runtime_id"] == i["runtime_id"]
        and binding["request_key"] == a["request_key"]
        and binding["request_fingerprint"] == fingerprint(accepted["request"])
        and binding["contract_fingerprint"] == contract_fp
        and type(binding["revision"]) is int
        and binding["revision"] == request.expected_revision
        and type(binding["data_version"]) is int
        and binding["data_version"] >= 0
        and binding["release_fingerprint"] == request.expected_release_fingerprint
        and binding["resource_id"] == request.resource_id == spec["resource_id"]
        and request.column == spec["column"]
        and request.request_key == binding["request_key"]
    )
    original_body = workflow.UseInput(
        expected_version=1,
        expected_definition_fingerprint=binding["definition_fingerprint"],
        resource_id=request.resource_id,
        column=request.column,
        request_key="instance-" + fingerprint([iid, request.request_key])[:64],
        consent=request.consent,
    )
    original = (
        c.execute(
            select(
                csv_report_workflow_uses.c.request_key,
                csv_report_workflow_uses.c.request_fingerprint,
            ).where(csv_report_workflow_uses.c.run_id == rid)
        )
        .mappings()
        .one()
    )
    require(
        original["request_key"] == original_body.request_key
        and original["request_fingerprint"] == fingerprint(original_body.model_dump())
    )
    revision = binding["revision"]
    require(
        1 <= revision <= len(i["history"])
        and i["history"][revision - 1]["release_id"] == binding["release_id"]
    )
    if revision > 1:
        boundary = c.execute(
            select(approvals.c.payload["data_version"]).where(
                approvals.c.id == i["history"][revision - 1]["approval_id"]
            )
        ).scalar_one()
        require(type(boundary) is int and binding["data_version"] >= boundary)
    if revision < len(i["history"]):
        boundary = c.execute(
            select(approvals.c.payload["data_version"]).where(
                approvals.c.id == i["history"][revision]["approval_id"]
            )
        ).scalar_one()
        require(type(boundary) is int and binding["data_version"] <= boundary)
    if hint["status"] not in TERMINAL:
        require(
            i["release_id"] == binding["release_id"]
            and i["revision"] == binding["revision"]
            and i["data_version"] == binding["data_version"]
        )
    return binding


def projection(store, c, user, iid, key):
    i, _ = owned_instance(store, c, user, iid)
    found = c.execute(
        select(app_runs.c.input["run_id"].as_string()).where(
            app_runs.c.instance_id == iid,
            app_runs.c.principal_id == user,
            app_runs.c.request_key == key,
        )
    ).scalar_one_or_none()
    if found is None:
        raise DomainError("RESOURCE_NOT_FOUND")
    binding = scope_gate(store, c, found)
    require(binding is not None)
    state = (
        c.execute(select(runs.c.status, runs.c.version).where(runs.c.id == found)).mappings().one()
    )
    a = c.execute(
        select(app_runs.c.result_version).where(app_runs.c.id == binding["app_run_id"])
    ).scalar_one()
    return {
        **binding,
        **dict(state),
        "result_version": a,
        "definition_version": 1,
        "model_requests": 0,
        "formal_publication_enabled": False,
    }


def use(store, user, iid, body, limits, policy):
    with store.tx() as c:
        i, r = owned_instance(store, c, user, iid)
        old = c.execute(
            select(app_runs.c.input["run_id"].as_string()).where(
                app_runs.c.instance_id == iid,
                app_runs.c.principal_id == user,
                app_runs.c.request_key == body.request_key,
            )
        ).scalar_one_or_none()
        if old:
            receipt = projection(store, c, user, iid, body.request_key)
            require(receipt["request_fingerprint"] == fingerprint(body.model_dump()))
            return receipt
        require(
            i["revision"] == body.expected_revision
            and r["fingerprint"] == body.expected_release_fingerprint
            and not active_runs(c, user, iid)
        )
        verify_records(store, c, user, i, lifecycle.data_rows(c, iid, store=store, user=user))
        aid = i["source_app_id"]
        use_body = workflow.UseInput(
            expected_version=1,
            expected_definition_fingerprint=r["snapshot"]["draft"]["fingerprint"],
            resource_id=body.resource_id,
            column=body.column,
            request_key="instance-" + fingerprint([iid, body.request_key])[:64],
            consent=body.consent,
        )
        require(
            not c.execute(
                select(csv_report_workflow_uses.c.run_id).where(
                    csv_report_workflow_uses.c.workflow_id == aid,
                    csv_report_workflow_uses.c.principal_id == user,
                    csv_report_workflow_uses.c.request_key == use_body.request_key,
                )
            ).first()
        )
        made = workflow.use_tx(store, c, user, aid, use_body, limits, policy)
        rid, app_run_id = made["run_id"], new_id("iapprun")
        binding = dict(
            namespace=VERSION,
            run_id=rid,
            app_run_id=app_run_id,
            workflow_id=aid,
            definition_fingerprint=made["definition_fingerprint"],
            instance_id=iid,
            release_id=r["id"],
            release_fingerprint=r["fingerprint"],
            revision=i["revision"],
            data_version=i["data_version"],
            principal_id=user,
            project_id=i["project_id"],
            runtime_id=i["runtime_id"],
            resource_id=body.resource_id,
            request_key=body.request_key,
            request_fingerprint=fingerprint(body.model_dump()),
            contract_fingerprint=c.execute(
                select(run_contracts.c.fingerprint).where(run_contracts.c.run_id == rid)
            ).scalar_one(),
        )
        c.execute(
            insert(app_runs).values(
                id=app_run_id,
                instance_id=iid,
                release_id=r["id"],
                principal_id=user,
                request_key=body.request_key,
                fingerprint=fingerprint(binding),
                input=binding,
                status="WAITING_APPROVAL",
                output=None,
                error=None,
                result_version=None,
            )
        )
        context = c.execute(select(runs.c.context).where(runs.c.id == rid)).scalar_one()
        c.execute(
            update(runs)
            .where(runs.c.id == rid)
            .values(
                context={
                    **context,
                    "csv_full_report_instance": dict(
                        app_run_id=app_run_id, fingerprint=fingerprint(binding)
                    ),
                }
            )
        )
        record(c, user, rid, JOB, app_run_id, body.model_dump(), binding)
        store.event(c, rid, EVENT, binding)
        return projection(store, c, user, iid, body.request_key)


def result_record(store, c, run, contract):
    from .ordinary_csv import accepted_result

    result = accepted_result(store, c, run, contract)
    require(run["status"] == "SUCCEEDED" and run["result"] == result and not run["cancel_intent"])
    spec = contract.ordinary_csv_report.model_dump()
    receipt = result["receipts"][-1]
    return dict(
        ordinary_run_id=run["id"],
        contract_fingerprint=fingerprint(contract.model_dump(exclude_none=True)),
        result_fingerprint=fingerprint(result),
        report_resource_id=receipt["data"]["resource_id"],
        report_hash=spec["report_hash"],
        source_resource_id=spec["resource_id"],
        column=spec["column"],
        count=spec["count"],
        sum=spec["sum"],
    )


def finish_tx(store, c, rid, state, error):
    binding = scope_gate(store, c, rid)
    if binding is None:
        return
    output, version = None, None
    if state == "SUCCEEDED":
        i, r = owned_instance(store, c, binding["principal_id"], binding["instance_id"])
        require(
            i["release_id"] == binding["release_id"]
            and i["revision"] == binding["revision"]
            and i["data_version"] == binding["data_version"]
        )
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        output = result_record(store, c, run, store.frozen_contract(c, run))
        version = i["data_version"] + 1
        value = dict(result=output, release_ref=r["id"])
        changed = c.execute(
            update(instances)
            .where(
                instances.c.id == i["id"],
                instances.c.release_id == binding["release_id"],
                instances.c.revision == binding["revision"],
                instances.c.data_version == binding["data_version"],
            )
            .values(data_version=version)
        ).rowcount
        require(changed == 1)
        c.execute(
            insert(data).values(
                instance_id=i["id"],
                version=version,
                run_id=binding["app_run_id"],
                release_id=r["id"],
                schema_version=1,
                data=value,
                fingerprint=fingerprint(value),
            )
        )
    c.execute(
        update(app_runs)
        .where(app_runs.c.id == binding["app_run_id"])
        .values(status=state, output=output, error=error, result_version=version)
    )


def data_scope_gate(store, c, user, iid, *, app_run_id=None):
    if store is None or user is None:
        return
    aid = c.execute(
        select(instances.c.source_app_id).where(
            instances.c.id == iid, instances.c.principal_id == user
        )
    ).scalar_one_or_none()
    if not c.execute(
        select(csv_report_workflows.c.id).where(csv_report_workflows.c.id == aid)
    ).first():
        return
    checked_recipe(store, c, user, aid)
    ids = (
        c.execute(
            select(app_runs.c.input["run_id"].as_string()).where(
                app_runs.c.instance_id == iid,
                app_runs.c.principal_id == user,
                *([] if app_run_id is None else [app_runs.c.id == app_run_id]),
            )
        )
        .scalars()
        .all()
    )
    for rid in ids:
        require(rid is not None and scope_gate(store, c, rid) is not None)


def sync_control(c, user, rid, state):
    # Stop metadata remains usable after revocation; no protected input is loaded.
    c.execute(
        update(app_runs)
        .where(
            app_runs.c.principal_id == user,
            app_runs.c.input["run_id"].as_string() == rid,
            app_runs.c.input["namespace"].as_string() == VERSION,
        )
        .values(status=state)
    )


def switch_receipt(store, c, user, iid, key, limits):
    i, _ = owned_instance(store, c, user, iid)
    entry = pair(c, user, iid, SWITCH, key)
    if entry is None:
        raise DomainError("RESOURCE_NOT_FOUND")
    response = entry["response"]
    a = lifecycle.approval(
        c, user, response["id"], response["fingerprint"], "switch", allow_consumed=True
    )
    p = a["payload"]
    lifecycle.require_switch_payload(p)
    require(
        p["instance_id"] == iid
        and p["target_release_id"] == entry["request"]["target_release_id"]
        and p["revision"] == entry["request"]["expected_revision"]
        and p["target_fingerprint"] == entry["request"]["expected_target_fingerprint"]
    )
    target = lifecycle.read_release(store, c, user, p["target_release_id"], limits)
    require(target["fingerprint"] == p["target_fingerprint"])
    if a["consumed"]:
        history = [h for h in i["history"] if h.get("approval_id") == a["id"]]
        require(
            history
            == [
                dict(
                    revision=p["revision"] + 1,
                    release_id=target["id"],
                    previous_release_id=p["from_release_id"],
                    approval_id=a["id"],
                    kind="switch",
                )
            ]
        )
        committed = dict(
            instance_id=iid,
            release_id=target["id"],
            revision=p["revision"] + 1,
            data_version=p["data_version"],
            namespace=lifecycle.NAMESPACE,
        )
    else:
        # This call uses the caller's transaction to preserve fresh authority and CAS checks.
        dependency = lifecycle.switch_preflight(store, c, user, iid, target["id"])
        records = lifecycle.data_rows(c, iid, store=store, user=user)
        require(
            i["revision"] == p["revision"]
            and i["release_id"] == p["from_release_id"]
            and i["data_version"] == p["data_version"]
            and dependency == p["logic_dependency_fingerprint"]
            and fingerprint([dict(x) for x in records]) == p["data_fingerprint"]
            and lifecycle.grant_version(c, i["project_id"], user) == p["grant_version"]
        )
        committed = None
    return {**dict(a), "committed": committed, "formal_publication_enabled": False}


def prepare_switch(store, user, iid, body, limits):
    with store.tx() as c:
        owned_instance(store, c, user, iid)
        entry = pair(c, user, iid, SWITCH, body.request_key)
        if entry:
            require(entry["request"] == body.model_dump())
        else:
            a = lifecycle.prepare_switch(
                store,
                user,
                iid,
                body.target_release_id,
                body.expected_revision,
                limits,
                expected_target_fingerprint=body.expected_target_fingerprint,
                _tx=c,
            )
            record(
                c,
                user,
                iid,
                SWITCH,
                body.request_key,
                body.model_dump(),
                dict(id=a["id"], fingerprint=a["fingerprint"]),
            )
        return switch_receipt(store, c, user, iid, body.request_key, limits)


def verify_records(store, c, user, i, records):
    require(len(records) == i["data_version"])
    for version, row in enumerate(records, 1):
        a = c.execute(select(app_runs).where(app_runs.c.id == row["run_id"])).mappings().one()
        rid = a["input"]["run_id"]
        binding = scope_gate(store, c, rid)
        run = c.execute(select(runs).where(runs.c.id == rid)).mappings().one()
        expected = result_record(store, c, run, store.frozen_contract(c, run))
        release = lifecycle.read_release(store, c, user, binding["release_id"], None)
        validate_value(release["snapshot"]["data_schema"], row["data"], "complete_report_result")
        require(
            binding["instance_id"] == i["id"]
            and row["schema_version"] == 1
            and type(row["version"]) is int
            and row["version"] == version
            and row["version"] == binding["data_version"] + 1
            and expected["contract_fingerprint"] == binding["contract_fingerprint"]
            and fingerprint(a["output"]) == fingerprint(expected)
            and fingerprint(row["data"])
            == fingerprint(dict(result=expected, release_ref=binding["release_id"]))
        )
        if binding["revision"] < len(i["history"]):
            upper = c.execute(
                select(approvals.c.payload["data_version"]).where(
                    approvals.c.id == i["history"][binding["revision"]]["approval_id"]
                )
            ).scalar_one()
            require(row["version"] <= upper)


def delivery(store, user, aid, limits):
    with store.tx() as c:
        row = checked_recipe(store, c, user, aid)
        release_ids = (
            c.execute(
                select(releases.c.id).where(
                    releases.c.principal_id == user,
                    releases.c.project_id == row["project_id"],
                    releases.c.snapshot["draft"]["id"].as_string() == aid,
                )
            )
            .scalars()
            .all()
        )
        published = [
            dict(lifecycle.read_release(store, c, user, rid, limits)) for rid in release_ids
        ]
        instance_ids = (
            c.execute(
                select(instances.c.id).where(
                    instances.c.principal_id == user,
                    instances.c.source_app_id == aid,
                    instances.c.project_id == row["project_id"],
                )
            )
            .scalars()
            .all()
        )
        values = []
        for iid in instance_ids:
            i, r = owned_instance(store, c, user, iid)
            records = lifecycle.data_rows(c, iid, store=store, user=user)
            verify_records(store, c, user, i, records)
            keys = (
                c.execute(
                    select(app_runs.c.request_key).where(
                        app_runs.c.instance_id == iid, app_runs.c.principal_id == user
                    )
                )
                .scalars()
                .all()
            )
            values.append(
                {
                    **dict(i),
                    "release_fingerprint": r["fingerprint"],
                    "runs": [projection(store, c, user, iid, key) for key in keys],
                    "data": [dict(x) for x in records],
                }
            )
        return dict(
            namespace=VERSION,
            formal_publication_enabled=False,
            workflow_id=aid,
            definition_fingerprint=row["fingerprint"],
            releases=published,
            instances=values,
        )


def mount(app, store, limits, identity, settings):
    dependency = Depends(identity)
    root = "/api/apps/{aid}/csv-full-report-delivery"

    @app.get(root)
    def read_delivery(aid: str, user=dependency):
        return delivery(store, user, aid, limits)

    @app.post(root + "/release-approvals", status_code=201)
    def prepare(aid: str, body: ReleaseInput, user=dependency):
        return prepare_release(store, user, aid, body)

    @app.get(root + "/release-requests/{key}")
    def recover_release(aid: str, key: str, user=dependency):
        with store.tx() as c:
            checked_recipe(store, c, user, aid)
            entry = pair(c, user, aid, RELEASE, key)
            if entry is None:
                raise DomainError("RESOURCE_NOT_FOUND")
            value = dict(validate_approval(store, c, user, entry["response"]["id"]))
            rid = c.execute(
                select(releases.c.id).where(releases.c.approval_id == value["id"])
            ).scalar_one_or_none()
            return {
                **value,
                "release": dict(lifecycle.read_release(store, c, user, rid, limits))
                if rid
                else None,
            }

    @app.get(root + "/instance-requests/{rid}/{key}")
    def recover_instance(aid: str, rid: str, key: str, user=dependency):
        with store.tx() as c:
            checked_recipe(store, c, user, aid)
            iid = "iinstance_" + fingerprint(dict(user=user, release=rid, key=key))[:32]
            i, r = owned_instance(store, c, user, iid)
            require(i["source_app_id"] == aid and i["history"][0]["release_id"] == rid)
            original = lifecycle.read_release(store, c, user, rid, limits)
            # Original creation receipt survives later adoption; current pointers are explicit.
            return {
                **dict(i),
                "release_id": rid,
                "revision": 1,
                "data_version": 0,
                "history": [i["history"][0]],
                "release_fingerprint": original["fingerprint"],
                "current_release_id": r["id"],
                "current_revision": i["revision"],
            }

    @app.post("/api/internal/instances/{iid}/csv-full-report-uses", status_code=202)
    def prepare_use(iid: str, body: UseInput, user=dependency):
        return use(
            store,
            user,
            iid,
            body,
            limits,
            dict(mode=settings.mode, request_model=settings.model, limits=limits.model_dump()),
        )

    @app.get("/api/internal/instances/{iid}/csv-full-report-requests/{key}")
    def recover_use(iid: str, key: str, user=dependency):
        with store.tx() as c:
            return projection(store, c, user, iid, key)

    @app.post("/api/internal/instances/{iid}/csv-full-report-switch-approvals", status_code=201)
    def switch_prepare(iid: str, body: SwitchInput, user=dependency):
        return prepare_switch(store, user, iid, body, limits)

    @app.get("/api/internal/instances/{iid}/csv-full-report-switch-requests/{key}")
    def switch_read(iid: str, key: str, user=dependency):
        with store.tx() as c:
            return switch_receipt(store, c, user, iid, key, limits)

    @app.post("/api/internal/instances/{iid}/csv-full-report-switch-requests/{key}/commit")
    def switch_commit(iid: str, key: str, body: ApprovalInput, user=dependency):
        with store.tx() as c:
            accepted = switch_receipt(store, c, user, iid, key, limits)
            require(body.fingerprint == accepted["fingerprint"])
            if accepted["committed"] is None:
                lifecycle.commit_switch(
                    store, user, accepted["id"], body.fingerprint, limits, _tx=c
                )
            return switch_receipt(store, c, user, iid, key, limits)

"""Prospective, exact-Run human applicability declarations for single-step CSV sums."""

import time
from typing import Annotated

from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy import select

from . import app_jobs, lifecycle
from . import owner_acceptance as owner
from .contracts import validate_value
from .db import (
    csv_owner_records,
    csv_owner_seals,
    events,
    fingerprint,
    internal_app_runs,
    internal_instance_data,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    operation_intents,
    operations,
    run_contracts,
    runs,
)
from .errors import DomainError
from .extraction import exact_sum_oracle
from .tools import authorized_read

VERSION = "owner.csv-sum.v1"
CONSENT = "FREEZE_SUM_ONLY_WITHOUT_MD"
ITEMS = [
    dict(
        id="scope",
        text="本人仅判断本次固定CSV材料、所选数值列和结构化求和结果是否适用于本次用途；不包含原任务完整目标或MD报告。",
    ),
    dict(
        id="material-column",
        text="本人已核对冻结材料、内容指纹和本次所选列；不把其他材料或其他Run的结果当成本次结果。",
    ),
    dict(id="sum-count", text="本人已核对本次合计、记录数及结果版本，并逐项说明接受或拒绝的依据。"),
    dict(
        id="limits",
        text="此声明不代表通用语义验证、完整MD合同验收或正式发布；新输入和新结果需分别判断。",
    ),
]


def require(value, message="Exact prospective CSV sum review changed"):
    if not value:
        raise DomainError("VERSION_CONFLICT", message)


def supported(release):
    c = release["snapshot"]["draft"]["candidate"]
    return (
        "execution_source" not in release["snapshot"]
        and len(c["actions"]) == 1
        and c["actions"][0]["executor"]
        == dict(kind="registered_tool", ref="data.aggregate_csv", version="1")
        and c["actions"][0]["effect"] == "read"
        and c["manifest"]["validation_suite_ref"] == "receipt.readback.v1"
    )


def prospective(release, source, inp, consent, *, effective_draft=None):
    if consent != CONSENT or not supported(release):
        raise DomainError(
            "UNSUPPORTED_CAPABILITY", "Only explicit single-step CSV sum scope is supported"
        )
    draft = effective_draft if effective_draft is not None else release["snapshot"]["draft"]
    require(draft["id"] == release["snapshot"]["draft"]["id"]
        and draft["runtime_id"] == release["snapshot"]["draft"]["runtime_id"])
    require(source["hash"] == draft["candidate"]["source_hash"] and source["format"] == "csv")
    return dict(
        version=VERSION,
        consent=CONSENT,
        scope="SUM_ONLY_WITHOUT_MD",
        items=ITEMS,
        release_id=release["id"],
        release_fingerprint=release["fingerprint"],
        app_id=draft["id"],
        draft_fingerprint=draft["fingerprint"],
        resource_id=source.get("resource_id", source.get("id")),
        source_hash=source["hash"],
        input=inp,
        full_md_report_included=False,
        semantic_goal_acceptance="NOT_RUN",
        technical_semantic_status="UNKNOWN",
        formal_publication_enabled=False,
    )


def scope(store, c, user, iid, rid):
    pid = owner.natural_scope(store, c, user, iid, rid)
    # Independent scalar route anchors before any private Run, binding, result or ledger payload.
    linked = (
        c.execute(
            select(internal_app_runs.c.id, internal_app_runs.c.release_id)
            .join(
                internal_run_bindings,
                internal_run_bindings.c.app_run_id == internal_app_runs.c.id,
            )
            .where(
                internal_run_bindings.c.run_id == rid,
                internal_app_runs.c.instance_id == iid,
                internal_app_runs.c.principal_id == user,
            )
        )
        .mappings()
        .one()
    )
    header = (
        c.execute(
            select(runs.c.project_id, runs.c.runtime_id, runs.c.principal_id).where(
                runs.c.id == rid
            )
        )
        .mappings()
        .one()
    )
    instance = c.execute(
        select(internal_instances.c.runtime_id).where(internal_instances.c.id == iid)
    ).scalar_one()
    require(
        header["principal_id"] == user
        and header["project_id"] == pid
        and header["runtime_id"] == instance
    )
    accepted = (
        c.execute(
            select(
                events.c.data["instance_id"].as_string().label("iid"),
                events.c.data["app_run_id"].as_string().label("aid"),
                events.c.data["release_id"].as_string().label("rel"),
            ).where(
                events.c.run_id == rid,
                events.c.kind == "ACCEPTED",
                events.c.data["namespace"].as_string() == app_jobs.KIND,
            )
        )
        .mappings()
        .all()
    )
    require(
        len(accepted) == 1
        and accepted[0] == dict(iid=iid, aid=linked["id"], rel=linked["release_id"])
    )
    return pid


def authority(store, c, user, iid, rid):
    scope(store, c, user, iid, rid)
    from .text_continuations import job_gate

    job_gate(store, c, user, rid)
    header = (
        c.execute(
            select(runs.c.runtime_id, runs.c.project_id, runs.c.resource_refs).where(
                runs.c.id == rid, runs.c.principal_id == user
            )
        )
        .mappings()
        .one()
    )
    binding = (
        c.execute(
            select(
                internal_run_bindings.c.snapshot["release_id"].as_string().label("release"),
                internal_run_bindings.c.snapshot["csv_owner_review"]["resource_id"]
                .as_string()
                .label("resource"),
            ).where(internal_run_bindings.c.run_id == rid)
        )
        .mappings()
        .one()
    )
    frozen_resource = c.execute(
        select(run_contracts.c.snapshot["resources"][0]["resource_id"].as_string()).where(
            run_contracts.c.run_id == rid
        )
    ).scalar_one()
    release_resource = c.execute(
        select(
            internal_releases.c.snapshot["draft"]["candidate"]["manifest"]["data_bindings"][0][
                "resource_ref"
            ].as_string()
        ).where(
            internal_releases.c.id == binding["release"], internal_releases.c.principal_id == user
        )
    ).scalar_one_or_none()
    intent_resources = (
        c.execute(
            select(operation_intents.c.request["args"]["resource_id"].as_string())
            .join(operations, operations.c.id == operation_intents.c.operation_id)
            .where(operations.c.run_id == rid, operations.c.call_id == "instance_result")
        )
        .scalars()
        .all()
    )
    refs = header["resource_refs"]
    require(isinstance(refs, list) and len(refs) == 1)
    ids = refs + [frozen_resource] + intent_resources
    if binding["resource"] is not None:
        ids.append(binding["resource"])
    require(all(isinstance(resource, str) for resource in ids))
    for resource in set(ids + [release_resource]):
        for action in ("resource.read", "data.aggregate_csv"):
            store.authorize(c, user, header["runtime_id"], header["project_id"], resource, action)
    require(all(resource == refs[0] for resource in ids))
    from . import csv_goal_revisions as revision
    marker = c.execute(select(internal_run_bindings.c.snapshot[revision.MARKER]).where(
        internal_run_bindings.c.run_id == rid)).scalar()
    if marker is None:
        require(release_resource == refs[0])
    else:
        # source_gate authorized original and effective materials before these
        # projections; load_binding below reconstructs the sealed definition.
        revision.job_gate(store,c,user,rid)
        from .db import delivery_graph_requests
        effective_resources = c.execute(select(delivery_graph_requests.c.snapshot["response"][
            "effective_candidate"]["manifest"]["data_bindings"][0]["resource_ref"].as_string()).where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.app_id == marker["instance_id"],
                delivery_graph_requests.c.request_key == marker["preview_key"],
                delivery_graph_requests.c.kind.in_([revision.PREVIEW,revision.PREVIEW+"_seal"]))).scalars().all()
        require(effective_resources == [refs[0],refs[0]])


def context(store, c, user, iid, rid, limits):
    authority(store, c, user, iid, rid)
    job = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    s, a, release = app_jobs.load_binding(store, c, user, job, limits, return_release=True)
    require(
        s.get("csv_review") == CONSENT and "csv_owner_review" in s and "offline_replay" not in s,
        "This Run did not freeze the CSV sum-only scope before execution",
    )
    require(supported(release))
    i = dict(
        c.execute(select(internal_instances).where(internal_instances.c.id == iid)).mappings().one()
    )
    require(
        job["status"] == a["status"] == "SUCCEEDED"
        and job["error"] is None
        and a["error"] is None
        and not job["cancel_intent"]
        and not store.has_unknown(c, rid),
        "A complete successful CSV result is required",
    )
    require(
        i["revision"] == s["expected_revision"]
        and i["release_id"] == release["id"]
        and i["data_version"] == a["result_version"],
        "Selected result is no longer current",
    )
    require(
        not c.execute(
            select(internal_app_runs.c.id).where(
                internal_app_runs.c.instance_id == iid,
                internal_app_runs.c.status.not_in(["SUCCEEDED", "FAILED", "CANCELLED"]),
            )
        ).first(),
        "A new instance result is in progress",
    )
    draft = release["snapshot"]["draft"]
    from . import csv_goal_revisions as revision
    if revision.MARKER in s:
        effective,_,_,_ = revision.bound(store,c,user,release,limits,s)
        ref = revision.Reference.model_validate(s[revision.MARKER])
        _,value = revision.load_preview(store,c,user,ref.instance_id,ref.preview_key,limits)
        if revision.material_policy(value):
            draft = effective
    candidate = draft["candidate"]
    inp = s["input"]
    validate_value(candidate["manifest"]["input_schema"], inp)
    validate_value(candidate["manifest"]["output_schema"], a["output"], "result")
    resource = candidate["manifest"]["data_bindings"][0]["resource_ref"]
    source = authorized_read(
        store,
        c,
        user,
        s["runtime_id"],
        s["project_id"],
        "resource.read",
        dict(resource_id=resource),
    )
    expected_policy = prospective(release, source, inp, s["csv_review"],
        effective_draft=draft if draft is not release["snapshot"]["draft"] else None)
    require(fingerprint(s["csv_owner_review"]) == fingerprint(expected_policy))
    frozen = (
        c.execute(
            select(events.c.data).where(
                events.c.run_id == rid, events.c.kind == "CSV_REVIEW_FROZEN"
            )
        )
        .scalars()
        .all()
    )
    require(
        frozen
        == [
            dict(
                instance_id=iid,
                app_run_id=a["id"],
                release_id=release["id"],
                binding_fingerprint=fingerprint(s),
                policy_fingerprint=fingerprint(expected_policy),
            )
        ]
    )
    args = dict(resource_id=resource, **inp)
    output = authorized_read(
        store, c, user, s["runtime_id"], s["project_id"], "data.aggregate_csv", args
    )
    require(fingerprint(output) == fingerprint(a["output"]))
    exact_sum_oracle(source["content"], inp["column"], output)
    records = [
        dict(r)
        for r in c.execute(
            select(internal_instance_data).where(
                internal_instance_data.c.instance_id == iid,
                internal_instance_data.c.run_id == a["id"],
            )
        ).mappings()
    ]
    ops = [
        dict(r) for r in c.execute(select(operations).where(operations.c.run_id == rid)).mappings()
    ]
    require(len(records) == len(ops) == 1)
    record, op = records[0], ops[0]
    intent = dict(tool="data.aggregate_csv", args=args)
    actual_intent = c.execute(
        select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])
    ).scalar()
    receipt = dict(
        operation_id=op["id"],
        status="VERIFIED",
        app_run_id=a["id"],
        instance_id=iid,
        release_id=release["id"],
        result_version=record["version"],
        output_fingerprint=fingerprint(output),
        data=output,
        artifact_refs=[],
        check_results=[dict(check="csv.exact_integer_sum.v1", status="PASS")],
    )
    require(
        op["call_id"] == "instance_result"
        and op["status"] == "VERIFIED"
        and op["tool_ref"] == "data.aggregate_csv"
        and fingerprint(actual_intent) == fingerprint(intent)
        and op["fingerprint"] == fingerprint(intent)
        and fingerprint(op["receipt"]) == fingerprint(receipt)
        and fingerprint(job["result"])
        == fingerprint(
            dict(
                app_run_id=a["id"],
                instance_id=iid,
                release_id=release["id"],
                result_version=record["version"],
                receipt_ref=op["id"],
            )
        )
        and record["release_id"] == release["id"]
        and record["schema_version"] == release["snapshot"]["data_schema_version"]
        and record["version"] == a["result_version"]
        and fingerprint(record["data"])
        == fingerprint(
            dict(
                result=output,
                **(
                    {"release_ref": release["id"]}
                    if "release_ref" in release["snapshot"]["data_schema"]["properties"]
                    else {}
                ),
            )
        )
        and record["fingerprint"] == fingerprint(record["data"])
    )
    contract = store.frozen_contract(c, job)
    return dict(
        version=VERSION,
        principal_id=user,
        project_id=i["project_id"],
        instance_id=iid,
        app_id=i["source_app_id"],
        run_id=rid,
        app_run_id=a["id"],
        run_version=job["version"],
        instance_revision=i["revision"],
        release_id=release["id"],
        release_fingerprint=release["fingerprint"],
        draft_fingerprint=draft["fingerprint"],
        binding_fingerprint=fingerprint(s),
        contract_fingerprint=fingerprint(contract.model_dump()),
        prospective=expected_policy,
        items=expected_policy["items"],
        material=dict(resource_id=resource, source_hash=source["hash"], content=source["content"]),
        input=inp,
        output=output,
        output_fingerprint=fingerprint(output),
        typed_fingerprint=record["fingerprint"],
        result_version=a["result_version"],
        actual_operations=ops,
        grant_version=lifecycle.grant_version(c, i["project_id"], user),
        technical_status="SUCCEEDED",
        independent_sum_check="PASS",
        semantic_goal_acceptance="NOT_RUN",
        technical_semantic_status="UNKNOWN",
        full_md_report_included=False,
        formal_publication_enabled=False,
    )


def ledger(c, user, iid, rid):
    return owner.run_ledger(c, user, rid, csv_owner_records, csv_owner_seals, dict(instance_id=iid))


def payload(c, row):
    return owner.run_payload(c, row, csv_owner_records)


def final_gate(store, c, user, iid, rid, limits, fresh, *, expires_at=None):
    require(
        fingerprint(context(store, c, user, iid, rid, limits)) == fingerprint(fresh),
        "Review changed before commit",
    )
    require(expires_at is None or time.time() < expires_at, "Review expired before commit")


def submit(store, user, iid, rid, limits, body):
    return owner.scoped_run_submit(
        store,
        user,
        rid,
        body,
        dict(
            namespace="csv-owner-submission-rejection.v1",
            scope_metadata=dict(instance_id=iid),
            scope=lambda c: scope(store, c, user, iid, rid),
            ledger=lambda c: ledger(c, user, iid, rid),
            payload=payload,
            context=lambda c: context(store, c, user, iid, rid, limits),
            append=lambda c, pid, rows, body, status, **kw: owner.run_append(
                c,
                user,
                pid,
                rid,
                rows,
                body,
                status,
                records=csv_owner_records,
                seals=csv_owner_seals,
                scope_metadata=dict(instance_id=iid),
                **kw,
            ),
            final_gate=lambda c, fresh, **kw: final_gate(
                store, c, user, iid, rid, limits, fresh, **kw
            ),
        ),
    )


def read(store, user, iid, rid, limits, key=None):
    with store.tx() as c:
        pid = scope(store, c, user, iid, rid)
        rows = ledger(c, user, iid, rid)
        last = rows[-1] if rows else None
        app = c.execute(
            select(internal_instances.c.source_app_id).where(internal_instances.c.id == iid)
        ).scalar_one()
        out = dict(
            version=VERSION,
            principal_id=user,
            project_id=pid,
            instance_id=iid,
            app_id=app,
            run_id=rid,
            sequence=len(rows),
            history=rows,
            latest=last,
            owner_acceptance=last["status"] if last else "PENDING",
            content_access=False,
            full_md_report_included=False,
            semantic_goal_acceptance="NOT_RUN",
            technical_semantic_status="UNKNOWN",
            formal_publication_enabled=False,
        )
        recovered = next((r for r in rows if r["request_key"] == key), None) if key else None
        if key and not recovered:
            raise DomainError("OUTCOME_UNKNOWN", "Original declaration key not found")
        try:
            fresh = context(store, c, user, iid, rid, limits)
            values = {r["id"]: payload(c, r) for r in rows}
            if last and last["kind"] in {"PREPARE", "DECIDE"}:
                p = values[last["id"]]
                require(fingerprint(fresh) == fingerprint(p["contract"]))
                out["record"] = dict(last, payload=p)
                if last["kind"] == "PREPARE" and time.time() >= p["expires_at"]:
                    out["owner_acceptance"] = "EXPIRED"
            out.update(content_access=True, current=fresh)
            if recovered and fingerprint(
                values[recovered["id"]].get("contract", fresh)
            ) == fingerprint(fresh):
                recovered = dict(recovered, payload=values[recovered["id"]])
        except DomainError as error:
            out.pop("record", None)
            out["invalidation_reason"] = error.code
            if last and last["kind"] not in {"CANCEL", "REVOKE"}:
                out["owner_acceptance"] = "STALE"
        if recovered:
            out["recovered"] = recovered
        return out


def mount(app, store, limits, identity):
    dep = Depends(identity)

    @app.get("/api/internal/instances/{iid}/runs/{rid}/csv-owner-review")
    def state(iid: str, rid: str, request_key: str | None = None, user=dep):
        try:
            return JSONResponse(
                read(store, user, iid, rid, limits, request_key),
                headers={"Cache-Control": "no-store"},
            )
        except DomainError as error:
            if error.code != "OUTCOME_UNKNOWN":
                raise
            return JSONResponse(
                {"error": error.public()}, status_code=409, headers={"Cache-Control": "no-store"}
            )

    @app.post("/api/internal/instances/{iid}/runs/{rid}/csv-owner-review-requests", status_code=201)
    def command(
        iid: str,
        rid: str,
        body: Annotated[
            owner.NaturalPrepare | owner.Decide | owner.Stop, Field(discriminator="command")
        ],
        user=dep,
    ):
        return dict(
            formal_publication_enabled=False,
            record=submit(store, user, iid, rid, limits, body.model_dump()),
        )

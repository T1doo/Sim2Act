"""Explicit one-MD requirement on an ordinary Goal; reuse original tool and receipts."""

import hashlib
from typing import Literal

from sqlalchemy import select

from .contracts import OrdinaryArtifactDelivery
from .db import fingerprint, local_effects, operations, resources
from .errors import DomainError

VERSION: Literal["ordinary-goal-md.v1"] = "ordinary-goal-md.v1"
HUMAN_VERSION = "owner.ordinary-goal-md.v2"


def delivery_policy():
    from .tools import definitions

    return OrdinaryArtifactDelivery(
        version=VERSION,
        required=True,
        format="md",
        destination="current-project",
        max_artifacts=1,
        max_text_characters=8000,
        tool_ref="artifact.save_text",
        tool_version="1",
        tool_definitions_fingerprint=fingerprint(definitions()),
        acceptance_check="核对本Run唯一MD成果的完整内容、来源、未决项及精确版本；文件回读不证明语义正确",
    ).model_dump()


def require(value, message):
    if not value:
        raise DomainError("VERIFICATION_FAILED", message)


def validate_contract(contract, *, raw=None):
    selected = contract.artifact_delivery
    if selected is None:
        if contract.human_review and contract.human_review.version == HUMAN_VERSION:
            raise DomainError("VERSION_CONFLICT", "Required MD policy was removed")
        return
    if (
        fingerprint(selected.model_dump()) != fingerprint(delivery_policy())
        or (raw is not None and fingerprint(raw) != fingerprint(delivery_policy()))
        or contract.source_goal_card is None
        or contract.human_review is None
        or contract.human_review.version != HUMAN_VERSION
        or any(
            getattr(contract, k) is not None
            for k in ("natural_planning", "application_generation", "ordinary_csv_report")
        )
    ):
        raise DomainError("VERSION_CONFLICT", "Frozen MD delivery/tool policy differs")


def check_pending(pending):
    saves = [call["id"] for call in pending if call["function"]["name"] == "artifact.save_text"]
    require(
        len(saves) <= 1,
        "One MD required; multiple save calls in one response rejected before dispatch",
    )


def dispatch_gate(store, c, run, name):
    contract = store.frozen_contract(c, run)
    validate_contract(contract)
    require(
        name in {"resource.read", "data.aggregate_csv", "artifact.save_text"},
        "Unsupported MD task action",
    )
    if name == "artifact.save_text":
        require(
            not c.execute(
                select(operations.c.id).where(
                    operations.c.run_id == run["id"], operations.c.tool_ref == name
                )
            ).first(),
            "This Run already has its one MD save operation",
        )


def artifacts(store, c, run, contract, *, required):
    validate_contract(contract)
    store.authorize_receipts(c, run)
    rows = [
        dict(r)
        for r in c.execute(
            select(operations).where(
                operations.c.run_id == run["id"], operations.c.tool_ref == "artifact.save_text"
            )
        ).mappings()
    ]
    require(len(rows) <= 1, "Multiple MD saves violate frozen bound")
    if required:
        require(
            len(rows) == 1 and rows[0]["status"] == "VERIFIED",
            "Required MD has not been saved and verified",
        )
    result = []
    for operation in rows:
        if operation["status"] != "VERIFIED":
            continue
        # Identifiers + current permissions before any protected artifact body/readback.
        effect = (
            c.execute(select(local_effects).where(local_effects.c.operation_id == operation["id"]))
            .mappings()
            .first()
        )
        require(effect is not None, "MD effect missing")
        rid = effect["resource_id"]
        store.authorize(
            c, run["principal_id"], run["runtime_id"], run["project_id"], rid, "resource.read"
        )
        require(
            operation["receipt"].get("artifact_refs") == [rid], "Artifact effect/receipt differ"
        )
        from .tools import reconcile_readback

        status, receipt = reconcile_readback(store, c, run, operation)
        require(
            status == "VERIFIED" and receipt == operation["receipt"],
            "MD original bytes or receipt changed",
        )
        file = (
            c.execute(
                select(resources).where(
                    resources.c.id == rid, resources.c.project_id == run["project_id"]
                )
            )
            .mappings()
            .first()
        )
        require(
            file is not None
            and file["format"] == "md"
            and len(file["content"]) <= 8000
            and hashlib.sha256(file["content"].encode()).hexdigest()
            == effect["content_hash"]
            == file["hash"],
            "Exact project MD bytes/hash/format required",
        )
        result.append(dict(file))
    if required:
        require(len(result) == 1, "One verified MD required")
    return result


def report(store, c, run, contract, *, required):
    files = artifacts(store, c, run, contract, required=required)
    return dict(
        version=VERSION,
        status="DELIVERED"
        if required
        else "PENDING"
        if run["status"] not in {"PARTIAL", "SUCCEEDED", "FAILED", "CANCELLED"}
        else "INCOMPLETE",
        artifacts=files,
        receipts=[
            dict(r)
            for r in c.execute(
                select(operations.c.receipt).where(
                    operations.c.run_id == run["id"],
                    operations.c.tool_ref == "artifact.save_text",
                    operations.c.status == "VERIFIED",
                )
            ).scalars()
        ],
        automatic_goal_acceptance="NOT_RUN",
        semantic_status="UNKNOWN",
    )


def projection(store, c, run, contract):
    current = report(store, c, run, contract, required=run["status"] == "PARTIAL")
    if run["status"] == "PARTIAL":
        require(
            isinstance(run["result"], dict)
            and run["result"].get("goal_acceptance") == "NOT_RUN"
            and run["result"].get("artifact_delivery") == current,
            "Stored MD result differs from current same-Run proof",
        )
    return current

"""Completed local fixed CSV tasks, minimal proofs and conservative source retirement.

No model, F1 Run promotion, PREVIEW source or generic task/Release engine.
"""

import copy
from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select, update

from .apps import authorize_source, csv_candidate, load_draft, persist_csv_candidate
from .contracts import Limits, Strict
from .db import (
    app_drafts,
    fingerprint,
    goal_card_versions,
    local_csv_tasks,
    new_id,
    projects,
    resource_retirements,
    resources,
    runs,
    task_extractions,
)
from .errors import DomainError
from .extraction import exact_sum_oracle
from .tools import authorized_read

POLICY = "erase_source_retain_minimal_proof_require_current_grants.v1"
GOAL = "fixed_csv_exact_sum.v1"


class LocalTaskInput(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    column: str = Field(min_length=1, max_length=200)
    request_key: str = Field(min_length=1, max_length=100)
    synthetic_fixture: Literal[True]
    goal: Literal["fixed_csv_exact_sum.v1"]


class TaskExtractionInput(Strict):
    expected_proof_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    name: str = Field(min_length=1, max_length=200)
    request_key: str = Field(min_length=1, max_length=100)


class RetirementInput(Strict):
    expected_proof_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retain_minimal_proof: Literal[True]
    policy: Literal["erase_source_retain_minimal_proof_require_current_grants.v1"]


def locked_project(store, c, user, pid):
    project = store.own_project(c, user, pid)
    c.execute(select(projects.c.id).where(projects.c.id == pid).with_for_update()).one()
    return project


def task_public(row):
    # Do not disclose stored old task parameters/results through proof inspection.
    return {
        "id": row["id"],
        "namespace": "LOCAL_DECLARATIVE_TASK",
        "status": row["status"],
        "proof": row["proof"],
        "proof_fingerprint": row["proof_fingerprint"],
        "error": row["error"],
        "model_requests": 0,
    }


def complete_csv_task(store, user, pid, body):
    with store.tx() as c:
        project = locked_project(store, c, user, pid)
        rid = body["resource_id"]
        authorize_source(store, c, user, project, rid, project["runtime_id"])
        request_fp = fingerprint(body)
        old = (
            c.execute(
                select(local_csv_tasks).where(
                    local_csv_tasks.c.project_id == pid,
                    local_csv_tasks.c.principal_id == user,
                    local_csv_tasks.c.request_key == body["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["request_fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            if old["status"] == "SUCCEEDED":
                verified_task(store, c, user, old["id"])
            return task_public(old)
        tid = new_id("localtask")
        value = {"resource_id": rid, "column": body["column"]}
        output, proof, error = None, None, None
        try:
            source = authorized_read(
                store, c, user, project["runtime_id"], pid, "resource.read", {"resource_id": rid}
            )
            output = authorized_read(
                store, c, user, project["runtime_id"], pid, "data.aggregate_csv", value
            )
            exact_sum_oracle(source["content"], body["column"], output)
            proof = {
                "version": 1,
                "kind": "completed_fixed_csv_task",
                "namespace": "LOCAL_DECLARATIVE_TASK",
                "task_id": tid,
                "project_id": pid,
                "principal_id": user,
                "source_resource_id": rid,
                "source_hash": source["hash"],
                "status": "SUCCEEDED",
                "goal": GOAL,
                "input_fingerprint": fingerprint(value),
                "output_fingerprint": fingerprint(output),
                "tool": {"ref": "data.aggregate_csv", "version": "1", "effect": "read"},
                "check": {"ref": "csv.exact_integer_sum.v1", "status": "PASS"},
                "parameter_scope": {"creation": ["new_csv_resource"], "runtime": ["column"]},
                "model_requests": 0,
            }
        except DomainError as exc:
            error = exc.public()
        row = {
            "id": tid,
            "project_id": pid,
            "principal_id": user,
            "resource_id": rid,
            "request_key": body["request_key"],
            "request_fingerprint": request_fp,
            "status": "FAILED" if error else "SUCCEEDED",
            "input": value,
            "output": output,
            "error": error,
            "proof": proof,
            "proof_fingerprint": fingerprint(proof) if proof else None,
        }
        c.execute(insert(local_csv_tasks).values(**row))
        return {**task_public(row), "output": output if not error else None}


def retirement_row(c, rid):
    return (
        c.execute(select(resource_retirements).where(resource_retirements.c.resource_id == rid))
        .mappings()
        .first()
    )


def verified_task(store, c, user, tid):
    task = c.execute(select(local_csv_tasks).where(local_csv_tasks.c.id == tid)).mappings().first()
    if not task or task["principal_id"] != user:
        raise DomainError("PERMISSION_DENIED")
    project = store.own_project(c, user, task["project_id"])
    authorize_source(store, c, user, project, task["resource_id"], project["runtime_id"])
    proof = task["proof"]
    if task["status"] != "SUCCEEDED" or task["error"] is not None or not isinstance(proof, dict):
        raise DomainError("VERIFICATION_FAILED", "需要实际已完成固定任务及可信证明")
    proof_keys = {
        "version",
        "kind",
        "namespace",
        "task_id",
        "project_id",
        "principal_id",
        "source_resource_id",
        "source_hash",
        "status",
        "goal",
        "input_fingerprint",
        "output_fingerprint",
        "tool",
        "check",
        "parameter_scope",
        "model_requests",
    }
    if (
        set(proof) != proof_keys
        or fingerprint(proof) != task["proof_fingerprint"]
        or any(
            proof.get(k) != v
            for k, v in {
                "version": 1,
                "kind": "completed_fixed_csv_task",
                "namespace": "LOCAL_DECLARATIVE_TASK",
                "task_id": tid,
                "project_id": project["id"],
                "principal_id": user,
                "source_resource_id": task["resource_id"],
                "status": "SUCCEEDED",
                "goal": GOAL,
                "tool": {"ref": "data.aggregate_csv", "version": "1", "effect": "read"},
                "check": {"ref": "csv.exact_integer_sum.v1", "status": "PASS"},
                "parameter_scope": {"creation": ["new_csv_resource"], "runtime": ["column"]},
                "model_requests": 0,
            }.items()
        )
    ):
        raise DomainError("VERSION_CONFLICT", "完成任务证明不一致")
    retired = retirement_row(c, task["resource_id"])
    if retired:
        source = (
            c.execute(select(resources).where(resources.c.id == task["resource_id"]))
            .mappings()
            .one()
        )
        if (
            retired["task_id"] != tid
            or retired["proof_fingerprint"] != task["proof_fingerprint"]
            or retired["principal_id"] != user
            or retired["project_id"] != project["id"]
            or retired["source_hash"] != proof["source_hash"]
            or retired["policy"] != POLICY
            or source["content"] != ""
            or source["hash"] != retired["source_hash"]
            or source["format"] != "retired"
            or task["input"] is not None
            or task["output"] is not None
        ):
            raise DomainError("VERSION_CONFLICT", "退休策略、授权定位或擦除状态不一致")
    else:
        if (
            not isinstance(task["input"], dict)
            or fingerprint(task["input"]) != proof["input_fingerprint"]
            or not task["output"]
            or fingerprint(task["output"]) != proof["output_fingerprint"]
        ):
            raise DomainError("VERSION_CONFLICT")
        accepted_request = {
            **task["input"],
            "request_key": task["request_key"],
            "synthetic_fixture": True,
            "goal": GOAL,
        }
        if fingerprint(accepted_request) != task["request_fingerprint"]:
            raise DomainError("VERSION_CONFLICT", "完成任务输入与已接受请求不一致")
        source = authorized_read(
            store,
            c,
            user,
            project["runtime_id"],
            project["id"],
            "resource.read",
            {"resource_id": task["resource_id"]},
        )
        output = authorized_read(
            store,
            c,
            user,
            project["runtime_id"],
            project["id"],
            "data.aggregate_csv",
            task["input"],
        )
        if source["hash"] != proof["source_hash"] or output != task["output"]:
            raise DomainError("VERSION_CONFLICT")
        exact_sum_oracle(source["content"], task["input"]["column"], output)
    return task, project


def inspect_task(store, user, tid):
    with store.tx() as c:
        row = (
            c.execute(select(local_csv_tasks).where(local_csv_tasks.c.id == tid)).mappings().first()
        )
        if (
            row
            and row["principal_id"] == user
            and row["status"] == "FAILED"
            and row["proof"] is None
        ):
            project = store.own_project(c, user, row["project_id"])
            authorize_source(store, c, user, project, row["resource_id"], project["runtime_id"])
            return task_public(row)
        task, _ = verified_task(store, c, user, tid)
        return task_public(task)


def task_template(proof, rid, target_hash, aid=None, action_id=None):
    candidate = csv_candidate(
        rid,
        target_hash,
        GOAL,
        Limits(
            max_requests=1,
            max_tools=1,
            max_repairs=0,
            max_total_tokens=1,
            max_output_tokens=1,
            run_seconds=1,
        ),
    )
    if aid:
        candidate["manifest"]["app_id"] = aid
        candidate["actions"][0]["action_id"] = action_id
        candidate["manifest"]["action_bindings"][0]["action_id"] = action_id
    candidate["manifest"].update(
        origin="task_run", goal_ref=proof["task_id"], source_run_ref=proof["task_id"]
    )
    candidate["task_proof"] = {
        "proof": copy.deepcopy(proof),
        "proof_fingerprint": fingerprint(proof),
        "target_resource_id": rid,
        "target_hash": target_hash,
        "retirement_policy": POLICY,
    }
    return candidate


def extract_task(store, user, tid, body, limits):
    with store.tx() as c:
        row = (
            c.execute(select(local_csv_tasks).where(local_csv_tasks.c.id == tid)).mappings().first()
        )
        if not row:
            raise DomainError("PERMISSION_DENIED")
        locked_project(store, c, user, row["project_id"])
        task, project = verified_task(store, c, user, tid)
        if task["proof_fingerprint"] != body["expected_proof_fingerprint"]:
            raise DomainError("VERSION_CONFLICT")
        rid = body["resource_id"]
        authorize_source(store, c, user, project, rid, project["runtime_id"])
        target = authorized_read(
            store,
            c,
            user,
            project["runtime_id"],
            project["id"],
            "resource.read",
            {"resource_id": rid},
        )
        if target["format"] != "csv" or target["hash"] == task["proof"]["source_hash"]:
            raise DomainError("INVALID_INPUT", "要求同项目内容不同的新CSV")
        request_fp = fingerprint({**body, "task_id": tid, "target_hash": target["hash"]})
        old = (
            c.execute(
                select(task_extractions).where(
                    task_extractions.c.task_id == tid,
                    task_extractions.c.principal_id == user,
                    task_extractions.c.request_key == body["request_key"],
                )
            )
            .mappings()
            .first()
        )
        if old:
            if old["request_fingerprint"] != request_fp:
                raise DomainError("VERSION_CONFLICT")
            load_draft(store, c, user, old["app_id"], limits)
            return {"id": old["app_id"], "state": "PREVIEW_ONLY", "publishable": False}
        if retirement_row(c, task["resource_id"]):
            raise DomainError("RESOURCE_UNAVAILABLE", "仅允许退休前核查并提取，不新增退休后候选")
        candidate = task_template(task["proof"], rid, target["hash"])
        result = persist_csv_candidate(c, project, body["name"], rid, candidate, limits)
        c.execute(
            insert(task_extractions).values(
                task_id=tid,
                principal_id=user,
                request_key=body["request_key"],
                request_fingerprint=request_fp,
                app_id=result["id"],
                snapshot=candidate["task_proof"],
            )
        )
        return result


def validate_task_candidate(store, c, user, draft):
    saved = (
        c.execute(select(task_extractions).where(task_extractions.c.app_id == draft["id"]))
        .mappings()
        .first()
    )
    origin = draft["candidate"]["task_proof"]
    if not saved or saved["principal_id"] != user or saved["snapshot"] != origin:
        raise DomainError("VERSION_CONFLICT", "来源证明不可删除、替换或协调改写")
    task, project = verified_task(store, c, user, saved["task_id"])
    if project["id"] != draft["project_id"]:
        raise DomainError("PERMISSION_DENIED")
    if task["proof"] != origin["proof"] or task["proof_fingerprint"] != origin["proof_fingerprint"]:
        raise DomainError("VERSION_CONFLICT")
    expected = task_template(
        task["proof"],
        origin["target_resource_id"],
        origin["target_hash"],
        draft["id"],
        draft["candidate"]["actions"][0]["action_id"],
    )
    if expected != draft["candidate"]:
        raise DomainError("VERSION_CONFLICT")


def retire_task_source(store, user, tid, body):
    with store.tx() as c:
        row = (
            c.execute(select(local_csv_tasks).where(local_csv_tasks.c.id == tid)).mappings().first()
        )
        if not row:
            raise DomainError("PERMISSION_DENIED")
        locked_project(store, c, user, row["project_id"])
        task, project = verified_task(store, c, user, tid)
        if (
            body["expected_proof_fingerprint"] != task["proof_fingerprint"]
            or body["expected_source_hash"] != task["proof"]["source_hash"]
        ):
            raise DomainError("VERSION_CONFLICT")
        old = retirement_row(c, task["resource_id"])
        if old:
            return dict(old)
        # This slice retires isolated fixture sources, never changes existing consumers.
        for run in c.execute(select(runs).where(runs.c.project_id == project["id"])).mappings():
            if task["resource_id"] in run["resource_refs"]:
                raise DomainError("VERSION_CONFLICT", "来源已用于F1任务，不在本轮退休范围")
        for draft in c.execute(
            select(app_drafts).where(app_drafts.c.project_id == project["id"])
        ).mappings():
            if any(
                x.get("resource_ref") == task["resource_id"]
                for x in draft["candidate"]["manifest"]["data_bindings"]
            ):
                raise DomainError("VERSION_CONFLICT", "来源仍被既有应用使用")
        for version in c.execute(select(goal_card_versions.c.snapshot)).scalars():
            if any(
                x.get("resource_id") == task["resource_id"] for x in version["resource_snapshots"]
            ):
                raise DomainError("VERSION_CONFLICT", "来源仍被目标卡引用")
        other_tasks = (
            c.execute(
                select(local_csv_tasks.c.id).where(
                    local_csv_tasks.c.resource_id == task["resource_id"],
                    local_csv_tasks.c.id != tid,
                )
            )
            .scalars()
            .all()
        )
        if (
            other_tasks
            and c.execute(
                select(task_extractions.c.app_id).where(task_extractions.c.task_id.in_(other_tasks))
            ).first()
        ):
            raise DomainError("VERSION_CONFLICT", "来源还有其他完成任务候选")
        retirement = {
            "resource_id": task["resource_id"],
            "project_id": project["id"],
            "principal_id": user,
            "task_id": tid,
            "proof_fingerprint": task["proof_fingerprint"],
            "source_hash": task["proof"]["source_hash"],
            "policy": POLICY,
        }
        c.execute(insert(resource_retirements).values(**retirement))
        c.execute(
            update(resources)
            .where(resources.c.id == task["resource_id"])
            .values(content="", format="retired")
        )
        # No old cells, parameter values or cached answers remain in this task namespace.
        c.execute(
            update(local_csv_tasks)
            .where(local_csv_tasks.c.resource_id == task["resource_id"])
            .values(input=None, output=None)
        )
        return retirement

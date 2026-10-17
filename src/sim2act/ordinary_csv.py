"""Explicit prospective CSV→complete MD contract on the original Run/tool gateway.

No language interpretation, model, new executor, Grant policy or fixed-goal checker.
"""

import hashlib
import json
import threading
import time

from pydantic import Field
from sqlalchemy import select, update

from .contracts import Strict
from .db import (
    attempts,
    events,
    fingerprint,
    local_effects,
    operation_intents,
    operations,
    reservations,
    resources,
    run_contracts,
    runs,
)
from .errors import DomainError

VERSION = "ordinary-csv-report.v1"
GOAL = "按事前确认的CSV列精确汇总，核对记录数，保存并回读完整MD报告。"
RULES = [
    "CSV至多32768字节，UTF-8无BOM；唯一非空表头；严格等宽；忽略空行；至多1000条记录。",
    "所选列每格须为有限十进制；系数至多1000位，指数绝对值至多1000；精确相加，不四舍五入。",
    "完整MD至多8000字符，保存参数JSON至多32768字节；包含来源ID、版本/hash、列、记录数、精确合计及规则；按原文保存并在同一Run核对回读。",
    "仅此结构化目标验收；通用语义NOT_RUN，人工PENDING，正式发布关闭；0模型请求。",
]
TOOLS = {"resource.read": "1", "data.aggregate_csv": "1", "artifact.save_text": "1"}


class PrepareInput(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    column: str = Field(min_length=1, max_length=32768)
    request_key: str = Field(min_length=1, max_length=100)


class ConfirmInput(Strict):
    version: int = Field(ge=1)
    contract_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def report_text(spec):
    return (
        "# CSV 精确汇总报告\n\n"
        f"来源：{spec['resource_id']}\n版本：1\nSHA-256：{spec['source_hash']}\n"
        f"列：{json.dumps(spec['column'], ensure_ascii=False)}\n记录数：{spec['count']}\n"
        f"精确合计：{spec['sum']}\n\n" + "\n".join(RULES) + "\n"
    )


def prepare(store, user, project, body, policy):
    with store.tx() as c:
        return prepare_tx(store, c, user, project, body, policy)


def prepare_tx(store, c, user, project, body, policy):
    """Shared original contract builder; callers may atomically bind saved workflows."""
    from .extraction import exact_sum_oracle
    from .tools import aggregate_csv_content, authorized_read, definitions, validate_call

    p = store.lock_project(c, user, project)
    source = authorized_read(
        store,
        c,
        user,
        p["runtime_id"],
        project,
        "resource.read",
        {"resource_id": body.resource_id},
    )
    if source["format"] != "csv" or len(source["content"].encode()) > 32768:
        raise DomainError("INVALID_INPUT", "本合同只接受至多32768字节的CSV材料")
    store.authorize(c, user, p["runtime_id"], project, body.resource_id, "data.aggregate_csv")
    store.authorize(c, user, p["runtime_id"], project, project, "artifact.save_text")
    data = aggregate_csv_content(source["content"], body.resource_id, body.column)
    exact_sum_oracle(source["content"], body.column, data)
    spec = dict(
        version=VERSION,
        checker="csv-report-independent.v1",
        resource_id=body.resource_id,
        revision=1,
        source_hash=source["hash"],
        column=body.column,
        csv_rule="utf8-no-bom-strict-unique-header-rectangular-1000.v1",
        numeric_rule="finite-decimal-exact-1000-digits-exponent.v1",
        count=data["count"],
        sum=data["sum"],
        report_format="md",
        save_rule="same-run-transactional-save-and-exact-readback.v1",
        tool_versions=TOOLS,
        tool_definitions_fingerprint=fingerprint(definitions()),
        model_requests=0,
    )
    spec["report_text"] = report_text(spec)
    spec["report_hash"] = sha(spec["report_text"])
    # Reject the full original save-tool bounds now, never truncate after confirmation.
    validate_call("artifact.save_text", {"text": spec["report_text"]})
    validate_call("data.aggregate_csv", {"resource_id": body.resource_id, "column": body.column})
    if policy["limits"]["max_tools"] < 3:
        raise DomainError("BUDGET_EXHAUSTED", "本合同需原注册工具调用额度3次")
    rid = store.submit_tx(
        c,
        user,
        project,
        GOAL,
        [body.resource_id],
        body.request_key,
        policy={**policy, "ordinary_csv_report": spec},
    )
    r = dict(c.execute(select(runs).where(runs.c.id == rid)).mappings().one())
    if "csv_report_frozen" not in r["context"]:
        saved = c.execute(
            select(run_contracts.c.fingerprint).where(run_contracts.c.run_id == rid)
        ).scalar_one()
        seal = {
            "contract_fingerprint": saved,
            "spec_fingerprint": fingerprint(spec),
            "deadline": r["created_at"] + policy["limits"]["run_seconds"],
        }
        c.execute(
            update(runs)
            .where(runs.c.id == rid)
            .values(status="WAITING_APPROVAL", context={**r["context"], "csv_report_frozen": seal})
        )
        store.event(c, rid, "CSV_REPORT_FROZEN", seal)
    return {"run_id": rid, "mode": "DETERMINISTIC", "model_requests": 0}


def event_seal(c, rid, kind, expected):
    values = (
        c.execute(select(events.c.data).where(events.c.run_id == rid, events.c.kind == kind))
        .scalars()
        .all()
    )
    if values != [expected]:
        raise DomainError("VERSION_CONFLICT", "CSV合同持久化事件与Run不一致")


def frozen(store, c, run, contract):
    spec = contract.ordinary_csv_report
    marker = run["context"].get("csv_report_frozen")
    has_event = c.execute(
        select(events.c.id).where(
            events.c.run_id == run["id"], events.c.kind == "CSV_REPORT_FROZEN"
        )
    ).first()
    if spec is None:
        if marker is not None or has_event or contract.goal.acceptance_version == VERSION:
            raise DomainError("VERSION_CONFLICT", "事前CSV合同被移除")
        return None
    raw = spec.model_dump()
    expected = {
        "contract_fingerprint": fingerprint(contract.model_dump(exclude_none=True)),
        "spec_fingerprint": fingerprint(raw),
        "deadline": run["created_at"] + contract.limits.run_seconds,
    }
    if (
        marker != expected
        or contract.goal.acceptance_version != VERSION
        or contract.goal.constraints != RULES
        or contract.goal.goal != GOAL
        or contract.goal.resource_refs != [spec.resource_id]
        or len(contract.resources) != 1
        or contract.resources[0].model_dump()
        != dict(
            resource_id=spec.resource_id, revision=1, content_hash=spec.source_hash, format="csv"
        )
        or contract.source_goal_card is not None
        or contract.natural_planning is not None
        or contract.application_generation is not None
        or spec.tool_versions != TOOLS
        or contract.limits.max_tools < 3
        or report_text(raw) != spec.report_text
        or sha(spec.report_text) != spec.report_hash
    ):
        raise DomainError("VERSION_CONFLICT", "冻结CSV合同或完整报告要求不一致")
    event_seal(c, run["id"], "CSV_REPORT_FROZEN", expected)
    source = c.execute(select(resources).where(resources.c.id == spec.resource_id)).mappings().one()
    from .extraction import exact_sum_oracle

    exact_sum_oracle(source["content"], spec.column, {"count": spec.count, "sum": spec.sum})
    if len(source["content"].encode()) > 32768:
        raise DomainError("VERIFICATION_FAILED")
    from .tools import definitions, validate_call

    if spec.tool_definitions_fingerprint != fingerprint(definitions()):
        raise DomainError("VERSION_CONFLICT", "原注册工具定义版本已改变")
    validate_call("artifact.save_text", {"text": spec.report_text})
    return raw


def active(store, c, run, contract, settings=None):
    spec = frozen(store, c, run, contract)
    if spec is None:
        raise DomainError("UNSUPPORTED_CAPABILITY", "此Run没有事前CSV合同")
    if time.time() >= run["context"]["csv_report_frozen"]["deadline"]:
        raise DomainError("BUDGET_EXHAUSTED", "事前合同已过执行有效期；请重新明确准备新任务")
    if settings is not None and (
        settings.max_tools < 3
        or time.time() >= run["created_at"] + min(settings.run_seconds, contract.limits.run_seconds)
    ):
        raise DomainError("BUDGET_EXHAUSTED", "当前Worker工具额度或执行时限已收紧，未继续执行")
    from .tools import authorized_read

    authorized_read(
        store,
        c,
        run["principal_id"],
        run["runtime_id"],
        run["project_id"],
        "resource.read",
        {"resource_id": spec["resource_id"]},
    )
    for resource, tool in [
        (spec["resource_id"], "data.aggregate_csv"),
        (run["project_id"], "artifact.save_text"),
    ]:
        store.authorize(
            c, run["principal_id"], run["runtime_id"], run["project_id"], resource, tool
        )
    return spec


def confirmation(store, c, run, contract):
    frozen(store, c, run, contract)
    value = run["context"].get("csv_report_confirmation")
    if not isinstance(value, dict) or set(value) != {
        "version",
        "contract_fingerprint",
        "request_key",
        "run_id",
        "principal_id",
        "project_id",
        "runtime_id",
    }:
        raise DomainError("PERMISSION_DENIED", "请先明确确认此Run的完整事前合同")
    try:
        body = ConfirmInput.model_validate(
            {k: value[k] for k in ("version", "contract_fingerprint", "request_key")}
        )
    except ValueError as exc:
        raise DomainError("VERSION_CONFLICT", "确认记录无效") from exc
    if (
        body.contract_fingerprint != run["context"]["csv_report_frozen"]["contract_fingerprint"]
        or value["run_id"] != run["id"]
        or value["principal_id"] != run["principal_id"]
        or value["project_id"] != run["project_id"]
        or value["runtime_id"] != run["runtime_id"]
        or body.version != 1
    ):
        raise DomainError("VERSION_CONFLICT", "确认未绑定原Run版本及合同")
    event_seal(c, run["id"], "CSV_REPORT_CONFIRMED", value)
    return value


def confirm(store, user, rid, body):
    store.require_run_owner(user, rid)
    with store.tx() as c:
        project = c.execute(
            select(runs.c.project_id).where(runs.c.id == rid, runs.c.principal_id == user)
        ).scalar_one()
        store.lock_project(c, user, project)
        from .goal_applications import source_scope_gate

        source_scope_gate(store, c, rid)
        run = dict(
            c.execute(select(runs).where(runs.c.id == rid).with_for_update()).mappings().one()
        )
        contract = store.frozen_contract(c, run)
        frozen(store, c, run, contract)
        expected = {
            **body.model_dump(),
            "run_id": rid,
            "principal_id": user,
            "project_id": run["project_id"],
            "runtime_id": run["runtime_id"],
        }
        previous = run["context"].get("csv_report_confirmation")
        if previous is not None:
            if confirmation(store, c, run, contract) != expected:
                raise DomainError("VERSION_CONFLICT", "只能读取原确认回执，不可换key或合同")
            return {
                "run_id": rid,
                "confirmed_contract": body.contract_fingerprint,
                "confirmed_version": body.version,
            }
        active(store, c, run, contract)
        if (
            run["status"] != "WAITING_APPROVAL"
            or run["version"] != body.version
            or body.version != 1
            or run["cancel_intent"]
            or body.contract_fingerprint
            != run["context"]["csv_report_frozen"]["contract_fingerprint"]
            or c.execute(select(operations.c.id).where(operations.c.run_id == rid)).first()
        ):
            raise DomainError("VERSION_CONFLICT", "Run版本或完整合同已改变，未执行")
        c.execute(
            update(runs)
            .where(runs.c.id == rid)
            .values(
                status="QUEUED",
                version=run["version"] + 1,
                context={**run["context"], "csv_report_confirmation": expected},
            )
        )
        store.event(c, rid, "CSV_REPORT_CONFIRMED", expected)
        return {
            "run_id": rid,
            "confirmed_contract": body.contract_fingerprint,
            "confirmed_version": body.version,
        }


def calls(spec):
    return [
        {
            "id": "csv_report_read_v1",
            "function": {"name": "resource.read"},
            "args": {"resource_id": spec["resource_id"]},
        },
        {
            "id": "csv_report_sum_v1",
            "function": {"name": "data.aggregate_csv"},
            "args": {"resource_id": spec["resource_id"], "column": spec["column"]},
        },
        {
            "id": "csv_report_save_v1",
            "function": {"name": "artifact.save_text"},
            "args": {"text": spec["report_text"]},
        },
    ]


def receipts(store, c, run, spec, *, complete=False, allow_unknown=False):
    """Independent read-only composite check of actual intent/effect/receipt bindings."""
    if (
        any(run["context"].get(key) != 0 for key in ("requests", "reserved_tokens", "repairs"))
        or c.execute(select(attempts.c.id).where(attempts.c.run_id == run["id"])).first()
        or c.execute(select(reservations.c.id).where(reservations.c.run_id == run["id"])).first()
    ):
        raise DomainError("VERIFICATION_FAILED", "零模型请求合同被违反")
    ops = [
        dict(op)
        for op in c.execute(select(operations).where(operations.c.run_id == run["id"])).mappings()
    ]
    by_call = {op["call_id"]: op for op in ops}
    expected_calls = calls(spec)
    if len(by_call) != len(ops) or set(by_call) - {call["id"] for call in expected_calls}:
        raise DomainError("VERIFICATION_FAILED", "存在合同外或重复工具调用")
    source = (
        c.execute(select(resources).where(resources.c.id == spec["resource_id"])).mappings().one()
    )
    result = []
    for index, call in enumerate(expected_calls):
        op = by_call.get(call["id"])
        if op is None:
            if len(ops) != index:
                raise DomainError("VERIFICATION_FAILED", "工具回执不是连续前序")
            break
        if op["status"] != "VERIFIED":
            if allow_unknown and not complete and len(ops) == index + 1:
                break
            raise DomainError("OUTCOME_UNKNOWN", "已有工具效果未核对；不自动重发")
        if not isinstance(op["receipt"], dict):
            raise DomainError("VERIFICATION_FAILED", "原工具回执缺失或类型无效")
        tool, args = call["function"]["name"], call["args"]
        intent = c.execute(
            select(operation_intents.c.request).where(operation_intents.c.operation_id == op["id"])
        ).scalar_one_or_none()
        request = {"tool": tool, "args": args}
        if op["tool_ref"] != tool or op["fingerprint"] != fingerprint(request) or intent != request:
            raise DomainError("VERIFICATION_FAILED", "工具意图不匹配冻结合同")
        effect = (
            c.execute(select(local_effects).where(local_effects.c.operation_id == op["id"]))
            .mappings()
            .first()
        )
        if index == 0:
            data = dict(
                resource_id=spec["resource_id"],
                content=source["content"],
                hash=spec["source_hash"],
                format="csv",
            )
        elif index == 1:
            data = {
                key: spec[key] for key in ("resource_id", "column", "count", "sum", "source_hash")
            }
            from .extraction import exact_sum_oracle

            exact_sum_oracle(source["content"], spec["column"], op["receipt"].get("data", {}))
        else:
            if not effect or effect["content_hash"] != spec["report_hash"]:
                raise DomainError("VERIFICATION_FAILED", "保存效果未绑定完整报告")
            store.authorize(
                c,
                run["principal_id"],
                run["runtime_id"],
                run["project_id"],
                effect["resource_id"],
                "resource.read",
            )
            from .tools import read_data

            saved = read_data(c, effect["resource_id"], "resource.read", {})
            res = (
                c.execute(select(resources).where(resources.c.id == effect["resource_id"]))
                .mappings()
                .one()
            )
            if (
                res["project_id"] != run["project_id"]
                or saved["format"] != "md"
                or saved["content"] != spec["report_text"]
                or saved["hash"] != spec["report_hash"]
            ):
                raise DomainError("VERIFICATION_FAILED", "保存的完整MD未通过逐字回读")
            data = {"resource_id": effect["resource_id"], "hash": spec["report_hash"]}
        if index != 2 and effect:
            raise DomainError("VERIFICATION_FAILED", "只读步骤存在写效果")
        expected = dict(
            operation_id=op["id"],
            status="VERIFIED",
            data=data,
            artifact_refs=[effect["resource_id"]] if index == 2 else [],
            receipt_ref=op["id"],
            check_results=[{"check": "receipt.readback.v1", "status": "PASS"}],
            usage_ref=None,
            error=None,
        )
        if fingerprint(op["receipt"]) != fingerprint(expected):
            raise DomainError("VERIFICATION_FAILED", "回执类型、内容或同Run绑定不一致")
        result.append(expected)
    if run["context"].get("tools") != len(result) or complete and len(result) != 3:
        raise DomainError("VERIFICATION_FAILED", "完整合同三步核验未完成")
    return result


def dispatch_gate(store, c, run, call, settings):
    if settings is None:
        raise DomainError("PERMISSION_DENIED", "CSV合同工具分派需当前Worker有效限额")
    contract = store.frozen_contract(c, run)
    spec = active(store, c, run, contract, settings)
    confirmation(store, c, run, contract)
    prefix = receipts(store, c, run, spec)
    expected = calls(spec)
    # A retry may read the same already VERIFIED original operation, never a new ID.
    if call not in expected or expected.index(call) > len(prefix):
        raise DomainError("PERMISSION_DENIED", "仅允许确认合同的连续三步和原调用ID")


def accepted_result(store, c, run, contract):
    spec = frozen(store, c, run, contract)
    confirmation(store, c, run, contract)
    actual = receipts(store, c, run, spec, complete=True)
    return {
        "mode": "DETERMINISTIC",
        "model_requests": 0,
        "answer": "完整MD报告已按事前合同保存并独立核对。",
        "receipts": actual,
        "goal_acceptance": "PASS_CSV_REPORT_CONTRACT",
        "task_acceptance": {
            "version": VERSION,
            "checker": spec["checker"],
            "status": "PASS",
            "scope": "EXPLICIT_CSV_REPORT_CONTRACT_ONLY",
            "whole_task_accepted": True,
            "contract_fingerprint": run["context"]["csv_report_frozen"]["contract_fingerprint"],
            "checks": [
                "source-version-hash",
                "exact-column-count-sum",
                "three-original-tool-intents-receipts",
                "same-run-md-save-effect",
                "complete-content-byte-readback",
                "zero-model-requests",
            ],
            "general_semantic_acceptance": "NOT_RUN",
            "owner_acceptance": "PENDING",
            "formal_publication_enabled": False,
        },
    }


def projection(store, c, run, contract):
    spec = frozen(store, c, run, contract)
    confirmed = run["context"].get("csv_report_confirmation") is not None
    if confirmed:
        confirmation(store, c, run, contract)
    actual = receipts(store, c, run, spec, allow_unknown=True)
    if actual and not confirmed:
        raise DomainError("VERIFICATION_FAILED", "未确认合同不能存在已执行步骤")
    if run["status"] == "SUCCEEDED" or run["result"] is not None:
        if (
            run["status"] != "SUCCEEDED"
            or run["cancel_intent"]
            or run["error"] is not None
            or run["result"] != accepted_result(store, c, run, contract)
        ):
            raise DomainError("VERIFICATION_FAILED", "事前合同最终状态与独立验收不一致")
    return {
        "confirmed": confirmed,
        "deadline": run["context"]["csv_report_frozen"]["deadline"],
        "rules": RULES,
        "receipts": actual,
        "model_requests": 0,
    }


def _process(worker, run, contract):
    from .tools import dispatch

    rid, fence = run["id"], run["fence"]
    try:
        for call in calls(contract.ordinary_csv_report.model_dump()):
            if worker.stop.is_set():
                worker.finish(rid, fence, "PAUSED")
                return
            with worker.store.tx() as c:
                current = worker.store.guard(c, rid, fence)
                if current["status"] != "RUNNING":
                    worker_state = (
                        "CANCELLED" if current["status"] == "CANCEL_REQUESTED" else "PAUSED"
                    )
                else:
                    worker_state = None
            if worker_state:
                worker.finish(rid, fence, worker_state)
                return
            dispatch(worker.store, rid, fence, call, ordinary_csv_settings=worker.s)
        with worker.store.tx() as c:
            current = worker.store.guard(c, rid, fence)
            result = accepted_result(
                worker.store, c, current, worker.store.frozen_contract(c, current)
            )
        worker.finish(rid, fence, "SUCCEEDED", result=result)
    except DomainError as exc:
        state = (
            "WAITING_RESOURCE"
            if exc.code
            in {"GRANT_REVOKED", "PERMISSION_DENIED", "RESOURCE_UNAVAILABLE", "OUTCOME_UNKNOWN"}
            else "FAILED"
        )
        try:
            worker.finish(rid, fence, state, error=exc.public())
        except DomainError:
            pass  # A stale lease cannot finalize; existing recovery owns the Run.


def process(worker, run, contract):
    # Same heartbeat lifecycle as the ordinary Worker loop; no separate executor.
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(worker.s.lease_seconds / 3):
            try:
                worker.store.heartbeat(
                    worker.id,
                    run["id"],
                    run["fence"],
                    worker.s.lease_seconds,
                    _deadline=run["created_at"]
                    + min(worker.s.run_seconds, contract.limits.run_seconds),
                    _running_only=True,
                )
            except Exception:
                stop.set()

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        _process(worker, run, contract)
    finally:
        stop.set()
        thread.join(timeout=2)

"""Frozen hypothetical conditions checker, not language understanding or Run approval."""

from typing import Literal

from fastapi import Depends
from pydantic import Field, StrictBool

from .contracts import Strict
from .db import fingerprint
from .errors import DomainError
from .tools import authorized_read

SOURCE_HASH = "ec7cf7070be884d8e27cd2e107484dbebe3885bae0434107ef76fefecdb71808"
RULE_LINES = {"R1": 3, "R2": 4, "R3": 5}
CONTRACT = {
    "id": "conditional-obligations.synthetic-a.v1",
    "version": 1,
    "source_hash": SOURCE_HASH,
    "allowed_formats": ["txt", "md"],
    "rule_lines": RULE_LINES,
    "scenario_kind": "HYPOTHETICAL_EMPLOYEE",
    "approval_threshold_exclusive": 500,
    "deadline_calendar_days_from_trip_end": 10,
    "receipt_restarts_deadline": False,
    "late_policy": "UNSPECIFIED",
    "absolute_date": "UNKNOWN",
    "scope": "human-declared finite rules; no free-text semantic or owner acceptance",
}


class Scenario(Strict):
    kind: Literal["HYPOTHETICAL_EMPLOYEE"]
    trip_ended: StrictBool | None
    amount: int | None = Field(strict=True, ge=0, le=1000000)
    receipt_present: StrictBool | None
    approved: StrictBool | None
    elapsed_days: int | None = Field(strict=True, ge=0, le=3650)


class Citation(Strict):
    line: int = Field(strict=True, ge=1, le=200)
    quote: str = Field(min_length=1, max_length=1000)


class Finding(Strict):
    rule_id: Literal["R1", "R2", "R3"]
    applies: Literal["TRUE", "FALSE", "UNKNOWN"]
    citation: Citation


class Report(Strict):
    findings: list[Finding] = Field(min_length=3, max_length=3)
    decision: Literal["ALLOW", "BLOCK", "UNKNOWN"]
    next_actions: list[
        Literal[
            "wait_trip_end",
            "obtain_receipt",
            "obtain_prior_approval",
            "clarify_facts",
            "clarify_late_policy",
            "submit_claim_and_receipt",
        ]
    ] = Field(min_length=1, max_length=6)
    deadline_days: int = Field(strict=True, ge=1, le=3650)
    absolute_date: str = Field(min_length=1, max_length=40)
    receipt_restarts_deadline: StrictBool
    explanation: str = Field(min_length=1, max_length=1000)


class CheckInput(Strict):
    resource_id: str = Field(pattern=r"^res_[a-f0-9]{32}$")
    expected_source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_contract_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    scenario: Scenario
    report: Report


def public_contract():
    return {
        "id": CONTRACT["id"],
        "version": CONTRACT["version"],
        "fingerprint": fingerprint(CONTRACT),
        "source_hash": SOURCE_HASH,
        "scenario_schema": Scenario.model_json_schema(),
        "report_schema": Report.model_json_schema(),
        "scope": CONTRACT["scope"],
        "semantic_status": "UNKNOWN",
        "owner_acceptance": "PENDING",
        "formal_publication_enabled": False,
        "real_model_requests": 0,
    }


def _conditions(s):
    def state(value):
        return "UNKNOWN" if value is None else "TRUE" if value else "FALSE"

    applies = {
        "R1": state(s.trip_ended),
        "R2": state(None if s.amount is None else s.amount > 500),
        "R3": state(None if s.receipt_present is None else not s.receipt_present),
    }
    contradictory = s.trip_ended is False and s.elapsed_days not in (None, 0)
    late = s.trip_ended is True and s.elapsed_days is not None and s.elapsed_days > 10
    unknown = (
        s.trip_ended is None
        or s.amount is None
        or s.receipt_present is None
        or (applies["R2"] == "TRUE" and s.approved is None)
        or (s.trip_ended is True and s.elapsed_days is None)
    )
    actions = []
    if s.trip_ended is False:
        actions.append("wait_trip_end")
    if s.receipt_present is False:
        actions.append("obtain_receipt")
    if applies["R2"] == "TRUE" and s.approved is False:
        actions.append("obtain_prior_approval")
    blocked = bool(actions)
    if contradictory or unknown:
        actions.append("clarify_facts")
    if late:
        actions.append("clarify_late_policy")
    decision = (
        "UNKNOWN"
        if contradictory or late
        else "BLOCK"
        if blocked
        else "UNKNOWN"
        if unknown
        else "ALLOW"
    )
    if decision == "ALLOW":
        actions.append("submit_claim_and_receipt")
    return applies, decision, actions, not contradictory


def read_source(store, user, pid, rid, expected_hash=None):
    with store.tx() as c:
        project = store.own_project(c, user, pid)
        source = authorized_read(
            store,
            c,
            user,
            project["runtime_id"],
            pid,
            "resource.read",
            {"resource_id": rid},
        )
    if source["format"] not in {"txt", "md"}:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Pinned textual rule source required")
    if source["hash"] != SOURCE_HASH or (
        expected_hash is not None and source["hash"] != expected_hash
    ):
        raise DomainError("VERSION_CONFLICT", "Source is outside the pinned rule contract")
    return source


def rule_results(s, lines):
    def state(value):
        return "UNKNOWN" if value is None else "SATISFIED" if value else "UNSATISFIED"

    r1 = ("NOT_APPLICABLE", "行程尚未结束，原10自然日期限尚未开始。")
    if s.trip_ended is None:
        r1 = ("UNKNOWN", "行程结束与否未知，不能确定期限是否开始。")
    elif s.trip_ended:
        r1 = (
            state(None if s.elapsed_days is None else s.elapsed_days <= 10),
            "结束后的自然日数未知。"
            if s.elapsed_days is None
            else (
                f"假设已结束{s.elapsed_days}个自然日，仍在10自然日期限窗口；未核查报销单和收据是否已实际提交。"
                if s.elapsed_days <= 10
                else f"假设已结束{s.elapsed_days}个自然日，期限窗口已超过；逾期政策未知，不证明当前可补报。"
            ),
        )
    r2 = ("UNKNOWN", "金额未知，不能确定超过500元的审批条件。")
    if s.amount is not None:
        r2 = (
            ("NOT_APPLICABLE", f"金额{s.amount}元，未超过500元。")
            if s.amount <= 500
            else (
                state(s.approved),
                f"金额{s.amount}元，超过500元；主管批准"
                + ("未知。" if s.approved is None else "已取得。" if s.approved else "尚未取得。"),
            )
        )
    r3 = (
        state(s.receipt_present),
        "收据状态"
        + (
            "未知。"
            if s.receipt_present is None
            else "齐全；仍沿用原期限。"
            if s.receipt_present
            else "缺失；不得提交，补齐不重启期限。"
        ),
    )
    return [
        {
            "rule_id": rid,
            "satisfaction": status,
            "reason": reason,
            "citation": {"line": RULE_LINES[rid], "quote": lines[RULE_LINES[rid] - 1]},
        }
        for rid, (status, reason) in zip(RULE_LINES, [r1, r2, r3], strict=True)
    ]


def evaluate(store, user, pid, body):
    request = CheckInput.model_validate(body)
    if request.expected_contract_fingerprint != fingerprint(CONTRACT):
        raise DomainError("VERSION_CONFLICT", "Registered check contract changed")
    source = read_source(store, user, pid, request.resource_id, request.expected_source_hash)
    return evaluate_source(request, source)


def evaluate_source(request, source):
    """Shared finite oracle after the caller's independent authorized byte read."""
    if source["hash"] != SOURCE_HASH or request.expected_contract_fingerprint != fingerprint(
        CONTRACT
    ):
        raise DomainError("VERSION_CONFLICT")
    lines = source["content"].splitlines()
    expected, decision, actions, consistent = _conditions(request.scenario)
    report = request.report
    checks = []

    def check(cid, valid):
        checks.append({"id": cid, "status": "PASS" if valid else "FAIL"})

    check("facts.consistent", consistent)
    findings: dict[str, Finding] = {f.rule_id: f for f in report.findings}
    check("rules.complete_unique", len(findings) == 3)
    for rid, number in RULE_LINES.items():
        finding = findings.get(rid)
        check(
            rid + ".source_citation",
            bool(
                finding
                and finding.citation.line == number
                and finding.citation.quote == lines[number - 1]
            ),
        )
        check(rid + ".condition", bool(finding and finding.applies == expected[rid]))
    check("decision", report.decision == decision)
    check(
        "next_actions",
        len(report.next_actions) == len(set(report.next_actions))
        and set(report.next_actions) == set(actions),
    )
    check("deadline.original_calendar_days", report.deadline_days == 10)
    check("deadline.absolute_unknown", report.absolute_date == "UNKNOWN")
    check("exception.no_deadline_restart", report.receipt_restarts_deadline is False)
    return {
        "contract_id": CONTRACT["id"],
        "contract_version": CONTRACT["version"],
        "rule_results": rule_results(request.scenario, lines),
        "decision": decision,
        "contract_fingerprint": fingerprint(CONTRACT),
        "source": {"resource_id": request.resource_id, "hash": source["hash"]},
        "input_fingerprint": fingerprint(request.scenario.model_dump()),
        "report_fingerprint": fingerprint(report.model_dump()),
        "checks": checks,
        "check_status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
        "semantic_status": "UNKNOWN",
        "owner_acceptance": "PENDING",
        "explanation_status": "NOT_CHECKED",
        "formal_publication_enabled": False,
        "real_model_requests": 0,
        "run_approval": False,
    }


def mount(app, store, identity):
    user_dependency = Depends(identity)

    @app.get("/api/projects/{pid}/conditional-checks/contract")
    def contract(pid: str, user=user_dependency):
        with store.tx() as c:
            store.own_project(c, user, pid)
        return public_contract()

    @app.get("/api/projects/{pid}/conditional-checks/sources/{rid}")
    def source(pid: str, rid: str, user=user_dependency):
        from .contracts import resource_id

        resource_id(rid)
        value = read_source(store, user, pid, rid)
        lines = value["content"].splitlines()
        return {
            "resource_id": rid,
            "hash": value["hash"],
            "contract": public_contract(),
            "rules": [
                {"rule_id": r, "line": n, "quote": lines[n - 1]} for r, n in RULE_LINES.items()
            ],
        }

    @app.post("/api/projects/{pid}/conditional-checks")
    def inspect(pid: str, body: CheckInput, user=user_dependency):
        return evaluate(store, user, pid, body.model_dump())

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


def evaluate(store, user, pid, body):
    request = CheckInput.model_validate(body)
    if request.expected_contract_fingerprint != fingerprint(CONTRACT):
        raise DomainError("VERSION_CONFLICT", "Registered check contract changed")
    with store.tx() as c:
        project = store.own_project(c, user, pid)
        source = authorized_read(
            store,
            c,
            user,
            project["runtime_id"],
            pid,
            "resource.read",
            {"resource_id": request.resource_id},
        )
    if source["format"] not in {"txt", "md"}:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Pinned textual rule source required")
    if source["hash"] != request.expected_source_hash or source["hash"] != SOURCE_HASH:
        raise DomainError("VERSION_CONFLICT", "Source is outside the pinned rule contract")
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

    @app.post("/api/projects/{pid}/conditional-checks")
    def inspect(pid: str, body: CheckInput, user=user_dependency):
        return evaluate(store, user, pid, body.model_dump())

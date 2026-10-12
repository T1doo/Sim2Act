"""Actual bounded deterministic checks for an immutable conservative PROJECT plan.

Original scope jobs remain pending: unknown semantics and omissions are not
discharged by these independent read-only checks.
"""

import csv
import io
import re
from decimal import Decimal
from fractions import Fraction
from typing import Annotated, Any, Literal

from fastapi import Depends
from pydantic import Field, field_validator, model_validator
from sqlalchemy import select

from . import delivery_graph as core
from . import delivery_graph_apps as graph
from . import report_manifest_apps as report
from .column_patches import KeyInput, read_pair, require_capacity, validate_request_key
from .conditional_runs import _current_check
from .contracts import validate_action_input, validate_value
from .db import app_drafts, fingerprint
from .db import delivery_graph_requests as requests
from .errors import DomainError
from .tools import authorized_read, csv_column_options, validate_call

KIND = "project_scope_check"
NAMESPACE = "project-deterministic-check.v1"
CONSENT = "CONFIRM_EXACT_PROJECT_DETERMINISTIC_CHECKS"
APP = r"^app_[a-f0-9]{32}$"
KEY = r"^[A-Za-z0-9_-]{1,100}$"


class SafeInput(KeyInput):
    @model_validator(mode="before")
    @classmethod
    def valid_unicode(cls, value):
        pending = [value]
        while pending:
            item = pending.pop()
            if isinstance(item, dict):
                pending.extend(item.keys())
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
            elif isinstance(item, str):
                try:
                    item.encode("utf-8")
                except UnicodeError as exc:
                    raise DomainError("INVALID_INPUT", "Valid UTF-8 confirmation required") from exc
        return value


class CSVInput(SafeInput):
    column: str = Field(min_length=1, max_length=200)


class Binding(SafeInput):
    app_id: str = Field(pattern=APP)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)


class CSVBinding(Binding):
    kind: Literal["CSV"]
    input: CSVInput


class ReportBinding(Binding):
    kind: Literal["REPORT"]
    run_id: str = Field(pattern=report.RUN)
    expected_run_version: int = Field(strict=True, ge=1)
    expected_run_fence: int = Field(strict=True, ge=0)
    expected_result_fingerprint: str = Field(pattern=graph.HASH)


class Confirmation(SafeInput):
    plan_key: str = Field(min_length=1, max_length=128)
    expected_plan_fingerprint: str = Field(pattern=graph.HASH)
    expected_options_fingerprint: str = Field(pattern=graph.HASH)
    selections: list[Annotated[CSVBinding | ReportBinding, Field(discriminator="kind")]] = Field(
        max_length=128
    )
    consent: Literal["CONFIRM_EXACT_PROJECT_DETERMINISTIC_CHECKS"]
    request_key: str = Field(pattern=KEY)

    @field_validator("plan_key", mode="before")
    @classmethod
    def safe_plan_key(cls, value):
        return validate_request_key(value)


def flags():
    return dict(
        project_revalidation_completed=False,
        semantic_status="UNKNOWN",
        owner_acceptance="PENDING",
        overall_run_acceptance="NOT_ACCEPTED",
        formal_publication_enabled=False,
        canonical_patch_executed=False,
        business_writes=0,
        model_requests=0,
    )


def members(store, c, user, pid, limits):
    """Authority/source failures must not be swallowed by expansion omissions."""
    store.lock_project(c, user, pid)
    rows = (
        c.execute(
            select(app_drafts).where(app_drafts.c.project_id == pid).order_by(app_drafts.c.id)
        )
        .mappings()
        .all()
    )
    validated: dict[str, Any] = {}
    for row in rows:
        candidate = row["candidate"]
        if (
            isinstance(candidate, dict)
            and candidate.get("namespace") == "bounded-conditional-app.v1"
        ):
            from .conditional_apps import load

            load(store, c, user, pid, row["id"])
            validated[row["id"]] = None
        else:
            validated[row["id"]] = graph.load_family(store, c, user, pid, row["id"], limits)
    return validated


def plan_context(store, c, user, pid, aid, key, limits):
    validate_request_key(key)
    validated = members(store, c, user, pid, limits)
    saved = graph.current(store, c, user, pid, aid, limits)
    row = graph.lookup(c, user, aid, "plan", key)
    if row is None:
        graph.conflict("An exact accepted PROJECT plan is required")
    body, outer = graph.checked_request(row)
    graph.validate_plan_seal(c, user, aid, key, row)
    graph.verify_outer(outer)
    if outer["receipt"]["revalidation_scope"] != "PROJECT":
        raise DomainError("UNSUPPORTED_CAPABILITY", "Existing APP checks remain separate")
    if fingerprint({k: outer[k] for k in graph.metadata(saved)}) != fingerprint(
        graph.metadata(saved)
    ):
        graph.conflict("PROJECT plan baseline changed")
    request = dict(
        project_id=pid, app_id=aid, request_key=key, changes=[v.model_dump() for v in body.changes]
    )
    fresh = core.plan_change(
        saved["graph"], body.expected_graph_fingerprint, request, saved["context"], outer["receipt"]
    )
    if fingerprint(fresh) != fingerprint(outer["receipt"]):
        graph.conflict("PROJECT impact plan changed")
    graph.verify_jobs(c, user, aid, key, outer["scope_jobs"])
    current_jobs, expansion = graph.expansion(store, c, user, pid, aid, fresh, limits, key)

    def comparable(jobs):
        return sorted(
            ({k: v for k, v in item.items() if k != "id"} for item in jobs),
            key=lambda item: item["app_id"],
        )

    if fingerprint(expansion) != fingerprint(outer["scope_expansion"]) or fingerprint(
        comparable(current_jobs)
    ) != fingerprint(comparable(outer["scope_jobs"])):
        graph.conflict("PROJECT membership, authority, locks or sources changed")
    # Only a missing trusted graph or a fully validated named wrapper is an omission.
    for item in expansion["omissions"]:
        parts = validated[item["app_id"]]
        if parts is None:
            if item["reason"] != "VERSION_CONFLICT":
                graph.conflict("Named source omission changed")
        elif item["reason"] != "GRAPH_NOT_DERIVED":
            graph.conflict("Invalid peer proof cannot be an unchecked omission")
    return outer, validated


def options_in(store, c, user, pid, aid, key, limits):
    outer, validated = plan_context(store, c, user, pid, aid, key, limits)
    applications = []
    for binding in outer["scope_expansion"]["applications"]:
        target = binding["app_id"]
        anchor = graph.current(store, c, user, pid, target, limits)
        parts = validated[target]
        if parts is None:
            graph.conflict("Noncanonical member cannot have a trusted graph")
        draft, manifest, action, *_ = parts
        item = dict(
            app_id=target,
            name=draft["name"],
            binding=binding,
            checks=[n for n in anchor["graph"]["nodes"] if n["kind"] == "CHECK"],
        )
        executor = (action.executor.kind, action.executor.ref)
        if (
            executor == ("registered_tool", "data.aggregate_csv")
            and len(manifest.workflow) == 1
            and len(draft["candidate"]["actions"]) == 1
        ):
            source = authorized_read(
                store,
                c,
                user,
                draft["runtime_id"],
                pid,
                "resource.read",
                {"resource_id": manifest.data_bindings[0].resource_ref},
            )
            item.update(
                kind="CSV",
                columns=[
                    v["name"]
                    for v in csv_column_options(source["content"])["columns"]
                    if v["numeric"]
                ],
                supported=True,
            )
            if not item["columns"]:
                item.update(supported=False, reason="NO_FINITE_NUMERIC_COLUMN_OPTIONS")
        elif executor == ("bounded_report", "intern.conditional_report"):
            runs = [
                v["run"]
                for v in report.records(store, c, user, draft, manifest)
                if v["run"]["status"] == "WAITING_APPROVAL" and v["run"]["result"]
            ]
            item.update(
                kind="REPORT",
                runs=[
                    {k: v[k] for k in ("run_id", "version", "fence", "result_fingerprint")}
                    for v in runs
                ],
                supported=bool(runs),
            )
            if not runs:
                item["reason"] = "NO_COMPLETE_ARCHIVED_RUN"
        else:
            item.update(
                kind="UNSUPPORTED", supported=False, reason="NO_REGISTERED_DETERMINISTIC_ADAPTER"
            )
        applications.append(item)
    omitted_checks = []
    for omission in outer["scope_expansion"]["omissions"]:
        parts = validated[omission["app_id"]]
        refs = (
            []
            if parts is None
            else sorted(
                {parts[1].validation_suite_ref}
                | {v.ref for v in parts[1].dependency_lock if v.kind == "check"}
                | {
                    v
                    for action in parts[0]["candidate"]["actions"]
                    for v in action["postcheck_refs"]
                }
            )
        )
        omitted_checks.append(
            dict(
                app_id=omission["app_id"],
                reason=omission["reason"],
                declaration_status="NONCANONICAL_NAMED_SOURCE"
                if parts is None
                else "TRUSTED_GRAPH_NOT_DERIVED",
                declared_checks=[
                    dict(check_ref=ref, node_id=None, status="NOT_RUN", reason=omission["reason"])
                    for ref in refs
                ],
            )
        )
    value = dict(
        namespace=NAMESPACE,
        project_id=pid,
        app_id=aid,
        plan_key=key,
        plan_fingerprint=outer["native_outer_fingerprint"],
        project_revalidation_status=outer["scope_expansion"]["status"],
        scope="PROJECT",
        applications=applications,
        omissions=outer["scope_expansion"]["omissions"],
        omitted_checks=omitted_checks,
        global_invariants=outer["receipt"]["global_invariants"],
        **flags(),
    )
    return {**value, "options_fingerprint": fingerprint(value)}, validated


@graph.controlled
def options(store, user, pid, aid, key, limits):
    with store.tx() as c:
        return options_in(store, c, user, pid, aid, key, limits)[0]


def csv_check(store, c, user, pid, parts, selection):
    draft, manifest, action, *_ = parts
    input_value = selection.input.model_dump()
    validate_value(manifest.input_schema, input_value)
    args = {"resource_id": manifest.data_bindings[0].resource_ref, **input_value}
    validate_action_input(action, args)
    validate_call(action.executor.ref, args)
    source = authorized_read(
        store,
        c,
        user,
        draft["runtime_id"],
        pid,
        "resource.read",
        {"resource_id": args["resource_id"]},
    )
    actual = authorized_read(store, c, user, draft["runtime_id"], pid, action.executor.ref, args)
    validate_value(action.output_schema, actual, "action_output")
    output = {k: actual[v.field] for k, v in manifest.outputs.items()}
    validate_value(manifest.output_schema, output, "output")
    # Independent exact arithmetic; bound exponent/digits before materializing a Fraction.
    rows = list(csv.DictReader(io.StringIO(source["content"])))
    values = [Decimal(row[input_value["column"]]) for row in rows]
    values.append(Decimal(actual["sum"]))
    bounded = all(
        v.is_finite()
        and abs(int(v.as_tuple().exponent)) <= 1000
        and len(v.as_tuple().digits) <= 2048
        for v in values
    )
    checks = [
        dict(
            id="source.readback",
            status="PASS"
            if actual["source_hash"] == source["hash"]
            and actual["resource_id"] == source["resource_id"]
            and actual["column"] == input_value["column"]
            else "FAIL",
        ),
        dict(id="count.independent", status="PASS" if actual["count"] == len(rows) else "FAIL"),
    ]
    checks.append(
        dict(
            id="sum.independent",
            status=(
                "PASS"
                if sum((Fraction(v) for v in values[:-1]), Fraction()) == Fraction(values[-1])
                else "FAIL"
            )
            if bounded
            else "NOT_RUN",
        )
    )
    status = (
        "FAIL" if any(v["status"] == "FAIL" for v in checks) else "PASS" if bounded else "NOT_RUN"
    )
    return dict(
        status=status,
        output=output,
        checks=checks,
        actual_reads=[
            dict(
                resource_id=source["resource_id"],
                source_hash=source["hash"],
                tool_ref="resource.read",
            ),
            dict(**args, source_hash=source["hash"], tool_ref=action.executor.ref),
        ],
        input=input_value,
        reason=None if bounded else "NUMERIC_PRECISION_OUTSIDE_BOUNDED_ORACLE",
    )


def execute(store, c, user, pid, aid, body, limits):
    opt, validated = options_in(store, c, user, pid, aid, body.plan_key, limits)
    if (
        opt["plan_fingerprint"] != body.expected_plan_fingerprint
        or opt["options_fingerprint"] != body.expected_options_fingerprint
    ):
        graph.conflict("Confirm the exact current PROJECT plan and inputs")
    selections = {v.app_id: v for v in body.selections}
    required = {v["app_id"] for v in opt["applications"] if v["supported"]}
    if len(selections) != len(body.selections) or set(selections) != required:
        raise DomainError("INVALID_INPUT", "Select every executable application exactly once")
    # Validate every selection before the first actual checker is executed.
    for item in opt["applications"]:
        if not item["supported"]:
            continue
        selection = selections[item["app_id"]]
        if (
            selection.kind != item["kind"]
            or selection.expected_graph_fingerprint != item["binding"]["graph_fingerprint"]
        ):
            graph.conflict("Peer graph selection changed")
        if isinstance(selection, CSVBinding):
            validate_value(
                validated[selection.app_id][1].input_schema, selection.input.model_dump()
            )
            if selection.input.column not in item["columns"]:
                raise DomainError("INVALID_INPUT", "Select a current numeric CSV column")
        else:
            selected = dict(
                run_id=selection.run_id,
                version=selection.expected_run_version,
                fence=selection.expected_run_fence,
                result_fingerprint=selection.expected_result_fingerprint,
            )
            if not any(fingerprint(v) == fingerprint(selected) for v in item["runs"]):
                graph.conflict("Confirm the exact candidate's archived Report version")
    outcomes = []
    for item in opt["applications"]:
        detail = None
        if item["supported"]:
            selection = selections[item["app_id"]]
            if isinstance(selection, CSVBinding):
                detail = csv_check(store, c, user, pid, validated[selection.app_id], selection)
                check_ref = "receipt.readback.v1"
            else:
                _, _, proof = _current_check(store, c, user, pid, selection.run_id)
                if (
                    proof["version"] != selection.expected_run_version
                    or proof["fence"] != selection.expected_run_fence
                    or proof["result_fingerprint"] != selection.expected_result_fingerprint
                ):
                    graph.conflict("Archived Report changed during checks")
                detail = dict(
                    status=proof["checks"]["check_status"],
                    archived_run=proof,
                    explanation_status="NOT_CHECKED",
                )
                check_ref = report.CHECK
        outcomes.append(
            dict(
                app_id=item["app_id"],
                binding=item["binding"],
                selection=selections[item["app_id"]].model_dump() if item["supported"] else None,
                declared_checks=[
                    dict(
                        node_id=n["id"],
                        revision=n["revision"],
                        content_fingerprint=n["content_fingerprint"],
                        check_ref=n["definition"]["check_ref"],
                        status=detail["status"]
                        if detail and n["definition"]["check_ref"] == check_ref
                        else "NOT_RUN",
                        reason=None
                        if detail and n["definition"]["check_ref"] == check_ref
                        else "NO_REGISTERED_CHECKER",
                    )
                    for n in item["checks"]
                ],
                actual=detail,
                not_run_reason=None if item["supported"] else item["reason"],
            )
        )
    latest, _ = options_in(store, c, user, pid, aid, body.plan_key, limits)
    if fingerprint(latest) != fingerprint(opt):
        graph.conflict("PROJECT changed during checks")
    statuses = [v["status"] for item in outcomes for v in item["declared_checks"]]
    executed = [item["actual"]["status"] for item in outcomes if item["actual"]]
    executed_status = (
        "FAIL"
        if "FAIL" in executed
        else "PASS"
        if executed and all(v == "PASS" for v in executed)
        else "NOT_RUN"
    )
    status = (
        "FAIL"
        if "FAIL" in statuses
        else "PARTIAL"
        if "NOT_RUN" in statuses or opt["omissions"]
        else "PASS"
    )
    value = dict(
        namespace=NAMESPACE,
        project_id=pid,
        app_id=aid,
        request_key=body.request_key,
        plan_key=body.plan_key,
        plan_fingerprint=opt["plan_fingerprint"],
        options_fingerprint=opt["options_fingerprint"],
        deterministic_status=status,
        executed_checks_status=executed_status,
        applications=outcomes,
        omissions=opt["omissions"],
        omitted_checks=opt["omitted_checks"],
        global_invariants=[
            dict(id=v, status="BLOCKED_UNKNOWN" if v == "dependency_completeness" else "PASS")
            for v in opt["global_invariants"]
        ],
        project_revalidation_status=opt["project_revalidation_status"],
        **flags(),
    )
    return {**value, "check_fingerprint": fingerprint(value)}


def load(store, c, user, pid, aid, key, limits):
    members(store, c, user, pid, limits)
    body, saved = read_pair(c, user, aid, KIND, key, Confirmation)
    if fingerprint(execute(store, c, user, pid, aid, body, limits)) != fingerprint(saved):
        graph.conflict("PROJECT check source, result or independent seal changed")
    return body, saved


@graph.controlled
def submit(store, user, pid, aid, body, limits):
    with store.tx() as c:
        value = execute(store, c, user, pid, aid, body, limits)
        if graph.lookup(c, user, aid, KIND, body.request_key):
            accepted, saved = load(store, c, user, pid, aid, body.request_key, limits)
            if fingerprint(accepted.model_dump()) != fingerprint(body.model_dump()):
                graph.conflict("PROJECT check request key changed")
            return {**saved, "cached": True}
        require_capacity(c, user, aid, KIND)
        graph.remember(c, user, aid, KIND, body.request_key, body, value)
        graph.remember(c, user, aid, KIND + "_seal", body.request_key, body, value)
        return {**value, "cached": False}


@graph.controlled
def inspect(store, user, pid, aid, key, limits):
    if not isinstance(key, str) or not re.fullmatch(KEY, key):
        raise DomainError("INVALID_INPUT", "Bounded PROJECT check key required")
    with store.tx() as c:
        return {**load(store, c, user, pid, aid, key, limits)[1], "cached": True}


@graph.controlled
def history(store, user, pid, aid, plan_key, limits):
    with store.tx() as c:
        opt, _ = options_in(store, c, user, pid, aid, plan_key, limits)
        items = []
        for row in c.execute(
            select(requests)
            .where(
                requests.c.app_id == aid, requests.c.principal_id == user, requests.c.kind == KIND
            )
            .order_by(requests.c.request_key)
        ).mappings():
            accepted, _ = read_pair(c, user, aid, KIND, row["request_key"], Confirmation)
            if accepted.plan_key == plan_key:
                items.append(load(store, c, user, pid, aid, row["request_key"], limits)[1])
        return dict(
            namespace=NAMESPACE,
            project_id=pid,
            app_id=aid,
            plan_key=plan_key,
            plan_fingerprint=opt["plan_fingerprint"],
            items=items,
            **flags(),
        )


def mount(app, store, identity, limits):
    dependency = Depends(identity)
    base = "/api/projects/{pid}/apps/{aid}/delivery-graph/scope-checks"

    @app.get(base + "/options")
    def choices(pid: str, aid: str, plan_key: str, user=dependency):
        return options(store, user, pid, aid, plan_key, limits)

    @app.post(base, status_code=201)
    def confirm(pid: str, aid: str, body: Confirmation, user=dependency):
        return submit(store, user, pid, aid, body, limits)

    @app.get(base)
    def saved(pid: str, aid: str, plan_key: str, user=dependency):
        return history(store, user, pid, aid, plan_key, limits)

    @app.get(base + "/{key}")
    def receipt(pid: str, aid: str, key: str, user=dependency):
        return inspect(store, user, pid, aid, key, limits)

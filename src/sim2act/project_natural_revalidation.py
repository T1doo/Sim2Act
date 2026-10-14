"""Closed project account for at most two existing natural-spec applications.

Independent checks use ordinary Workers. Original applications are immutable;
unknown dependency completeness is never discharged by local mechanical PASS.
"""

import copy
import sqlite3
from typing import Literal

from fastapi import Depends
from pydantic import Field
from sqlalchemy import case, func, select
from sqlalchemy.exc import OperationalError

from . import delivery_graph_apps as graph
from . import lifecycle
from . import natural_logic_patches as logic
from . import natural_specs as natural
from . import pa_spec_apps as spec
from .db import (
    app_drafts,
    delivery_graph_requests,
    fingerprint,
    internal_app_runs,
    internal_instances,
    internal_releases,
    internal_run_bindings,
    runs,
)
from .errors import DomainError
from .project_revalidation import SafeInput
from .text_logic_reuse import pair, remember

VERSION = "project-natural-check.v1"
PLAN, START, JOB, PROOF, SOURCE = (
    VERSION + "." + x for x in ("plan", "start", "job", "proof", "source")
)
CLOSE = VERSION + ".close"
CLOSE_CONSENT = "CLOSE_EXACT_UNSTARTED_PROJECT_ACCOUNT_RELEASE_OWN_RESERVATIONS"
KEY = r"^[A-Za-z0-9_-]{1,80}$"
CONSENT = "RUN_EXACT_ISOLATED_APPLICATION_CHECK_IN_FROZEN_PROJECT"


class Selection(SafeInput):
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")
    instance_id: str = Field(pattern=r"^iinstance_[a-f0-9]{32}$")
    preview_key: str | None = Field(default=None, pattern=KEY)
    expected_preview_fingerprint: str | None = Field(default=None, pattern=graph.HASH)


class Prepare(SafeInput):
    request_key: str = Field(pattern=KEY)
    expected_options_fingerprint: str = Field(pattern=graph.HASH)
    selections: list[Selection] = Field(min_length=1, max_length=2)


class Start(SafeInput):
    expected_plan_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["RUN_EXACT_ISOLATED_APPLICATION_CHECK_IN_FROZEN_PROJECT"]


class Close(SafeInput):
    expected_plan_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["CLOSE_EXACT_UNSTARTED_PROJECT_ACCOUNT_RELEASE_OWN_RESERVATIONS"]


class Reference(SafeInput):
    project_id: str = Field(pattern=r"^proj_[a-f0-9]{32}$")
    plan_key: str = Field(pattern=KEY)
    plan_fingerprint: str = Field(pattern=graph.HASH)
    app_id: str = Field(pattern=r"^app_[a-f0-9]{32}$")


class ReleasedSource(Reference):
    instance_id: str = Field(pattern=r"^iinstance_[a-f0-9]{32}$")


class Version(SafeInput):
    expected_plan_fingerprint: str = Field(pattern=graph.HASH)
    consent: Literal["CREATE_EXACT_CHECKED_INTERNAL_LOGIC_VERSION"]
    expected_check_fingerprint: str = Field(pattern=graph.HASH)


def candidate_graph(saved, candidate, limits):
    context = copy.deepcopy(saved["context"])
    for node in saved["graph"]["nodes"]:
        if node["kind"] == "ACTION":
            sid = node["key"].split(":", 1)[1]
            index = next(
                i
                for i, step in enumerate(candidate["spec_recipe"]["steps"])
                if step["step_id"] == sid
            )
            context["node_revisions"][node["key"]] = candidate["actions"][index]["revision"]
        elif node["kind"] in {"MANIFEST", "ARTIFACT", "VIEW"}:
            context["node_revisions"][node["key"]] = candidate["manifest"]["revision"]
    return graph.core.derive_manifest_graph(
        candidate["manifest"],
        candidate["actions"],
        saved["source_versions"],
        {n["key"]: n["id"] for n in saved["graph"]["nodes"]},
        context,
        limits,
        natural_candidate=candidate,
    )


def flags():
    return dict(
        namespace=VERSION,
        scope="PROJECT",
        project_revalidation_completed=False,
        dependency_completeness="BLOCKED_UNKNOWN",
        overall_run_acceptance="NOT_ACCEPTED",
        owner_acceptance="PENDING",
        semantic_status="UNKNOWN",
        formal_publication_enabled=False,
        source_application_writes=0,
    )


def members(store, c, user, pid, limits):
    store.lock_project(c, user, pid)
    rows = (
        c.execute(
            select(app_drafts).where(app_drafts.c.project_id == pid).order_by(app_drafts.c.id)
        )
        .mappings()
        .all()
    )
    result = []
    for draft in rows:
        # No filtering, downgrade of failed authority, or auto-derivation.
        family = graph.load_family(store, c, user, pid, draft["id"], limits)
        if not natural.is_candidate(draft["candidate"]):
            raise DomainError(
                "UNSUPPORTED_CAPABILITY",
                "All project members must be existing natural applications",
            )
        natural.compile_candidate(draft["candidate"], limits)
        if len(draft["candidate"]["spec_recipe"]["steps"]) != 6:
            raise DomainError(
                "UNSUPPORTED_CAPABILITY", "Existing six-step two-model applications only"
            )
        saved = graph.current(store, c, user, pid, draft["id"], limits, _family=family)
        result.append(
            dict(
                app_id=draft["id"],
                name=draft["name"],
                runtime_id=draft["runtime_id"],
                draft_fingerprint=draft["fingerprint"],
                graph=graph.metadata(saved),
                anchor_graph=saved["graph"],
                source_versions=saved["source_versions"],
            )
        )
    if not 1 <= len(result) <= 2:
        raise DomainError(
            "UNSUPPORTED_CAPABILITY",
            "The complete project must contain one or two existing natural applications",
        )
    return result


def options(store, c, user, pid, limits):
    applications = members(store, c, user, pid, limits)
    for item in applications:
        rows = (
            c.execute(
                select(
                    internal_instances.c.id,
                    internal_instances.c.release_id,
                    internal_instances.c.revision,
                    internal_instances.c.data_version,
                )
                .where(
                    internal_instances.c.project_id == pid,
                    internal_instances.c.principal_id == user,
                    internal_instances.c.source_app_id == item["app_id"],
                )
                .order_by(internal_instances.c.id)
            )
            .mappings()
            .all()
        )
        item["instances"] = [dict(r) for r in rows]
    value = dict(
        **flags(),
        project_id=pid,
        principal_id=user,
        applications=applications,
        maximum_applications=2,
        maximum_modified_applications=1,
        new_model_requests=0,
    )
    value["options_fingerprint"] = fingerprint(value)
    return value


def calculate(store, c, user, pid, body, limits, *, catalog=None, _replay=False):
    catalog = catalog or options(store, c, user, pid, limits)
    spec.require(catalog["options_fingerprint"] == body.expected_options_fingerprint)
    ids = [x.app_id for x in body.selections]
    spec.require(
        len(ids) == len(set(ids)) and sorted(ids) == [x["app_id"] for x in catalog["applications"]],
        "Exact complete project membership required",
    )
    spec.require(
        sum(x.preview_key is not None for x in body.selections) <= 1,
        "At most one explicitly modified application in this finite project account",
    )
    bindings = []
    for choice in sorted(body.selections, key=lambda x: x.app_id):
        spec.require((choice.preview_key is None) == (choice.expected_preview_fingerprint is None))
        # A CHECK result is evidence, not a new source application instance.
        owned = lifecycle.owned_instance_pointer(store, c, user, choice.instance_id, pid)
        spec.require(
            not any(x["role"] == "project_check" for x in pins(c, user, owned)),
            "Project CHECK evidence cannot become a new account source",
        )
        current_context = logic.context(
            store, c, user, choice.instance_id, limits, _allow_last=True
        )
        ctx, _, release, saved = current_context
        spec.require(ctx["project_id"] == pid and ctx["app_id"] == choice.app_id)
        candidate = saved.get("effective_candidate", release["snapshot"]["draft"]["candidate"])
        proposal = None
        if choice.preview_key is not None:
            _, proposal = logic.load_preview(
                store,
                c,
                user,
                choice.instance_id,
                choice.preview_key,
                limits,
                _prepared=current_context,
            )
            spec.require(proposal["preview_fingerprint"] == choice.expected_preview_fingerprint)
            spec.require(
                _replay
                or graph.lookup(c, user, choice.instance_id, logic.CHECK, choice.preview_key)
                is None,
                "A fresh project-isolated CHECK is required",
            )
            candidate = proposal["effective_candidate"]
        bindings.append(
            dict(
                selection=choice.model_dump(),
                context=ctx,
                effective_candidate=candidate,
                effective_fingerprint=fingerprint(candidate),
                effective_graph=saved["graph"],
                target_graph=candidate_graph(saved, candidate, limits),
                source_versions=saved["source_versions"],
                role="MODIFIED" if proposal else "REVALIDATE_UNCHANGED",
                proposal=proposal,
            )
        )
    value = dict(
        **flags(),
        project_id=pid,
        principal_id=user,
        request_key=body.request_key,
        membership=[
            {
                k: x[k]
                for k in (
                    "app_id",
                    "name",
                    "runtime_id",
                    "draft_fingerprint",
                    "graph",
                    "anchor_graph",
                    "source_versions",
                )
            }
            for x in catalog["applications"]
        ],
        applications=bindings,
        request=body.model_dump(),
        unknown_reasons=[
            dict(
                app_id=x["context"]["app_id"], reasons=x["effective_graph"]["unknown_dependencies"]
            )
            for x in bindings
        ],
        check_budget=[
            dict(
                app_id=x["context"]["app_id"],
                runtime_limits=x["effective_candidate"]["manifest"]["runtime_limits"],
                model_steps=2,
            )
            for x in bindings
        ],
    )
    value["plan_fingerprint"] = fingerprint(value)
    return value


@graph.controlled
def load_plan(store, c, user, pid, key, limits):
    """Reuse only the already complete proof within this locked transaction.

    Every non-SELECT invalidates the window. No token crosses a transaction,
    model response, callback or heartbeat; all successful logical authorities
    are rechecked even during same-window reuse (including grant expiry).
    """
    store.lock_project(c, user, pid)
    identity = (user, pid, key, fingerprint(limits.model_dump()))
    transaction = c.get_transaction()
    epoch = c.info.get("source_proof_write_epoch", 0)
    token = c.info.get("project_scope_segments", {}).get(identity)
    if (
        token
        and transaction is not None
        and token["transaction"] is transaction
        and token["epoch"] == epoch
    ):
        store.recheck_proof_authorities(c, {"_call_authorities": token["authorities"]})
        return Prepare.model_validate(copy.deepcopy(token["request"])), copy.deepcopy(token["plan"])
    with store.proof_authorities(c) as authorities:
        body, value = _load_plan(store, c, user, pid, key, limits)
    if (
        transaction is not None
        and transaction is c.get_transaction()
        and epoch == c.info.get("source_proof_write_epoch", 0)
    ):
        c.info.setdefault("project_scope_segments", {})[identity] = dict(
            transaction=transaction,
            epoch=epoch,
            authorities=tuple(sorted(authorities)),
            request=copy.deepcopy(body.model_dump()),
            plan=copy.deepcopy(value),
        )
    return body, value


def local_preview_segment(store, c, user, iid, key, limits):
    """Only an already verified selected proposal in the same project window."""
    for identity, token in c.info.get("project_scope_segments", {}).items():
        if (
            identity[0] != user
            or identity[3] != fingerprint(limits.model_dump())
            or token["transaction"] is not c.get_transaction()
            or token["epoch"] != c.info.get("source_proof_write_epoch", 0)
        ):
            continue
        for binding in token["plan"]["applications"]:
            proposal = binding["proposal"]
            if (
                proposal is None
                or binding["context"]["instance_id"] != iid
                or proposal["request_key"] != key
            ):
                continue
            store.recheck_proof_authorities(c, {"_call_authorities": token["authorities"]})
            ctx = proposal["context"]
            body = logic.Preview(
                request_key=key,
                expected_revision=ctx["instance_revision"],
                expected_release_fingerprint=ctx["release_fingerprint"],
                expected_graph_fingerprint=ctx["graph_fingerprint"],
                consume_prior_feedback="prior_items"
                in proposal["effective_candidate"]["spec_recipe"]["steps"][2]["inputs"],
            )
            return body, copy.deepcopy(proposal)
    return None


def _load_plan(store, c, user, pid, key, limits):
    current = members(store, c, user, pid, limits)
    spec.require(
        not close_present(c, user, pid, key),
        "Project account is closed; explicitly create a new key",
    )
    body, value = pair(c, user, pid, PLAN, key, Prepare)
    fp = {k: x for k, x in value.items() if k != "plan_fingerprint"}
    spec.require(
        value["plan_fingerprint"] == fingerprint(fp)
        and value["request"] == body.model_dump()
        and value["project_id"] == pid
        and value["principal_id"] == user
        and value["request_key"] == key
    )
    spec.require(
        current == value["membership"],
        "Complete project membership, graph, locks or authority changed",
    )
    spec.require(
        [x.app_id for x in sorted(body.selections, key=lambda x: x.app_id)]
        == [x["app_id"] for x in current]
    )
    fresh = calculate(
        store,
        c,
        user,
        pid,
        body,
        limits,
        catalog=dict(applications=current, options_fingerprint=body.expected_options_fingerprint),
        _replay=True,
    )
    spec.require(fresh == value, "Exact frozen project contract changed")
    for binding in value["applications"]:
        expected = ref(pid, key, value, binding["context"]["app_id"])
        accepted, seal = pair(c, user, binding["context"]["instance_id"], SOURCE, key, Reference)
        spec.require(
            accepted == expected and seal == expected.model_dump(),
            "Independent source roles changed",
        )
    return body, value


def close_present(c, user, pid, key):
    return any(graph.lookup(c, user, pid, kind, key) for kind in (CLOSE, CLOSE + "_seal"))


@graph.controlled
def plan_metadata(c, user, pid, key):
    """Only public selection identifiers and release pointers, never PLAN prose."""
    columns = [
        delivery_graph_requests.c.request_fingerprint,
        delivery_graph_requests.c.snapshot["request"].label("request"),
        delivery_graph_requests.c.snapshot["response"]["plan_fingerprint"].as_string().label("fp"),
    ]
    application_array = delivery_graph_requests.c.snapshot["response"]["applications"]
    if c.dialect.name == "sqlite":
        array_type = func.json_type(application_array)
        array_count = func.json_array_length(application_array)
    elif c.dialect.name == "postgresql":
        array_type = func.json_typeof(application_array)
        array_count = func.json_array_length(application_array)
    else:
        raise DomainError("UNSUPPORTED_CAPABILITY", "No exact historical JSON metadata contract")
    columns.extend(
        [
            array_type.label("application_type"),
            case((array_type == "array", array_count), else_=0).label("application_count"),
        ]
    )
    for field in ("project_id", "principal_id", "request_key"):
        columns.append(
            delivery_graph_requests.c.snapshot["response"][field].as_string().label(field)
        )
    for index in range(2):
        for field in ("release_id", "app_id", "instance_id", "project_id", "principal_id"):
            columns.append(
                delivery_graph_requests.c.snapshot["response"]["applications"][index]["context"][
                    field
                ]
                .as_string()
                .label(f"context{index}_{field}")
            )
    rows = (
        c.execute(
            select(*columns).where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.app_id == pid,
                delivery_graph_requests.c.kind.in_([PLAN, PLAN + "_seal"]),
                delivery_graph_requests.c.request_key == key,
            )
        )
        .mappings()
        .all()
    )
    spec.require(
        len(rows) == 2 and dict(rows[0]) == dict(rows[1]), "Independent PLAN metadata changed"
    )
    row = rows[0]
    spec.require(
        row["project_id"] == pid and row["principal_id"] == user and row["request_key"] == key
    )
    body = Prepare.model_validate(row["request"])
    spec.require(
        body.request_key == key and rows[0]["request_fingerprint"] == fingerprint(body.model_dump())
    )
    choices = sorted(body.selections, key=lambda x: x.app_id)
    spec.require(
        row["application_type"] == "array" and row["application_count"] == len(choices),
        "Exact historical application array required",
    )
    spec.require(
        len({x.app_id for x in choices}) == len(choices)
        and len({x.instance_id for x in choices}) == len(choices)
    )
    refs = [
        ReleasedSource(
            project_id=pid,
            plan_key=key,
            plan_fingerprint=rows[0]["fp"],
            app_id=x.app_id,
            instance_id=x.instance_id,
        ).model_dump()
        for x in choices
    ]
    releases = []
    for index, choice in enumerate(choices):
        spec.require(
            row[f"context{index}_app_id"] == choice.app_id
            and row[f"context{index}_instance_id"] == choice.instance_id
            and row[f"context{index}_project_id"] == pid
            and row[f"context{index}_principal_id"] == user,
            "Public PLAN context identity changed",
        )
        releases.append(row[f"context{index}_release_id"])
    if len(choices) == 1:
        spec.require(
            all(
                row[f"context1_{field}"] is None
                for field in ("release_id", "app_id", "instance_id", "project_id", "principal_id")
            )
        )
    spec.require(all(isinstance(x, str) and x.startswith("irelease_") for x in releases))
    return body, refs, releases


@graph.controlled
def close_receipt(c, user, pid, key):
    """Public reservation proof only; no private PLAN body or live source replay."""
    spec.require(
        not account_consumed(c, user, pid, key), "Closed account has contradictory consumption"
    )
    body, value = pair(c, user, pid, CLOSE, key, Close)
    refs = [ReleasedSource.model_validate(x) for x in value["released_sources"]]
    _, sources, _ = plan_metadata(c, user, pid, key)
    spec.require(value["released_sources"] == sources, "Complete closure source set changed")
    for source in refs:
        accepted, seal = pair(c, user, source.instance_id, SOURCE, key, Reference)
        expected_ref = {k: v for k, v in source.model_dump().items() if k != "instance_id"}
        spec.require(
            accepted.model_dump() == seal == expected_ref, "Independent closure source changed"
        )
    expected = dict(
        **flags(),
        project_id=pid,
        principal_id=user,
        plan_key=key,
        plan_fingerprint=body.expected_plan_fingerprint,
        account_status="CLOSED_UNSTARTED",
        check_execution_status="NOT_STARTED",
        effect_known=True,
        executed_model_requests=0,
        isolated_check_instances_created=0,
        released_sources=[x.model_dump() for x in refs],
    )
    spec.require(1 <= len(refs) <= 2 and len({x.app_id for x in refs}) == len(refs))
    spec.require(
        all(
            x.project_id == pid
            and x.plan_key == key
            and x.plan_fingerprint == body.expected_plan_fingerprint
            for x in refs
        )
    )
    expected["close_fingerprint"] = fingerprint(expected)
    spec.require(value == expected, "Exact closure receipt changed")
    return body, value


@graph.controlled
def archived_plan(store, c, user, pid, key, limits):
    # Closed history remains authorized, but never replays against new versions.
    store.lock_project(c, user, pid)
    metadata_body, sources, releases = plan_metadata(c, user, pid, key)
    for source, rid in zip(sources, releases, strict=True):
        graph.load_family(store, c, user, pid, source["app_id"], limits)
        owned = lifecycle.owned_instance_pointer(store, c, user, source["instance_id"], pid)
        spec.require(owned["source_app_id"] == source["app_id"])
        lifecycle.read_release(store, c, user, rid, limits)
    body, value = pair(c, user, pid, PLAN, key, Prepare)
    spec.require(body == metadata_body)
    spec.require(
        value["project_id"] == pid
        and value["principal_id"] == user
        and value["request_key"] == key
        and value["request"] == body.model_dump()
        and value["plan_fingerprint"]
        == fingerprint({k: v for k, v in value.items() if k != "plan_fingerprint"})
    )
    spec.require(len(value["applications"]) == len(body.selections))
    for binding, choice, rid in zip(
        value["applications"],
        sorted(body.selections, key=lambda x: x.app_id),
        releases,
        strict=True,
    ):
        ctx = binding["context"]
        spec.require(
            ctx["release_id"] == rid
            and ctx["app_id"] == choice.app_id
            and ctx["instance_id"] == choice.instance_id
            and ctx["project_id"] == pid
            and ctx["principal_id"] == user
        )
        accepted, seal = pair(c, user, choice.instance_id, SOURCE, key, Reference)
        expected = ref(pid, key, value, choice.app_id)
        spec.require(accepted == expected and seal == expected.model_dump())
    return body, value


def validate_closed_plan(plan, receipt):
    expected = [
        dict(
            **ref(
                plan["project_id"], plan["request_key"], plan, x["context"]["app_id"]
            ).model_dump(),
            instance_id=x["context"]["instance_id"],
        )
        for x in plan["applications"]
    ]
    spec.require(
        receipt["plan_fingerprint"] == plan["plan_fingerprint"]
        and receipt["released_sources"] == expected,
        "Closed account source set changed",
    )


def account_consumed(c, user, pid, key):
    # Either independent discovery index is sufficient to reject. Never infer
    # no execution from status or missing primary START alone.
    from sqlalchemy import or_

    markers = c.execute(
        select(delivery_graph_requests.c.request_key).where(
            delivery_graph_requests.c.principal_id == user,
            or_(
                (delivery_graph_requests.c.app_id == pid)
                & delivery_graph_requests.c.kind.in_(
                    [START, START + "_seal", PROOF, PROOF + "_seal"]
                )
                & or_(
                    delivery_graph_requests.c.request_key.startswith(key + ":", autoescape=True),
                    delivery_graph_requests.c.snapshot["response"]["plan_key"].as_string() == key,
                ),
                (delivery_graph_requests.c.app_id == pid)
                & delivery_graph_requests.c.kind.in_(
                    [VERSION + ".approval", VERSION + ".approval_seal"]
                )
                & (delivery_graph_requests.c.request_key == key),
                delivery_graph_requests.c.kind.in_([JOB, JOB + "_seal"])
                & (delivery_graph_requests.c.snapshot["request"]["project_id"].as_string() == pid)
                & (delivery_graph_requests.c.snapshot["request"]["plan_key"].as_string() == key),
            ),
        )
    ).first()
    bound = c.execute(
        select(internal_run_bindings.c.run_id).where(
            internal_run_bindings.c.snapshot["project_check"]["project_id"].as_string() == pid,
            internal_run_bindings.c.snapshot["project_check"]["plan_key"].as_string() == key,
        )
    ).first()
    return bool(markers or bound)


def require_unconsumed(c, user, pid, key, plan):
    spec.require(
        not account_consumed(c, user, pid, key), "Started or consumed project account cannot close"
    )
    for binding in plan["applications"]:
        iid = binding["context"]["instance_id"]
        local = c.execute(
            select(delivery_graph_requests.c.request_key).where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.app_id == iid,
                delivery_graph_requests.c.kind.in_(
                    [
                        logic.CHECK,
                        logic.CHECK + "_seal",
                        logic.APPROVAL,
                        logic.APPROVAL + "_seal",
                    ]
                ),
            )
        ).first()
        released = c.execute(
            select(internal_releases.c.id).where(
                internal_releases.c.principal_id == user,
                internal_releases.c.project_id == pid,
                internal_releases.c.snapshot["natural_logic_source"]["instance_id"].as_string()
                == iid,
            )
        ).first()
        # Accepted binding or JOB seal retains consumption if local CHECK indexes disappear.
        local_bound = c.execute(
            select(internal_run_bindings.c.run_id).where(
                internal_run_bindings.c.snapshot["logic_check"]["instance_id"].as_string() == iid,
            )
        ).first()
        local_job = c.execute(
            select(delivery_graph_requests.c.app_id).where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind.in_([logic.JOB, logic.JOB + "_seal"]),
                delivery_graph_requests.c.snapshot["response"]["instance_id"].as_string() == iid,
            )
        ).first()
        spec.require(
            not local and not released and not local_bound and not local_job,
            "Source already supplies CHECK or derived version evidence",
        )


def close_account(store, user, pid, key, body, limits):
    try:
        return _close_account(store, user, pid, key, body, limits)
    except OperationalError as exc:
        # Only a failed transaction entrance is known to have made no writes.
        # Do not retry, mask errors inside a transaction, or change its budget.
        code = getattr(exc.orig, "sqlite_errorcode", None)
        if (
            store.engine.dialect.name == "sqlite"
            and exc.statement == "BEGIN IMMEDIATE"
            and isinstance(exc.orig, sqlite3.Error)
            and isinstance(code, int)
            and code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
        ):
            raise DomainError(
                "VERSION_CONFLICT",
                "Project account is busy; read this plan with its original key "
                "to resolve any concurrent request before another write.",
            ) from exc
        raise


def _close_account(store, user, pid, key, body, limits):
    with store.tx() as c:
        store.lock_project(c, user, pid)
        if close_present(c, user, pid, key):
            _, plan = archived_plan(store, c, user, pid, key, limits)
            old, value = close_receipt(c, user, pid, key)
            spec.require(old == body)
            validate_closed_plan(plan, value)
            return value
        _, plan = load_plan(store, c, user, pid, key, limits)
        spec.require(body.expected_plan_fingerprint == plan["plan_fingerprint"])
        require_unconsumed(c, user, pid, key, plan)
        refs = [
            dict(
                **ref(pid, key, plan, x["context"]["app_id"]).model_dump(),
                instance_id=x["context"]["instance_id"],
            )
            for x in plan["applications"]
        ]
        value = dict(
            **flags(),
            project_id=pid,
            principal_id=user,
            plan_key=key,
            plan_fingerprint=plan["plan_fingerprint"],
            account_status="CLOSED_UNSTARTED",
            check_execution_status="NOT_STARTED",
            effect_known=True,
            executed_model_requests=0,
            isolated_check_instances_created=0,
            released_sources=refs,
        )
        value["close_fingerprint"] = fingerprint(value)
        remember(c, user, pid, CLOSE, key, body, value)
        return value


def ref(pid, key, plan, aid):
    return Reference(
        project_id=pid, plan_key=key, plan_fingerprint=plan["plan_fingerprint"], app_id=aid
    )


def member(plan, aid):
    found = [x for x in plan["applications"] if x["context"]["app_id"] == aid]
    spec.require(len(found) == 1)
    return found[0]


@graph.controlled
def guard(store, c, user, reference, limits):
    reference = Reference.model_validate(reference)
    _, plan = load_plan(store, c, user, reference.project_id, reference.plan_key, limits)
    spec.require(reference.plan_fingerprint == plan["plan_fingerprint"])
    return plan, member(plan, reference.app_id)


@graph.controlled
def job_gate(store, c, user, job, snapshot, limits):
    marker = graph.lookup(c, user, job["id"], JOB, "accepted")
    other = graph.lookup(c, user, job["id"], JOB + "_seal", "accepted")
    spec.require(
        bool(
            marker
            or other
            or c.execute(
                select(delivery_graph_requests.c.request_key).where(
                    delivery_graph_requests.c.principal_id == user,
                    delivery_graph_requests.c.kind.in_([START, START + "_seal"]),
                    delivery_graph_requests.c.snapshot["response"]["run_id"].as_string()
                    == job["id"],
                )
            ).first()
        )
        == ("project_check" in snapshot),
        "Project CHECK role cannot be removed",
    )
    if "project_check" not in snapshot:
        return
    accepted, frozen = pair(c, user, job["id"], JOB, "accepted", Reference)
    spec.require(accepted.model_dump() == frozen == snapshot["project_check"])
    plan, binding = guard(store, c, user, frozen, limits)
    _, started = pair(
        c, user, accepted.project_id, START, accepted.plan_key + ":" + accepted.app_id, Start
    )
    spec.require(
        started["run_id"] == job["id"]
        and snapshot["instance_id"] == started["check_instance_id"]
        and snapshot["release_id"] == binding["context"]["release_id"]
        and snapshot["instance_id"] != binding["context"]["instance_id"]
        and job["project_id"] == accepted.project_id
        and job["runtime_id"] == binding["context"]["runtime_id"]
    )
    return plan


def start(store, user, pid, key, aid, body, limits):
    try:
        return _start(store, user, pid, key, aid, body, limits)
    except OperationalError as exc:
        # Only a failed transaction entrance is known to have made no writes.
        # Do not retry, mask errors inside a transaction, or change its budget.
        code = getattr(exc.orig, "sqlite_errorcode", None)
        if (
            store.engine.dialect.name == "sqlite"
            and exc.statement == "BEGIN IMMEDIATE"
            and isinstance(exc.orig, sqlite3.Error)
            and isinstance(code, int)
            and code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
        ):
            raise DomainError(
                "VERSION_CONFLICT",
                "Project account is busy; read this plan with its original key "
                "to resolve any concurrent request before another write.",
            ) from exc
        raise


def _start(store, user, pid, key, aid, body, limits):
    from .app_jobs import enqueue

    with store.tx() as c:
        _, plan = load_plan(store, c, user, pid, key, limits)
        spec.require(body.expected_plan_fingerprint == plan["plan_fingerprint"])
        binding = member(plan, aid)
        ctx = binding["context"]
        stagekey = key + ":" + aid
        if graph.lookup(c, user, pid, START, stagekey):
            old, value = pair(c, user, pid, START, stagekey, Start)
            spec.require(old == body)
            job = (
                c.execute(
                    select(runs).where(runs.c.id == value["run_id"], runs.c.principal_id == user)
                )
                .mappings()
                .one()
            )
            snap = c.execute(
                select(internal_run_bindings.c.snapshot).where(
                    internal_run_bindings.c.run_id == job["id"]
                )
            ).scalar_one()
            job_gate(store, c, user, job, snap, limits)
            return value
        local = binding["proposal"]
        if local:
            spec.require(
                graph.lookup(c, user, ctx["instance_id"], logic.CHECK, local["request_key"])
                is None,
                "The selected proposal already has a different CHECK",
            )
        request_key = "project-check-" + fingerprint(dict(pid=pid, key=key, aid=aid))[:48]
        inst = lifecycle.create_instance_tx(
            store,
            c,
            user,
            ctx["release_id"],
            ctx["release_fingerprint"],
            limits,
            request_key=request_key,
        )
        reference = ref(pid, key, plan, aid)
        checked = enqueue(
            store,
            user,
            inst["id"],
            inst["revision"],
            ctx["release_fingerprint"],
            {},
            local["request_key"] if local else request_key,
            limits,
            logic_tx=c,
            logic_check=logic.reference(ctx["instance_id"], local["request_key"], local)
            if local
            else None,
            project_check=reference,
        )
        value = dict(
            **checked,
            check_instance_id=inst["id"],
            project_id=pid,
            app_id=aid,
            plan_key=key,
            plan_fingerprint=plan["plan_fingerprint"],
            role=binding["role"],
        )
        remember(c, user, pid, START, stagekey, body, value)
        if local:
            confirmation = logic.Check(
                request_key=local["request_key"],
                expected_preview_fingerprint=local["preview_fingerprint"],
                consent="RUN_EXACT_LOCAL_LOGIC_CHECK_KEEP_ORIGINAL",
            )
            remember(
                c, user, ctx["instance_id"], logic.CHECK, local["request_key"], confirmation, value
            )
        load_plan(store, c, user, pid, key, limits)
        return value


@graph.controlled
def outcome(store, c, user, pid, key, aid, limits):
    _, plan = load_plan(store, c, user, pid, key, limits)
    binding = member(plan, aid)
    stagekey = key + ":" + aid
    if not graph.lookup(c, user, pid, START, stagekey):
        return dict(app_id=aid, role=binding["role"], status="NOT_RUN")
    _, started = pair(c, user, pid, START, stagekey, Start)
    job = (
        c.execute(select(runs).where(runs.c.id == started["run_id"], runs.c.principal_id == user))
        .mappings()
        .one()
    )
    bound, outputs, proved = spec.verify_job(store, c, user, job, limits)
    job_gate(store, c, user, job, bound["snapshot"], limits)
    value = dict(
        app_id=aid,
        role=binding["role"],
        run_id=job["id"],
        check_instance_id=started["check_instance_id"],
        status="PASS" if job["status"] == "SUCCEEDED" else "NOT_PASSED",
        run_status=job["status"],
        cancel_intent=job["cancel_intent"],
        executed_model_requests=job["context"]["requests"],
    )
    if job["status"] == "SUCCEEDED":
        spec.require(
            len(proved) == 6 and bound["draft"]["candidate"] == binding["effective_candidate"]
        )
        value["actual_proof_fingerprint"] = fingerprint(
            dict(job=dict(job), output=outputs, proved=proved)
        )
        value["declared_checks"] = [
            dict(
                node_id=n["id"],
                revision=n["revision"],
                content_fingerprint=n["content_fingerprint"],
                check_ref=n["definition"]["check_ref"],
                status="PASS",
            )
            for n in binding["target_graph"]["nodes"]
            if n["kind"] == "CHECK"
        ]
        if binding["proposal"]:
            _, proof = logic.checked(
                store,
                c,
                user,
                binding["context"]["instance_id"],
                binding["proposal"]["request_key"],
                limits,
                _project_partial=True,
            )
            value["local_check_fingerprint"] = proof["check_fingerprint"]
        value["proof_fingerprint"] = fingerprint(value)
        if graph.lookup(c, user, pid, PROOF, stagekey):
            _, sealed = pair(c, user, pid, PROOF, stagekey, Start)
            spec.require(sealed == value, "Independent project CHECK receipt changed")
        else:
            accepted, _ = pair(c, user, pid, START, stagekey, Start)
            remember(c, user, pid, PROOF, stagekey, accepted, value)
    return value


def require_complete_checks(store, c, user, reference, limits):
    plan, _ = guard(store, c, user, reference, limits)
    # Pure verification avoids calling logic.checked recursively from aggregate.
    for binding in plan["applications"]:
        aid = binding["context"]["app_id"]
        stagekey = plan["request_key"] + ":" + aid
        spec.require(
            graph.lookup(c, user, plan["project_id"], START, stagekey) is not None,
            "All frozen project members need independent CHECK",
        )
        _, started = pair(c, user, plan["project_id"], START, stagekey, Start)
        job = (
            c.execute(
                select(runs).where(runs.c.id == started["run_id"], runs.c.principal_id == user)
            )
            .mappings()
            .one()
        )
        b, _, proved = spec.verify_job(store, c, user, job, limits)
        spec.require(
            job["status"] == "SUCCEEDED"
            and not job["cancel_intent"]
            and len(proved) == 6
            and b["draft"]["candidate"] == binding["effective_candidate"],
            "Project member CHECK has not passed",
        )
    return plan


def pins(c, user, i):
    """Owned scalar role hints: rejection only, never proof or private PLAN read."""
    source = (
        c.execute(
            select(delivery_graph_requests.c.request_key).where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.app_id == i["id"],
                delivery_graph_requests.c.kind.in_([SOURCE, SOURCE + "_seal"]),
            )
        )
        .scalars()
        .all()
    )
    # PLAN's two public source identifiers retain roles even if SOURCE is missing.
    from sqlalchemy import or_

    source += (
        c.execute(
            select(delivery_graph_requests.c.request_key).where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.app_id == i["project_id"],
                delivery_graph_requests.c.kind.in_([PLAN, PLAN + "_seal"]),
                or_(
                    delivery_graph_requests.c.snapshot["request"]["selections"][0][
                        "instance_id"
                    ].as_string()
                    == i["id"],
                    delivery_graph_requests.c.snapshot["request"]["selections"][1][
                        "instance_id"
                    ].as_string()
                    == i["id"],
                ),
            )
        )
        .scalars()
        .all()
    )
    jobs = (
        c.execute(
            select(internal_run_bindings.c.run_id)
            .join(runs, runs.c.id == internal_run_bindings.c.run_id)
            .join(internal_app_runs, internal_app_runs.c.id == internal_run_bindings.c.app_run_id)
            .where(
                runs.c.principal_id == user,
                runs.c.project_id == i["project_id"],
                internal_app_runs.c.principal_id == user,
                internal_app_runs.c.instance_id == i["id"],
                internal_run_bindings.c.snapshot["project_check"]["project_id"]
                .as_string()
                .is_not(None),
            )
        )
        .scalars()
        .all()
    )
    indexed = (
        c.execute(
            select(delivery_graph_requests.c.app_id)
            .join(runs, runs.c.id == delivery_graph_requests.c.app_id)
            .join(internal_app_runs, runs.c.request_key == "internal:" + internal_app_runs.c.id)
            .where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.kind.in_([JOB, JOB + "_seal"]),
                runs.c.principal_id == user,
                runs.c.project_id == i["project_id"],
                internal_app_runs.c.principal_id == user,
                internal_app_runs.c.instance_id == i["id"],
            )
        )
        .scalars()
        .all()
    )
    retained = (
        c.execute(
            select(delivery_graph_requests.c.snapshot["response"]["run_id"].as_string()).where(
                delivery_graph_requests.c.principal_id == user,
                delivery_graph_requests.c.app_id == i["project_id"],
                delivery_graph_requests.c.kind.in_([START, START + "_seal"]),
                delivery_graph_requests.c.snapshot["response"]["check_instance_id"].as_string()
                == i["id"],
            )
        )
        .scalars()
        .all()
    )
    active_sources = []
    for key in sorted(set(source)):
        if close_present(c, user, i["project_id"], key):
            _, receipt = close_receipt(c, user, i["project_id"], key)
            accepted, seal = pair(c, user, i["id"], SOURCE, key, Reference)
            spec.require(
                accepted.model_dump() == seal
                and dict(**seal, instance_id=i["id"]) in receipt["released_sources"],
                "Source closure binding changed",
            )
        else:
            active_sources.append(key)
    return [dict(role="project_source", plan_key=key) for key in active_sources] + [
        dict(role="project_check", run_id=jid)
        for jid in sorted(set(jobs) | set(indexed) | set(retained), key=str)
    ]


def version_receipt(store, c, user, pid, key, limits):
    _, plan = load_plan(store, c, user, pid, key, limits)
    body, frozen = pair(c, user, pid, VERSION + ".approval", key, Version)
    require_complete_checks(
        store, c, user, ref(pid, key, plan, frozen["app_id"]).model_dump(), limits
    )
    local = member(plan, frozen["app_id"])
    old, approval = pair(
        c,
        user,
        local["context"]["instance_id"],
        logic.APPROVAL,
        local["proposal"]["request_key"],
        logic.Version,
    )
    spec.require(
        body.expected_plan_fingerprint == plan["plan_fingerprint"]
        and approval == frozen["approval"]
        and old.expected_check_fingerprint == body.expected_check_fingerprint
    )
    proofs = [
        outcome(store, c, user, pid, key, x["context"]["app_id"], limits)
        for x in plan["applications"]
    ]
    spec.require(proofs == frozen["checks"])
    from .db import internal_releases

    releases = (
        c.execute(
            select(internal_releases.c.id).where(
                internal_releases.c.principal_id == user,
                internal_releases.c.project_id == pid,
                internal_releases.c.approval_id == approval["id"],
            )
        )
        .scalars()
        .all()
    )
    spec.require(len(releases) <= 1)
    release = lifecycle.read_release(store, c, user, releases[0], limits) if releases else None
    return {**frozen, "status": "COMMITTED" if release else "PROPOSED", "release": release}


def mount(app, store, limits, identity):
    dep = Depends(identity)
    base = "/api/projects/{pid}/natural-revalidation"

    @app.get(base + "/options")
    def read_options(pid: str, user=dep):
        with store.tx() as c:
            return options(store, c, user, pid, limits)

    @app.post(base + "/plans", status_code=201)
    def prepare(pid: str, body: Prepare, user=dep):
        with store.tx() as c:
            catalog = options(store, c, user, pid, limits)
            if graph.lookup(c, user, pid, PLAN, body.request_key):
                old, value = load_plan(store, c, user, pid, body.request_key, limits)
                spec.require(old == body)
                return value
            if (
                len(
                    c.execute(
                        select(delivery_graph_requests.c.request_key).where(
                            delivery_graph_requests.c.app_id == pid,
                            delivery_graph_requests.c.principal_id == user,
                            delivery_graph_requests.c.kind == PLAN,
                        )
                    ).all()
                )
                >= 16
            ):
                raise DomainError("BUDGET_EXCEEDED", "Finite project account capacity exhausted")
            value = calculate(store, c, user, pid, body, limits, catalog=catalog)
            spec.require(options(store, c, user, pid, limits) == catalog)
            remember(c, user, pid, PLAN, body.request_key, body, value)
            for binding in value["applications"]:
                reference = ref(pid, body.request_key, value, binding["context"]["app_id"])
                remember(
                    c,
                    user,
                    binding["context"]["instance_id"],
                    SOURCE,
                    body.request_key,
                    reference,
                    reference.model_dump(),
                )
            return value

    @app.get(base + "/plans")
    def history(pid: str, user=dep):
        with store.tx() as c:
            members(store, c, user, pid, limits)
            keys = (
                c.execute(
                    select(delivery_graph_requests.c.request_key)
                    .where(
                        delivery_graph_requests.c.app_id == pid,
                        delivery_graph_requests.c.principal_id == user,
                        delivery_graph_requests.c.kind == PLAN,
                    )
                    .order_by(delivery_graph_requests.c.request_key)
                )
                .scalars()
                .all()
            )
            items = []
            for key in keys:
                _, sources, _ = plan_metadata(c, user, pid, key)
                items.append(dict(request_key=key, plan_fingerprint=sources[0]["plan_fingerprint"]))
            return dict(**flags(), project_id=pid, principal_id=user, items=items)

    @app.post(base + "/plans/{key}/close")
    def close(pid: str, key: str, body: Close, user=dep):
        return close_account(store, user, pid, key, body, limits)

    @app.get(base + "/plans/{key}")
    def read(pid: str, key: str, user=dep):
        with store.tx() as c:
            store.lock_project(c, user, pid)
            if close_present(c, user, pid, key):
                _, plan = archived_plan(store, c, user, pid, key, limits)
                _, receipt = close_receipt(c, user, pid, key)
                validate_closed_plan(plan, receipt)
                return dict(
                    **flags(),
                    project_id=pid,
                    principal_id=user,
                    account_status="CLOSED_UNSTARTED",
                    plan=plan,
                    close_receipt=receipt,
                    applications=[],
                    local_checks_status="NOT_RUN",
                    version_approval_present=False,
                )
            _, plan = load_plan(store, c, user, pid, key, limits)
            items = [
                outcome(store, c, user, pid, key, x["context"]["app_id"], limits)
                for x in plan["applications"]
            ]
            modified = [x for x in plan["applications"] if x["role"] == "MODIFIED"]
            approval_present = bool(
                graph.lookup(c, user, pid, VERSION + ".approval", key)
                or graph.lookup(c, user, pid, VERSION + ".approval_seal", key)
            )
            if modified:
                local = modified[0]
                from .db import internal_releases

                approval_present = bool(
                    approval_present
                    or graph.lookup(
                        c,
                        user,
                        local["context"]["instance_id"],
                        logic.APPROVAL,
                        local["proposal"]["request_key"],
                    )
                    or graph.lookup(
                        c,
                        user,
                        local["context"]["instance_id"],
                        logic.APPROVAL + "_seal",
                        local["proposal"]["request_key"],
                    )
                    or c.execute(
                        select(internal_releases.c.id).where(
                            internal_releases.c.principal_id == user,
                            internal_releases.c.project_id == pid,
                            internal_releases.c.snapshot["natural_logic_source"][
                                "instance_id"
                            ].as_string()
                            == local["context"]["instance_id"],
                            internal_releases.c.snapshot["natural_logic_source"][
                                "preview_key"
                            ].as_string()
                            == local["proposal"]["request_key"],
                        )
                    ).first()
                )
            return dict(
                **flags(),
                project_id=pid,
                principal_id=user,
                version_approval_present=approval_present,
                plan=plan,
                applications=items,
                local_checks_status="PASS"
                if all(x["status"] == "PASS" for x in items)
                else "PARTIAL",
            )

    @app.post(base + "/plans/{key}/applications/{aid}/checks", status_code=202)
    def check(pid: str, key: str, aid: str, body: Start, user=dep):
        return start(store, user, pid, key, aid, body, limits)

    @app.post(base + "/plans/{key}/version-approvals", status_code=201)
    def approve(pid: str, key: str, body: Version, user=dep):
        with store.tx() as c:
            _, plan = load_plan(store, c, user, pid, key, limits)
            spec.require(body.expected_plan_fingerprint == plan["plan_fingerprint"])
            modified = [x for x in plan["applications"] if x["role"] == "MODIFIED"]
            spec.require(len(modified) == 1, "Exactly one selected local modification required")
            selected = modified[0]
            require_complete_checks(
                store,
                c,
                user,
                ref(pid, key, plan, selected["context"]["app_id"]).model_dump(),
                limits,
            )
            if graph.lookup(c, user, pid, VERSION + ".approval", key):
                old, _ = pair(c, user, pid, VERSION + ".approval", key, Version)
                spec.require(old == body)
                return version_receipt(store, c, user, pid, key, limits)
            approval = logic.propose_version_tx(
                store,
                c,
                user,
                selected["context"]["instance_id"],
                logic.Version(
                    request_key=selected["proposal"]["request_key"],
                    expected_check_fingerprint=body.expected_check_fingerprint,
                    consent=body.consent,
                ),
                limits,
            )
            proofs = [
                outcome(store, c, user, pid, key, x["context"]["app_id"], limits)
                for x in plan["applications"]
            ]
            result = dict(
                **flags(),
                project_id=pid,
                principal_id=user,
                plan_key=key,
                plan_fingerprint=plan["plan_fingerprint"],
                app_id=selected["context"]["app_id"],
                checks=proofs,
                approval=approval,
            )
            remember(c, user, pid, VERSION + ".approval", key, body, result)
            return version_receipt(store, c, user, pid, key, limits)

    @app.get(base + "/plans/{key}/version-approval")
    def read_approval(pid: str, key: str, user=dep):
        with store.tx() as c:
            return version_receipt(store, c, user, pid, key, limits)

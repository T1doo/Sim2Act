"""Owner-authored GoalCards for independent literal apps; no execution authority.

Fresh native cards and their app/version bindings are atomically double sealed.
They never adopt a source or target application's criteria or owner decision.
"""

import copy
import time
from typing import Literal

from pydantic import Field
from sqlalchemy import insert, select, update

from . import delivery_graph_apps as graph
from . import text_logic_reuse as logic
from .apps import load_draft
from .contracts import Strict
from .db import (
    app_drafts,
    delivery_graph_requests,
    fingerprint,
    goal_card_versions,
    goal_cards,
    new_id,
)
from .errors import DomainError
from .goals import GoalCardInput, Line
from .tools import authorized_read

VERSION = "app-owned-text-goal.v1"
KIND = "app_owned_text_goal"
MAX_VERSIONS = 64


class SaveInput(Strict):
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_goal_version: int = Field(ge=0)
    expected_goal_fingerprint: str | None = Field(default=None, pattern=graph.HASH)
    expected_binding_fingerprint: str | None = Field(default=None, pattern=graph.HASH)
    goal: GoalCardInput
    applicability: list[Line] = Field(min_length=1, max_length=16)
    consent: Literal["AUTHOR_THIS_APPLICATION_OWN_GOAL_AND_SCOPE"]
    request_key: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")


def scope(store, c, user, aid, limits):
    pid = c.execute(select(app_drafts.c.project_id).where(app_drafts.c.id == aid)).scalar_one_or_none()
    store.lock_project(c, user, pid)
    draft, manifest, _, _ = load_draft(store, c, user, aid, limits, lock=True)
    if not logic.independent(draft):
        raise DomainError("UNSUPPORTED_CAPABILITY", "Independent literal application required")
    obj, _, _ = logic.verify_candidate(store, c, user, draft, limits)
    rid = manifest.data_bindings[0].resource_ref
    source = authorized_read(store, c, user, draft["runtime_id"], pid, "resource.read", {"resource_id": rid})
    anchor = dict(app_id=aid, owner_id=user, project_id=pid, runtime_id=draft["runtime_id"],
                  candidate_fingerprint=draft["fingerprint"], resource_id=rid,
                  source_hash=source["hash"], logic_id=obj["id"], logic_fingerprint=obj["fingerprint"])
    return draft, source, anchor


def records(c, user, aid, anchor):
    rows = c.execute(select(delivery_graph_requests.c.request_key, delivery_graph_requests.c.kind).where(
        delivery_graph_requests.c.app_id == aid, delivery_graph_requests.c.principal_id == user,
        delivery_graph_requests.c.kind.in_([KIND, KIND + "_seal"]))).mappings().all()
    left = {r["request_key"] for r in rows if r["kind"] == KIND}
    right = {r["request_key"] for r in rows if r["kind"] == KIND + "_seal"}
    logic.require(left == right and len(left) <= MAX_VERSIONS)
    values = []
    for key in left:
        body, value = logic.pair(c, user, aid, KIND, key, SaveInput)
        logic.require(body.request_key == key and set(value) == {
            "namespace", "anchor", "card_id", "goal_version", "goal_fingerprint", "snapshot",
            "applicability", "sequence", "previous_binding_fingerprint", "request_key", "request_fingerprint"})
        logic.require(fingerprint(value["anchor"]) == fingerprint(anchor)
            and fingerprint(value["applicability"]) == fingerprint(body.applicability)
            and value["request_fingerprint"] == fingerprint(body.model_dump())
            and value["request_key"] == key and value["namespace"] == VERSION
            and fingerprint(value["snapshot"]["content"]) == fingerprint(body.goal.model_dump())
            and fingerprint(value["snapshot"]) == value["goal_fingerprint"]
            and body.goal.resource_refs == [anchor["resource_id"]]
            and body.goal.constraints and body.goal.acceptance_checks)
        native = c.execute(select(goal_card_versions).where(goal_card_versions.c.card_id == value["card_id"],
            goal_card_versions.c.version == value["goal_version"])).mappings().first()
        logic.require(native is not None and native["fingerprint"] == value["goal_fingerprint"]
                      and fingerprint(native["snapshot"]) == fingerprint(value["snapshot"]))
        values.append((body, value))
    values.sort(key=lambda v: v[1]["sequence"])
    previous = None
    cid = None
    for sequence, (body, value) in enumerate(values, 1):
        logic.require(type(value["sequence"]) is int and value["sequence"] == sequence
            and value["previous_binding_fingerprint"] == previous
            and body.expected_binding_fingerprint == previous
            and (cid is None or cid == value["card_id"])
            and type(value["goal_version"]) is int
            and value["goal_version"] == body.expected_goal_version + 1)
        previous, cid = fingerprint(value), value["card_id"]
    return values


def head(c, user, anchor, values):
    if not values:
        return None
    cid = values[-1][1]["card_id"]
    row = c.execute(select(goal_cards).where(goal_cards.c.id == cid)).mappings().first()
    logic.require(row is not None and row["project_id"] == anchor["project_id"])
    # Metadata is sufficient for an explicit CAS after a generic GoalCard edit.
    return dict(card_id=cid, version=row["version"], fingerprint=row["fingerprint"], title=row["title"])


def view(anchor, values, current_head):
    latest = values[-1][1] if values else None
    active = bool(latest and current_head["version"] == latest["goal_version"]
                  and current_head["fingerprint"] == latest["goal_fingerprint"]
                  and current_head["title"] == latest["snapshot"]["content"]["title"])
    return dict(namespace=VERSION, anchor=anchor, sequence=len(values), head=current_head,
        binding_fingerprint=fingerprint(latest) if latest else None,
        current={**copy.deepcopy(latest), "binding_fingerprint": fingerprint(latest)} if active and latest is not None else None,
        status="CURRENT" if active else "STALE" if latest else "MISSING",
        history=[dict(request_key=v["request_key"], sequence=v["sequence"], card_id=v["card_id"],
            goal_version=v["goal_version"], goal_fingerprint=v["goal_fingerprint"],
            binding_fingerprint=fingerprint(v)) for _, v in values],
        owner_acceptance="PENDING", technical_semantic_status="UNKNOWN", model_requests=0,
        formal_publication_enabled=False)


@graph.controlled
def read(store, user, aid, limits, key=None):
    with store.tx() as c:
        _, _, anchor = scope(store, c, user, aid, limits)
        values = records(c, user, aid, anchor)
        result = view(anchor, values, head(c, user, anchor, values))
        if key is not None:
            old = next(((b, v) for b, v in values if b.request_key == key), None)
            if old is None:
                raise DomainError("OUTCOME_UNKNOWN", "No effect for this original goal request")
            result["recovered"] = {**copy.deepcopy(old[1]), "binding_fingerprint": fingerprint(old[1])}
        return result


@graph.controlled
def current(store, c, user, draft, limits):
    _, _, anchor = scope(store, c, user, draft["id"], limits)
    values = records(c, user, draft["id"], anchor)
    state = view(anchor, values, head(c, user, anchor, values))
    if state["status"] != "CURRENT":
        raise DomainError("VERSION_CONFLICT", "Author this application's current GoalCard and scope")
    return state["current"]


def run_ref(store, c, user, draft, limits):
    _, _, anchor = scope(store, c, user, draft["id"], limits)
    values = records(c, user, draft["id"], anchor)
    if not values:
        return None
    value = current(store, c, user, draft, limits)
    return {k: copy.deepcopy(value[k]) for k in ("card_id", "goal_version", "goal_fingerprint",
                                               "binding_fingerprint", "sequence")}


def check_run(store, c, user, draft, limits, snapshot):
    if not logic.independent(draft):
        if "owner_goal" in snapshot or "owner_goal_binding_fingerprint" in snapshot:
            raise DomainError("VERSION_CONFLICT", "Owner GoalCard cannot change executor family")
        return
    expected = run_ref(store, c, user, draft, limits)
    logic.require(fingerprint(expected) == fingerprint(snapshot.get("owner_goal")),
                  "Own GoalCard changed after accepted Run; submit a fresh exact input")
    if expected is not None:
        logic.require(expected["binding_fingerprint"] == snapshot.get("owner_goal_binding_fingerprint"))


def verify_frozen_run(store, c, user, draft, limits, snapshot, *, archival_software=None):
    """Historical technical results retain their own sealed goal version."""
    if "owner_goal" not in snapshot and "owner_goal_binding_fingerprint" not in snapshot:
        return
    logic.require(logic.independent(draft) and "owner_goal" in snapshot
                  and "owner_goal_binding_fingerprint" in snapshot
                  and isinstance(snapshot["owner_goal"], dict)
                  and set(snapshot["owner_goal"]) == {"card_id", "goal_version", "goal_fingerprint", "binding_fingerprint", "sequence"}
                  and type(snapshot["owner_goal"]["goal_version"]) is int
                  and type(snapshot["owner_goal"]["sequence"]) is int)
    if archival_software is None:
        _, _, anchor = scope(store, c, user, draft["id"], limits)
    else:
        from .text_continuations import goal_anchor

        anchor = goal_anchor(store, c, user, draft, limits, archival_software)
    values = records(c, user, draft["id"], anchor)
    frozen = snapshot["owner_goal"]
    match = next((v for _, v in values if fingerprint(v) == snapshot["owner_goal_binding_fingerprint"]), None)
    if match is None:
        raise DomainError("VERSION_CONFLICT", "Frozen own GoalCard binding is missing")
    expected = {k: copy.deepcopy(match[k]) for k in ("card_id", "goal_version", "goal_fingerprint", "sequence")}
    expected["binding_fingerprint"] = fingerprint(match)
    logic.require(fingerprint(expected) == fingerprint(frozen))


@graph.controlled
def save(store, user, aid, body, limits):
    with store.tx() as c:
        _, source, anchor = scope(store, c, user, aid, limits)
        logic.require(body.expected_candidate_fingerprint == anchor["candidate_fingerprint"])
        if body.goal.resource_refs != [anchor["resource_id"]] or not body.goal.constraints or not body.goal.acceptance_checks:
            raise DomainError("INVALID_INPUT", "Own goal needs this one material, constraints and acceptance checks")
        if any(not s.strip() for s in [body.goal.title, body.goal.goal, *body.applicability,
            *body.goal.known, *body.goal.assumptions, *body.goal.unresolved,
            *body.goal.constraints, *body.goal.acceptance_checks]):
            raise DomainError("INVALID_INPUT", "Explicit nonblank goal and scope entries required")
        values = records(c, user, aid, anchor)
        old = next(((b, v) for b, v in values if b.request_key == body.request_key), None)
        if old:
            logic.require(fingerprint(old[0].model_dump()) == fingerprint(body.model_dump()))
            return dict(**copy.deepcopy(old[1]), binding_fingerprint=fingerprint(old[1]), cached=True,
                        model_requests=0, formal_publication_enabled=False)
        h = head(c, user, anchor, values)
        previous = fingerprint(values[-1][1]) if values else None
        logic.require(body.expected_binding_fingerprint == previous)
        logic.require((h is None and body.expected_goal_version == 0 and body.expected_goal_fingerprint is None)
            or (h is not None and body.expected_goal_version == h["version"]
                and body.expected_goal_fingerprint == h["fingerprint"]))
        if len(values) >= MAX_VERSIONS:
            raise DomainError("BUDGET_EXHAUSTED", "Own GoalCard binding version limit reached")
        snapshot = dict(schema_version="F2-goal-card.v1", content=body.goal.model_dump(),
            resource_snapshots=[dict(resource_id=anchor["resource_id"], hash=source["hash"], format=source["format"])])
        cid, version, fp, now = h["card_id"] if h else new_id("goal"), body.expected_goal_version + 1, fingerprint(snapshot), time.time()
        if h:
            changed = c.execute(update(goal_cards).where(goal_cards.c.id == cid,
                goal_cards.c.version == h["version"], goal_cards.c.fingerprint == h["fingerprint"])
                .values(version=version, fingerprint=fp, title=body.goal.title)).rowcount
            logic.require(changed == 1)
        else:
            c.execute(insert(goal_cards).values(id=cid, project_id=anchor["project_id"],
                title=body.goal.title, version=version, fingerprint=fp, created_at=now))
        c.execute(insert(goal_card_versions).values(card_id=cid, version=version,
            snapshot=snapshot, fingerprint=fp, created_at=now))
        value = dict(namespace=VERSION, anchor=anchor, card_id=cid, goal_version=version,
            goal_fingerprint=fp, snapshot=snapshot, applicability=body.applicability,
            sequence=len(values) + 1, previous_binding_fingerprint=previous,
            request_key=body.request_key, request_fingerprint=fingerprint(body.model_dump()))
        logic.remember(c, user, aid, KIND, body.request_key, body, value)
        current(store, c, user, {"id": aid}, limits)
        return dict(**value, binding_fingerprint=fingerprint(value), cached=False,
                    model_requests=0, formal_publication_enabled=False)


def mount(app, store, limits, identity):
    from fastapi import Depends
    from fastapi.responses import JSONResponse

    dependency = Depends(identity)

    @app.get("/api/internal/apps/{aid}/owner-goals")
    def inspect(aid: str, request_key: str | None = None, user=dependency):
        return JSONResponse(read(store, user, aid, limits, request_key),
                            headers={"Cache-Control": "no-store", "Vary": "Authorization"})

    @app.post("/api/internal/apps/{aid}/owner-goals", status_code=201)
    def submit(aid: str, body: SaveInput, user=dependency):
        return save(store, user, aid, body, limits)

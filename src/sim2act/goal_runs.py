"""Saved human goal → ordinary read-only task, never successful app provenance."""

from pydantic import Field
from sqlalchemy import select

from .contracts import GoalCardRunSource, Strict
from .db import events, fingerprint, goal_card_versions, goal_cards, run_contracts
from .errors import DomainError
from .goals import GoalCardInput, validate_card_version


class GoalRunInput(Strict):
    expected_version: int = Field(ge=1)
    expected_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(min_length=1, max_length=100)


def resolve_source(store, c, user, project, requested, prior):
    """Called inside the enqueue transaction and its existing project lock."""
    card = c.execute(select(goal_cards).where(
        goal_cards.c.id == requested["card_id"],
        goal_cards.c.project_id == project["id"],
    ).with_for_update()).mappings().first()
    if not card:
        raise DomainError("PERMISSION_DENIED")
    if prior:
        contract = store.frozen_contract(c, prior)
        binding = contract.source_goal_card
        if binding is None or any(getattr(binding, k) != requested[k] for k in
                                  ("card_id", "version", "fingerprint")):
            raise DomainError("VERSION_CONFLICT", "Request key belongs to another goal input")
        return binding
    if card["version"] != requested["version"] or card["fingerprint"] != requested["fingerprint"]:
        raise DomainError("VERSION_CONFLICT", "Saved goal changed; reopen before starting")
    saved = validate_card_version(store, c, user, card["id"], card["version"])
    if saved["fingerprint"] != requested["fingerprint"]:
        raise DomainError("VERSION_CONFLICT")
    GoalCardInput.model_validate(saved["snapshot"]["content"])
    return GoalCardRunSource(**requested, snapshot=saved["snapshot"])


def has_goal_source(c, run_id):
    return any("goal_source" in data for data in c.execute(select(events.c.data).where(
        events.c.run_id == run_id, events.c.kind == "ACCEPTED",
    )).scalars())


def verify_source(store, c, run, contract):
    source = contract.source_goal_card
    if source is None:
        return
    # Contract validation is structural. Existing send/read/effect gates check
    # current authorization; do not acquire Grant locks under a worker Run lock.
    card = c.execute(select(goal_cards).where(goal_cards.c.id == source.card_id)).mappings().first()
    if not card or card["project_id"] != run["project_id"]:
        raise DomainError("VERSION_CONFLICT", "Goal source project differs from task")
    store.own_project(c, run["principal_id"], card["project_id"])
    saved = c.execute(select(goal_card_versions).where(
        goal_card_versions.c.card_id == source.card_id,
        goal_card_versions.c.version == source.version,
    )).mappings().first()
    if not saved:
        raise DomainError("VERSION_CONFLICT", "Missing frozen goal history")
    content = GoalCardInput.model_validate(source.snapshot.get("content")).model_dump()
    if (
        fingerprint(source.snapshot) != source.fingerprint
        or saved["fingerprint"] != source.fingerprint
        or saved["snapshot"] != source.snapshot
        or contract.goal.goal_id != source.card_id
        or contract.goal.goal != content["goal"]
        or contract.goal.constraints != content["constraints"]
        or contract.goal.unresolved != content["unresolved"]
        or contract.goal.resource_refs != content["resource_refs"]
    ):
        raise DomainError("VERSION_CONFLICT", "Frozen task differs from its saved goal")
    expected = fingerprint({
        "goal": contract.goal.goal, "resource_refs": contract.goal.resource_refs,
        "policy": {"limits": contract.limits.model_dump(), "mode": contract.mode,
                   "request_model": contract.request_model,
                   **({"natural_planning": contract.natural_planning.model_dump()}
                      if contract.natural_planning is not None else {})},
        "goal_source": source.model_dump(),
    })
    accepted = c.execute(select(events.c.data).where(
        events.c.run_id == run["id"], events.c.kind == "ACCEPTED",
    )).scalars().all()
    if (run["fingerprint"] != expected or run["context"].get("saved_goal_input") != expected
            or fingerprint(accepted) != fingerprint([{"input_fingerprint": expected,
                             "goal_source": {"card_id": source.card_id, "version": source.version,
                                             "fingerprint": source.fingerprint},
                             **({"natural_planning": contract.natural_planning.model_dump()}
                                if contract.natural_planning is not None else {})}])):
        raise DomainError("VERSION_CONFLICT", "Goal source differs from original acceptance")


def acceptance(store, user, run_id):
    with store.tx() as c:
        saved = c.execute(select(run_contracts.c.snapshot).where(
            run_contracts.c.run_id == run_id,
        )).scalar_one()
        source = saved["source_goal_card"]
        return {
            "run_id": run_id, "status": "ACCEPTED", "goal_card_id": source["card_id"],
            "goal_version": source["version"], "goal_fingerprint": source["fingerprint"],
            "goal_acceptance": "NOT_RUN", "candidate_generated": False,
        }

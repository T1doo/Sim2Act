"""Saved human goal → ordinary read-only task, never successful app provenance."""

from pydantic import Field
from sqlalchemy import select

from .contracts import GoalCardRunSource, Strict
from .db import fingerprint, goal_cards, run_contracts
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


def verify_source(store, c, run, contract):
    source = contract.source_goal_card
    if source is None:
        return
    saved = validate_card_version(store, c, run["principal_id"], source.card_id, source.version)
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

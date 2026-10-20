"""Queued synthetic Generate source only; no model history or acceptance claim."""

import copy

import pytest
from sqlalchemy import select
from test_cold_binding_fact_leaves import no_external_transport as no_external_transport
from test_natural_spec_apps import SOURCE, facts, recipe, setup

from sim2act import goal_applications as generation
from sim2act import natural_specs as natural
from sim2act.db import attempts, runs
from sim2act.errors import DomainError


@pytest.fixture
def queued(env):
    data = setup(env)
    store, _, client, _, pid, _, card = data
    response = client.post(f"/api/projects/{pid}/goal-cards/{card['id']}/application-runs",
        json=dict(expected_version=card["version"], expected_fingerprint=card["fingerprint"],
            request_key="natural-facts-unit", family="natural_spec"))
    assert response.status_code == 202, response.text
    try:
        with store.tx() as c:
            run = dict(c.execute(select(runs).where(runs.c.id == response.json()["run_id"])).mappings().one())
            contract, material = generation.source(store, c, run)
        graph = recipe("ordered")
        value = dict(recipe=graph, sample_nodes=[dict(step_id=s["step_id"],
            items=[item for item in facts(SOURCE) if item["kind"] in natural.MODEL_KINDS[s["operator"]]])
            for s in graph["steps"] if s["operator"] in natural.MODEL_KINDS],
            source_hash=material["hash"], goal=contract.source_goal_card.snapshot["content"])
        yield store, run, contract, material, value
        with store.tx() as c:
            assert c.execute(select(attempts.c.id)).first() is None
    finally:
        client.close()


def test_natural_fact_inputs_share_full_message_and_sample_core(queued, monkeypatch):
    store, run, contract, material, value = queued
    original, calls = generation.source, []
    def source(*args):
        calls.append("source")
        return original(*args)
    monkeypatch.setattr(generation, "source", source)
    with store.tx() as c:
        messages = natural.initial_messages(store, c, run)
        assert messages == natural._initial_messages_from_facts(contract, material)
        candidate = natural.from_response(store, c, run, value)
        actual = natural._from_response_from_facts(run, contract, material, value)
        assert actual == candidate and calls == ["source", "source"]
        assert actual["spec_recipe"] == value["recipe"]
        assert actual["source_hash"] == material["hash"]


def test_natural_full_sample_errors_match_without_extra_source_calls(queued):
    store, run, contract, material, value = queued
    for broken in ({}, {**value, "sample_nodes": list(reversed(value["sample_nodes"]))},
            {**value, "sample_nodes": value["sample_nodes"][:1]}):
        with store.tx() as c:
            with pytest.raises(DomainError) as public:
                natural.from_response(store, c, run, copy.deepcopy(broken))
            with pytest.raises(DomainError) as explicit:
                natural._from_response_from_facts(run, contract, material, copy.deepcopy(broken))
        assert public.value.public() == explicit.value.public()


def test_public_source_error_precedes_sample_shape_and_keeps_original_exception(queued, monkeypatch):
    store, run, _, _, _ = queued
    original = DomainError("GRANT_REVOKED", "synthetic current source denial")
    def denied(*args):
        raise original
    monkeypatch.setattr(generation, "source", denied)
    with store.tx() as c:
        with pytest.raises(DomainError) as caught:
            natural.from_response(store, c, run, {})
    assert caught.value is original

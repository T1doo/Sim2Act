"""Strict input versions must not rely on Python numeric equality."""

import copy

import pytest
from test_delivery_graph import fixture, inputs, request

from sim2act.delivery_graph import derive_manifest_graph, plan_change
from sim2act.errors import DomainError


def seeded():
    candidate, limits = fixture("multi")
    versions, ids, context = inputs(candidate)
    graph = derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )
    context["graph_fingerprint"] = graph["graph_fingerprint"]
    return candidate, limits, versions, ids, context, graph


@pytest.mark.parametrize("bad_revision", [True, 1.0])
def test_each_external_version_rejects_equal_numeric_type_without_changing_context(bad_revision):
    candidate, limits, versions, ids, context, _ = seeded()
    for key in versions:
        altered = copy.deepcopy(versions)
        altered[key]["revision"] = bad_revision
        assert altered == versions  # The former equality-only input gate accepted this.
        with pytest.raises(DomainError) as rejected:
            derive_manifest_graph(
                candidate["manifest"], candidate["actions"], altered, ids, context, limits
            )
        assert rejected.value.code == "INVALID_MANIFEST", key
    # Keep the exact valid API result and stable IDs unchanged.
    assert derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )["nodes"]


@pytest.mark.parametrize("bad_revision", [True, 1.0])
@pytest.mark.parametrize(
    "location",
    [
        "derive_context_versions",
        "plan_context_versions",
        "plan_auth_revision",
        "plan_node_revision",
        "request_revision",
        "graph_revision",
        "graph_auth_revision",
    ],
)
def test_other_revision_boundaries_remain_strict(location, bad_revision):
    candidate, limits, versions, ids, context, graph = seeded()
    body = request(graph, "action:left")
    if location.endswith("context_versions"):
        for version in context["source_versions"].values():
            version["revision"] = bad_revision
    elif location == "plan_auth_revision":
        context["authorization_revision"] = bad_revision
    elif location == "plan_node_revision":
        context["node_revisions"]["action:left"] = bad_revision
    elif location == "request_revision":
        body["changes"][0]["expected_revision"] = bad_revision
    elif location == "graph_revision":
        graph["nodes"][0]["revision"] = bad_revision
    else:
        graph["authorization_revision"] = bad_revision
    with pytest.raises(DomainError) as rejected:
        if location == "derive_context_versions":
            derive_manifest_graph(
                candidate["manifest"], candidate["actions"], versions, ids, context, limits
            )
        else:
            plan_change(graph, graph["graph_fingerprint"], body, context)
    assert rejected.value.code == "INVALID_MANIFEST"


@pytest.mark.parametrize(
    "bad_versions",
    [
        None,
        [],
        True,
        {"extra": None},
        {"extra": {"revision": 1, "content_fingerprint": "a" * 64, "unexpected": True}},
    ],
)
def test_source_versions_requires_closed_mapping(bad_versions):
    candidate, limits, _, ids, context, _ = seeded()
    with pytest.raises(DomainError) as rejected:
        derive_manifest_graph(
            candidate["manifest"], candidate["actions"], bad_versions, ids, context, limits
        )
    assert rejected.value.code == "INVALID_MANIFEST"


def test_valid_but_changed_source_revision_is_still_version_conflict():
    candidate, limits, versions, ids, context, _ = seeded()
    versions[next(iter(versions))]["revision"] = 2
    with pytest.raises(DomainError) as rejected:
        derive_manifest_graph(
            candidate["manifest"], candidate["actions"], versions, ids, context, limits
        )
    assert rejected.value.code == "VERSION_CONFLICT"

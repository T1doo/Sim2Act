"""Offline independent graph oracles; no database fixture or model execution."""

import copy
import hashlib
import importlib.util
import json
import socket
import subprocess
from pathlib import Path

import pytest

from sim2act.apps import csv_candidate, object_schema
from sim2act.contracts import Limits
from sim2act.delivery_graph import derive_manifest_graph, plan_change
from sim2act.errors import DomainError


def uid(prefix, number):
    return prefix + "_" + format(number, "032x")


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def caps(multiplier=1):
    return Limits(
        max_requests=multiplier,
        max_tools=multiplier,
        max_repairs=0,
        max_total_tokens=1024 * multiplier,
        max_output_tokens=1024,
        run_seconds=30 * multiplier,
    )


def fixture(kind="csv"):
    if kind == "agent":
        # Reuse the repository's real bounded-agent manifest constructor only.
        path = Path(__file__).with_name("test_bounded_agent_apps.py")
        spec = importlib.util.spec_from_file_location("existing_agent_fixture", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        candidate = module.candidate(uid("res", 1), "合成证据")
        return candidate, Limits(**candidate["manifest"]["runtime_limits"])
    candidate = csv_candidate(uid("res", 1), "f" * 64, "synthetic", caps())
    if kind == "multi":
        second = copy.deepcopy(candidate["actions"][0])
        second["action_id"] = uid("action", 42)
        for item in second["dependencies"]:
            item["ref"] = uid("res", 2)
        for item in second["permission_requirements"]:
            item["resource_ref"] = uid("res", 2)
        candidate["actions"].append(second)
        m = candidate["manifest"]
        step_a = copy.deepcopy(m["workflow"][0])
        step_a.update(step_id="left", binding_id="left")
        step_b = copy.deepcopy(step_a)
        step_b.update(step_id="right", binding_id="right")
        step_b["inputs"]["resource_id"]["ref"] = "second"
        m["workflow"] = [step_a, step_b]
        m["action_bindings"] = [
            {"binding_id": key, "action_id": a["action_id"], "revision": 1}
            for key, a in zip(("left", "right"), candidate["actions"], strict=True)
        ]
        m["data_bindings"].append({"binding_id": "second", "resource_ref": uid("res", 2)})
        m["permission_requirements"].extend(second["permission_requirements"])
        m["dependency_lock"].append({"kind": "resource", "ref": uid("res", 2), "version": "1"})
        m["outputs"] = {
            key: {"source": "step", "ref": key, "field": "sum"} for key in ("left", "right")
        }
        m["output_schema"] = object_schema({key: {"type": "string"} for key in ("left", "right")})
        m["views"] = [{"component_ref": "text", "output_field": key} for key in ("left", "right")]
        m["runtime_limits"] = caps(2).model_dump()
        return candidate, caps(2)
    return candidate, caps()


def inputs(candidate):
    """Server snapshot fixture assembled independently from the declaration."""
    m = candidate["manifest"]
    external = {"goal:" + m["goal_ref"]}
    external.update("source:" + d["ref"] for d in m["dependency_lock"] if d["kind"] == "resource")
    external.update(
        "rule:" + d["kind"] + ":" + d["ref"]
        for d in m["dependency_lock"]
        if d["kind"] != "resource"
    )
    external.update("check:" + d["ref"] for d in m["dependency_lock"] if d["kind"] == "check")
    versions = {
        key: {"revision": 1, "content_fingerprint": digest({"external": key})} for key in external
    }
    keys = external | {"action:" + s["step_id"] for s in m["workflow"]}
    keys |= {"artifact:" + field for field in m["outputs"]}
    keys |= {"view:" + v["component_ref"] + ":" + v["output_field"] for v in m["views"]}
    keys.add("manifest:" + m["app_id"])
    ids = {key: uid("dg", index + 1) for index, key in enumerate(sorted(keys))}
    context = {
        "project_id": uid("proj", 10),
        "app_id": m["app_id"],
        "authorization_revision": 1,
        "authorized": True,
        "resource_ids": sorted(d["ref"] for d in m["dependency_lock"] if d["kind"] == "resource"),
        "node_revisions": dict.fromkeys(keys, 1),
        "locked_nodes": [],
        "source_versions": copy.deepcopy(versions),
        "dependency_edges": [],
        "unknown_dependencies": [],
    }
    return versions, ids, context


def derived(kind="csv", configure=None):
    candidate, limits = fixture(kind)
    versions, ids, context = inputs(candidate)
    if configure:
        configure(candidate, versions, ids, context)
    graph = derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )
    context["graph_fingerprint"] = graph["graph_fingerprint"]
    return graph, context, ids


def request(graph, *keys):
    by_key = {n["key"]: n for n in graph["nodes"]}
    return {
        "request_key": "synthetic-request",
        "project_id": graph["project_id"],
        "app_id": graph["app_id"],
        "changes": [
            {
                "node_id": by_key[k]["id"],
                "expected_revision": by_key[k]["revision"],
                "expected_content_fingerprint": by_key[k]["content_fingerprint"],
            }
            for k in keys
        ],
    }


def plan(graph, context, *keys, previous=None):
    return plan_change(graph, graph["graph_fingerprint"], request(graph, *keys), context, previous)


def error(code, call):
    with pytest.raises(DomainError) as failure:
        call()
    assert failure.value.code == code


@pytest.mark.parametrize("kind", ["csv", "agent", "multi"])
def test_real_declarations_deterministic_and_input_immutable(kind, monkeypatch):
    candidate, limits = fixture(kind)
    versions, ids, context = inputs(candidate)
    frozen = copy.deepcopy((candidate, versions, ids, context))

    def forbidden(*args, **kwargs):
        raise AssertionError("No network/process/DB dispatch allowed")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("sim2act.db.Store.__init__", forbidden)
    monkeypatch.setattr("sim2act.tools.dispatch", forbidden)
    monkeypatch.setattr("sim2act.tools.authorized_read", forbidden)
    graph = derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )
    reversed_context = copy.deepcopy(context)
    reversed_context["resource_ids"].reverse()
    again = derive_manifest_graph(
        candidate["manifest"],
        list(reversed(candidate["actions"])),
        dict(reversed(list(versions.items()))),
        dict(reversed(list(ids.items()))),
        reversed_context,
        limits,
    )
    assert graph == again
    assert (candidate, versions, ids, context) == frozen
    assert graph["graph_fingerprint"] == digest(
        {k: v for k, v in graph.items() if k != "graph_fingerprint"}
    )
    assert {n["id"] for n in graph["nodes"]} == set(ids.values())
    assert not any(n["kind"] == "RELEASE" for n in graph["nodes"])
    assert all(e["provenance"] == "DECLARED" for e in graph["edges"])


def test_hand_drawn_two_branch_oracle_retains_exact_unrelated_objects():
    graph, context, ids = derived("multi")
    before = copy.deepcopy((graph, context))
    receipt = plan(graph, context, "source:" + uid("res", 1))
    # Independent hand oracle: source1 -> left -> left result/view -> shared
    # checker -> manifest. No reverse propagation into the right branch.
    affected_keys = {
        "source:" + uid("res", 1),
        "action:left",
        "artifact:left",
        "view:text:left",
        "check:receipt.readback.v1",
        "manifest:" + graph["app_id"],
    }
    assert set(receipt["definite_impact"]) == {ids[k] for k in affected_keys}
    assert receipt["uncertain_impact"] == []
    assert receipt["revalidation_checks"] == [ids["check:receipt.readback.v1"]]
    assert receipt["invalidated_packages"] == [ids["manifest:" + graph["app_id"]]]
    assert receipt["retained_objects"] == [
        n for n in graph["nodes"] if n["key"] not in affected_keys
    ]
    assert (graph, context) == before
    assert receipt["patch_executed"] is False and receipt["business_write_performed"] is False
    assert receipt["publishable"] is False


@pytest.mark.parametrize(
    "edge_type", ["DATA", "RULE", "PRESENTATION", "SEMANTIC", "VERIFIED_BY", "PACKAGED_IN"]
)
def test_all_six_edges_propagate_to_independent_right_branch(edge_type):
    def extra(candidate, versions, ids, context):
        context["dependency_edges"] = [
            {
                "upstream": ids["action:left"],
                "downstream": ids["action:right"],
                "type": edge_type,
                "provenance": "HUMAN_CONFIRMED",
            }
        ]

    graph, context, ids = derived("multi", extra)
    receipt = plan(graph, context, "source:" + uid("res", 1))
    bucket = "uncertain_impact" if edge_type == "SEMANTIC" else "definite_impact"
    assert {ids[k] for k in ("action:right", "artifact:right", "view:text:right")} <= set(
        receipt[bucket]
    )
    assert ids["check:receipt.readback.v1"] in receipt[bucket]
    assert ids["manifest:" + graph["app_id"]] in receipt[bucket]


@pytest.mark.parametrize("provenance", ["ACTUAL_READ", "HUMAN_CONFIRMED", "MODEL_CANDIDATE"])
def test_dependency_provenance_not_fabricated_or_treated_as_complete(provenance):
    def extra(candidate, versions, ids, context):
        context["dependency_edges"] = [
            {
                "upstream": ids["action:left"],
                "downstream": ids["action:right"],
                "type": "DATA",
                "provenance": provenance,
            }
        ]

    graph, context, ids = derived("multi", extra)
    receipt = plan(graph, context, "source:" + uid("res", 1))
    assert any(e["provenance"] == provenance for e in graph["edges"])
    expected = "uncertain_impact" if provenance == "MODEL_CANDIDATE" else "definite_impact"
    assert ids["action:right"] in receipt[expected]


@pytest.mark.parametrize("scope", ["APP", "PROJECT"])
def test_unknown_dependencies_expand_without_a_declared_path(scope):
    def extra(candidate, versions, ids, context):
        context["unknown_dependencies"] = [
            {
                "node_id": ids["action:right"],
                "scope": scope,
                "reason": "Dynamic collection membership not bounded",
            }
        ]

    graph, context, ids = derived("multi", extra)
    receipt = plan(graph, context, "source:" + uid("res", 1))
    assert receipt["revalidation_scope"] == scope
    assert set(receipt["revalidation_nodes"]) == set(ids.values())
    assert ids["action:right"] in receipt["uncertain_impact"]
    assert receipt["retained_objects"] == []


def test_manifest_level_change_cannot_claim_packaging_only():
    graph, context, ids = derived("multi")
    receipt = plan(graph, context, "manifest:" + graph["app_id"])
    assert receipt["revalidation_scope"] == "APP"
    assert set(receipt["revalidation_nodes"]) == set(ids.values())
    req = request(graph, "source:" + uid("res", 1))
    req["presentation_only"] = True
    error("INVALID_MANIFEST", lambda: plan_change(graph, graph["graph_fingerprint"], req, context))


def test_view_change_retains_calculation_but_invalidates_check_and_package():
    graph, context, ids = derived("multi")
    receipt = plan(graph, context, "view:text:left")
    assert set(receipt["definite_impact"]) == {
        ids["view:text:left"],
        ids["check:receipt.readback.v1"],
        ids["manifest:" + graph["app_id"]],
    }
    assert {ids["action:left"], ids["artifact:left"]} <= {
        n["id"] for n in receipt["retained_objects"]
    }


@pytest.mark.parametrize(
    "locked_key", ["action:left", "view:text:left", "check:receipt.readback.v1"]
)
def test_affected_lock_refuses_without_mutation(locked_key):
    def lock(candidate, versions, ids, context):
        context["locked_nodes"] = [ids[locked_key]]

    graph, context, ids = derived("multi", lock)
    before = copy.deepcopy((graph, context))
    error("LOCK_CONFLICT", lambda: plan(graph, context, "source:" + uid("res", 1)))
    assert (graph, context) == before


def test_unrelated_lock_preserved_and_unknown_scope_cannot_bypass_it():
    def lock(candidate, versions, ids, context):
        context["locked_nodes"] = [ids["action:right"]]

    graph, context, ids = derived("multi", lock)
    assert any(
        n["id"] == ids["action:right"] and n["locked"]
        for n in plan(graph, context, "source:" + uid("res", 1))["retained_objects"]
    )

    def unknown(candidate, versions, ids, context):
        lock(candidate, versions, ids, context)
        context["unknown_dependencies"] = [
            {"node_id": ids["action:right"], "scope": "PROJECT", "reason": "Unknown reads"}
        ]

    graph, context, _ = derived("multi", unknown)
    error("LOCK_CONFLICT", lambda: plan(graph, context, "source:" + uid("res", 1)))


def test_same_key_same_parameters_reuses_fresh_plan_and_does_not_alias_inputs():
    graph, context, _ = derived("multi")
    req = request(graph, "action:left", "action:right")
    receipt = plan_change(graph, graph["graph_fingerprint"], req, context)
    before = copy.deepcopy(receipt)
    req["changes"].reverse()
    replay = plan_change(graph, graph["graph_fingerprint"], req, context, receipt)
    assert replay == receipt
    replay["definite_impact"].clear()
    assert receipt == before
    different = request(graph, "action:left")
    error(
        "VERSION_CONFLICT",
        lambda: plan_change(graph, graph["graph_fingerprint"], different, context, receipt),
    )
    corrupted = copy.deepcopy(receipt)
    corrupted["retained_objects"] = []
    corrupted["plan_fingerprint"] = digest(
        {k: v for k, v in corrupted.items() if k != "plan_fingerprint"}
    )
    error(
        "VERSION_CONFLICT",
        lambda: plan_change(graph, graph["graph_fingerprint"], req, context, corrupted),
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("revoked", "PERMISSION_DENIED"),
        ("resource", "PERMISSION_DENIED"),
        ("project", "PERMISSION_DENIED"),
        ("app", "PERMISSION_DENIED"),
        ("auth_revision", "PERMISSION_DENIED"),
        ("revision", "VERSION_CONFLICT"),
        ("external_hash", "VERSION_CONFLICT"),
        ("lock", "VERSION_CONFLICT"),
        ("anchor", "VERSION_CONFLICT"),
    ],
)
def test_cached_receipt_revalidates_current_authority_and_versions(case, code):
    graph, context, ids = derived("multi")
    receipt = plan(graph, context, "action:left")
    current = copy.deepcopy(context)
    if case == "revoked":
        current["authorized"] = False
    elif case == "resource":
        current["resource_ids"].clear()
    elif case in {"project", "app"}:
        current[case + "_id"] = uid("proj" if case == "project" else "app", 999)
    elif case == "auth_revision":
        current["authorization_revision"] += 1
    elif case == "revision":
        current["node_revisions"]["action:right"] += 1
    elif case == "external_hash":
        current["source_versions"]["source:" + uid("res", 2)]["content_fingerprint"] = "b" * 64
    elif case == "lock":
        current["locked_nodes"] = [ids["action:right"]]
    else:
        current["graph_fingerprint"] = None
    error(code, lambda: plan(graph, current, "action:left", previous=receipt))


def test_coherent_graph_and_node_rehash_cannot_replace_server_anchor():
    graph, context, _ = derived("multi")
    changed = copy.deepcopy(graph)
    # Manifest is the sink, so rewriting it and all public hashes is coherent.
    node = next(n for n in changed["nodes"] if n["kind"] == "MANIFEST")
    node["definition"]["revision"] = 999
    upstream = {n["id"]: n for n in changed["nodes"]}
    incoming = sorted(
        [
            {
                **e,
                "revision": upstream[e["upstream"]]["revision"],
                "content_fingerprint": upstream[e["upstream"]]["content_fingerprint"],
            }
            for e in changed["edges"]
            if e["downstream"] == node["id"]
        ],
        key=digest,
    )
    node["content_fingerprint"] = digest(
        {
            **{k: v for k, v in node.items() if k != "content_fingerprint"},
            "upstream_versions": incoming,
        }
    )
    changed["graph_fingerprint"] = digest(
        {k: v for k, v in changed.items() if k != "graph_fingerprint"}
    )
    error(
        "VERSION_CONFLICT",
        lambda: plan_change(
            changed, changed["graph_fingerprint"], request(changed, node["key"]), context
        ),
    )


@pytest.mark.parametrize(
    "case", ["graph", "node", "request_revision", "request_hash", "expected_graph"]
)
def test_stale_versions_and_fingerprints(case):
    graph, context, _ = derived()
    req = request(graph, "action:aggregate")
    expected = graph["graph_fingerprint"]
    if case == "graph":
        graph["graph_fingerprint"] = "b" * 64
    elif case == "node":
        graph["nodes"][0]["revision"] += 1
    elif case == "request_revision":
        req["changes"][0]["expected_revision"] += 1
    elif case == "request_hash":
        req["changes"][0]["expected_content_fingerprint"] = "b" * 64
    else:
        expected = "b" * 64
    error("VERSION_CONFLICT", lambda: plan_change(graph, expected, req, context))


@pytest.mark.parametrize(
    "case",
    [
        "context_bool",
        "context_revision",
        "source_revision",
        "node_revision",
        "lock_bool",
        "change_revision",
        "action_revision",
        "manifest_revision",
        "limits",
    ],
)
def test_strict_bool_is_not_a_revision_or_permission(case):
    candidate, limits = fixture()
    versions, ids, context = inputs(candidate)
    if case == "context_bool":
        context["authorized"] = 1
    elif case == "context_revision":
        context["authorization_revision"] = True
    elif case == "source_revision":
        key = next(iter(versions))
        versions[key]["revision"] = True
        context["source_versions"] = copy.deepcopy(versions)
    elif case == "node_revision":
        context["node_revisions"]["action:aggregate"] = True
    elif case == "lock_bool":
        context["locked_nodes"] = [True]
    elif case == "change_revision":
        graph, context, _ = derived()
        req = request(graph, "action:aggregate")
        req["changes"][0]["expected_revision"] = True
        error(
            "INVALID_MANIFEST", lambda: plan_change(graph, graph["graph_fingerprint"], req, context)
        )
        return
    elif case == "action_revision":
        candidate["actions"][0]["revision"] = True
    elif case == "manifest_revision":
        candidate["manifest"]["revision"] = True
    else:
        limits = limits.model_copy(update={"max_tools": True})
    error(
        "INVALID_MANIFEST",
        lambda: derive_manifest_graph(
            candidate["manifest"], candidate["actions"], versions, ids, context, limits
        ),
    )


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_id",
        "unknown_key",
        "missing_id",
        "extra_versions",
        "missing_versions",
        "wrong_snapshot",
        "wrong_revision",
        "duplicate_edge",
        "dangling",
        "cycle",
        "unknown_edge_field",
        "unknown_context_field",
        "unknown_scope",
        "dangling_unknown",
        "duplicate_unknown",
        "too_many_edges",
        "large_json",
    ],
)
def test_closed_mappings_and_graph_structure_negative_cases(case):
    candidate, limits = fixture()
    versions, ids, context = inputs(candidate)
    code = "INVALID_MANIFEST"
    e = {
        "upstream": ids["source:" + uid("res", 1)],
        "downstream": ids["action:aggregate"],
        "type": "DATA",
        "provenance": "ACTUAL_READ",
    }
    if case == "duplicate_id":
        ids["action:aggregate"] = ids["source:" + uid("res", 1)]
    elif case == "unknown_key":
        ids["unexpected"] = uid("dg", 900)
    elif case == "missing_id":
        del ids["action:aggregate"]
    elif case == "extra_versions":
        versions["unused"] = {"revision": 1, "content_fingerprint": "b" * 64}
        context["source_versions"] = copy.deepcopy(versions)
    elif case == "missing_versions":
        del versions["source:" + uid("res", 1)]
        context["source_versions"] = copy.deepcopy(versions)
        code = "VERSION_CONFLICT"
    elif case == "wrong_snapshot":
        versions["source:" + uid("res", 1)]["content_fingerprint"] = "a" * 64
        code = "VERSION_CONFLICT"
    elif case == "wrong_revision":
        context["node_revisions"]["action:aggregate"] = 2
        code = "VERSION_CONFLICT"
    elif case == "duplicate_edge":
        context["dependency_edges"] = [e, e]
    elif case == "dangling":
        e["upstream"] = uid("dg", 999)
        context["dependency_edges"] = [e]
    elif case == "cycle":
        e["upstream"], e["downstream"] = e["downstream"], e["upstream"]
        context["dependency_edges"] = [e]
    elif case == "unknown_edge_field":
        e["trusted"] = True
        context["dependency_edges"] = [e]
    elif case == "unknown_context_field":
        context["self_authorize"] = True
    elif case in {"unknown_scope", "dangling_unknown", "duplicate_unknown"}:
        unknown = {"node_id": ids["action:aggregate"], "scope": "APP", "reason": "unknown"}
        if case == "unknown_scope":
            unknown["scope"] = "GLOBAL"
        elif case == "dangling_unknown":
            unknown["node_id"] = uid("dg", 999)
        context["unknown_dependencies"] = [unknown] * (2 if case == "duplicate_unknown" else 1)
    elif case == "too_many_edges":
        context["dependency_edges"] = [e] * 513
    else:
        candidate["manifest"]["garbage"] = "x" * 262145
    error(
        code,
        lambda: derive_manifest_graph(
            candidate["manifest"], candidate["actions"], versions, ids, context, limits
        ),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("manifest", None),
        ("manifest", []),
        ("manifest", 7),
        ("actions", None),
        ("actions", 7),
        ("actions", []),
        ("actions", [None]),
    ],
)
def test_malformed_container_has_domain_error(field, value):
    candidate, limits = fixture()
    versions, ids, context = inputs(candidate)
    candidate[field] = value
    error(
        "INVALID_MANIFEST",
        lambda: derive_manifest_graph(
            candidate["manifest"], candidate["actions"], versions, ids, context, limits
        ),
    )


def test_additional_check_dependency_and_unused_locked_resource_are_not_silently_lost():
    candidate, limits = fixture()
    extra_ref = "source.literal_evidence.v1"
    candidate["actions"][0]["dependencies"].append(
        {"kind": "check", "ref": extra_ref, "version": "1"}
    )
    candidate["manifest"]["dependency_lock"].extend(
        [
            {"kind": "check", "ref": extra_ref, "version": "1"},
            {"kind": "resource", "ref": uid("res", 3), "version": "1"},
        ]
    )
    versions, ids, context = inputs(candidate)
    graph = derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )
    context["graph_fingerprint"] = graph["graph_fingerprint"]
    receipt = plan(graph, context, "rule:check:" + extra_ref)
    assert ids["action:aggregate"] in receipt["definite_impact"]
    assert ids["check:" + extra_ref] in receipt["revalidation_checks"]
    assert uid("res", 3) in graph["resource_ids"]
    versions.pop("rule:check:" + extra_ref)
    context["source_versions"] = copy.deepcopy(versions)
    error(
        "VERSION_CONFLICT",
        lambda: derive_manifest_graph(
            candidate["manifest"], candidate["actions"], versions, ids, context, limits
        ),
    )


def test_upstream_content_revisions_change_fingerprints_not_stable_ids():
    candidate, limits = fixture("multi")
    versions, ids, context = inputs(candidate)
    first = derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )
    key = "source:" + uid("res", 1)
    versions[key] = {"revision": 2, "content_fingerprint": "b" * 64}
    context["source_versions"] = copy.deepcopy(versions)
    context["node_revisions"][key] = 2
    second = derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )
    a, b = ({n["key"]: n for n in graph["nodes"]} for graph in (first, second))
    affected = {
        key,
        "action:left",
        "artifact:left",
        "view:text:left",
        "check:receipt.readback.v1",
        "manifest:" + first["app_id"],
    }
    for key in a:
        assert a[key]["id"] == b[key]["id"]
        assert (a[key]["content_fingerprint"] != b[key]["content_fingerprint"]) == (key in affected)
        if key not in affected:
            assert a[key] == b[key]


@pytest.mark.parametrize(
    "case", ["empty", "duplicate", "unknown_field", "missing_node", "cross_project"]
)
def test_request_rejects_invalid_scope_or_structure(case):
    graph, context, _ = derived()
    req = request(graph, "action:aggregate")
    code = "INVALID_MANIFEST"
    if case == "empty":
        req["changes"] = []
    elif case == "duplicate":
        req["changes"] *= 2
    elif case == "unknown_field":
        req["changes"][0]["impact"] = "presentation_only"
    elif case == "missing_node":
        req["changes"][0]["node_id"] = uid("dg", 999)
        code = "VERSION_CONFLICT"
    else:
        req["project_id"] = uid("proj", 999)
        code = "PERMISSION_DENIED"
    error(code, lambda: plan_change(graph, graph["graph_fingerprint"], req, context))


def test_manifest_suite_requires_explicit_checker_version_lock():
    candidate, limits = fixture()
    candidate["manifest"]["validation_suite_ref"] = "source.literal_evidence.v1"
    versions, ids, context = inputs(candidate)
    error(
        "INVALID_MANIFEST",
        lambda: derive_manifest_graph(
            candidate["manifest"], candidate["actions"], versions, ids, context, limits
        ),
    )


@pytest.mark.parametrize("field", ["context_nodes", "graph_nodes", "graph_edges"])
def test_node_and_edge_scale_limits(field):
    candidate, limits = fixture()
    versions, ids, context = inputs(candidate)
    if field == "context_nodes":
        context["node_revisions"] = {"node" + str(i): 1 for i in range(129)}
        error(
            "INVALID_MANIFEST",
            lambda: derive_manifest_graph(
                candidate["manifest"], candidate["actions"], versions, ids, context, limits
            ),
        )
    else:
        graph, current, _ = derived()
        req = request(graph, "action:aggregate")
        if field == "graph_nodes":
            graph["nodes"] = [graph["nodes"][0]] * 129
        else:
            graph["edges"] = [graph["edges"][0]] * 513
        error(
            "INVALID_MANIFEST", lambda: plan_change(graph, graph["graph_fingerprint"], req, current)
        )


def test_view_with_optional_unproduced_output_is_rejected_safely():
    candidate, limits = fixture()
    m = candidate["manifest"]
    m["output_schema"] = {
        "type": "object",
        "properties": {"sum": {"type": "string"}, "optional": {"type": "string"}},
        "required": ["sum"],
        "additionalProperties": False,
    }
    m["outputs"] = {"sum": m["outputs"]["sum"]}
    m["views"] = [{"component_ref": "text", "output_field": "optional"}]
    versions, ids, context = inputs(candidate)
    error(
        "INVALID_MANIFEST",
        lambda: derive_manifest_graph(m, candidate["actions"], versions, ids, context, limits),
    )


def test_duplicate_logical_view_identity_is_rejected():
    candidate, limits = fixture()
    candidate["manifest"]["views"] *= 2
    versions, ids, context = inputs(candidate)
    error(
        "INVALID_MANIFEST",
        lambda: derive_manifest_graph(
            candidate["manifest"], candidate["actions"], versions, ids, context, limits
        ),
    )

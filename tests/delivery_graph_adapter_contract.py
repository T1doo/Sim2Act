"""Executable black-box contract for a DeliveryGraph service adapter.

The factory returns an isolated synthetic test driver, not client authority.
Drivers map public plan requests/replies to an actual service and expose fixture
controls separately. This runner never supplies trusted context or prior receipt
in a normal client request. No database/network implementation lives here.

Run: python tests/delivery_graph_adapter_contract.py --driver MODULE:FACTORY
A passing reference double verifies this contract runner, not the product API.
"""

import argparse
import copy
import hashlib
import importlib
import json
import re


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def _ok(reply, driver):
    assert reply["status"] == 200, "Expected authorized plan"
    data = reply["data"]
    assert set(data) == {"core", "expansion", "outer_fingerprint"}, "Closed outer receipt"
    core = data["core"]
    assert core["schema_version"] == "delivery-change-plan.v1", "Core schema binding"
    public = copy.deepcopy(driver.info["request"])
    anchor = public.pop("expected_graph_fingerprint")
    public["changes"] = sorted(public["changes"], key=lambda c: c["node_id"])
    assert core["graph_fingerprint"] == anchor, "Saved graph anchor binding"
    assert core["request_key"] == public["request_key"], "Request key binding"
    assert core["request_fingerprint"] == _digest(public), "Request parameter binding"
    assert core["plan_fingerprint"] == _digest(
        {k: v for k, v in core.items() if k != "plan_fingerprint"}
    ), "Core receipt seal"
    expansion = data["expansion"]
    assert set(expansion) == {"scope", "applications", "snapshot_fingerprint"}
    assert expansion["scope"] == core["revalidation_scope"], "Expansion scope binding"
    records = expansion["applications"]
    assert isinstance(records, list) and records, "Expansion application snapshot"
    assert records == sorted(records, key=lambda a: a["app_id"]), "Canonical application order"
    assert len({a["app_id"] for a in records}) == len(records), "Duplicate application"
    assert driver.info["app_id"] in {a["app_id"] for a in records}, "Target omitted"
    for app in records:
        assert set(app) == {
            "project_id",
            "app_id",
            "graph_fingerprint",
            "authorization_revision",
            "locked_nodes",
        }
        assert app["project_id"] == driver.info["project_id"], "Expansion project binding"
        assert re.fullmatch(r"app_[a-f0-9]{32}", app["app_id"]), "Strict app identity"
        assert re.fullmatch(r"[a-f0-9]{64}", app["graph_fingerprint"]), "Graph seal"
        assert type(app["authorization_revision"]) is int and app["authorization_revision"] > 0
        assert isinstance(app["locked_nodes"], list), "Lock snapshot"
        if app["app_id"] == driver.info["app_id"]:
            assert app["graph_fingerprint"] == anchor, "Target expansion anchor"
    assert expansion["snapshot_fingerprint"] == _digest(records), "Expansion snapshot seal"
    assert data["outer_fingerprint"] == _digest(
        {k: v for k, v in data.items() if k != "outer_fingerprint"}
    ), "Outer receipt seal"
    assert core["project_id"] == driver.info["project_id"], "Response project binding"
    assert core["app_id"] == driver.info["app_id"], "Response app binding"
    assert core["patch_executed"] is False, "Plan must not execute patch"
    assert core["business_write_performed"] is False, "Plan must not write business data"
    assert core["publishable"] is False, "Plan must not authorize publication"
    return data


def _denied(driver, body, codes):
    before = copy.deepcopy(driver.observe())
    reply = driver.plan(body)
    assert reply["status"] in {400, 403, 409}, "Rejected operation must not return cached success"
    assert reply["error"] in codes, "Wrong public error contract"
    assert "data" not in reply, "Denied operation leaked plan/expansion data"
    assert driver.observe() == before, (
        "Rejected operation partially saved receipt or changed domain"
    )


def _first(driver):
    before = copy.deepcopy(driver.observe())
    reply = driver.plan(copy.deepcopy(driver.info["request"]))
    _ok(reply, driver)
    after = copy.deepcopy(driver.observe())
    assert after["domain_fingerprint"] == before["domain_fingerprint"], "Planning changed domain"
    assert after["receipt_count"] == before["receipt_count"] + 1, (
        "First plan not atomically persisted"
    )
    assert after["ledger_fingerprint"] != before["ledger_fingerprint"], "Receipt not saved"
    return reply


def _replay(driver):
    first = _first(driver)
    before = copy.deepcopy(driver.observe())
    cold = driver.cold()
    try:
        replay = cold.plan(copy.deepcopy(driver.info["request"]))
        _ok(replay, cold)
        assert replay == first, "Cold replay changed persisted receipt"
        assert cold.observe() == before, "Replay added receipt or changed domain"
    finally:
        cold.close()


def _transition_replay(driver, event, codes):
    _first(driver)
    driver.transition(event)
    _denied(driver, copy.deepcopy(driver.info["request"]), codes)


def _changed_parameters(driver):
    _first(driver)
    body = copy.deepcopy(driver.info["request"])
    body["changes"] = copy.deepcopy(driver.info["alternate_changes"])
    _denied(driver, body, {"VERSION_CONFLICT"})


def _project_switch(driver):
    _first(driver)
    body = copy.deepcopy(driver.info["request"])
    body["project_id"] = driver.info["foreign_project_id"]
    _denied(driver, body, {"PERMISSION_DENIED"})
    # Switching back must not let the denied request poison the scoped ledger.
    before = copy.deepcopy(driver.observe())
    _ok(driver.plan(copy.deepcopy(driver.info["request"])), driver)
    assert driver.observe() == before, "Project switch contaminated request-key namespace"


def _injected_authority(driver):
    _first(driver)
    driver.transition("revoke_primary")
    body = copy.deepcopy(driver.info["request"])
    body["current_context"] = {"authorized": True}
    body["previous_receipt"] = {"status": "PASS"}
    _denied(driver, body, {"INVALID_MANIFEST", "PERMISSION_DENIED"})


def _expanded_project(driver):
    reply = _first(driver)
    data = _ok(reply, driver)
    assert data["core"]["revalidation_scope"] == "PROJECT", "Expected project expansion"
    expansion = data["expansion"]
    assert expansion["scope"] == "PROJECT", "Project scope downgraded"
    applications = expansion["applications"]
    assert {a["app_id"] for a in applications} == {
        driver.info["app_id"],
        driver.info["related_app_id"],
    }, "Project expansion omitted related app or leaked foreign app"
    assert all(a["project_id"] == driver.info["project_id"] for a in applications), (
        "Cross-project expansion"
    )
    assert all(len(a["graph_fingerprint"]) == 64 for a in applications), (
        "Expansion lacks saved graph anchors"
    )
    assert len(expansion["snapshot_fingerprint"]) == 64, "Expansion snapshot not frozen"


def _initial_lock(driver):
    _denied(driver, copy.deepcopy(driver.info["request"]), {"LOCK_CONFLICT"})


def check_selection_response(request, reply, selected_project_id, selected_app_id):
    """Independent UI oracle; call only after normalizing an actual UI response.

    A server may validly finish an old authorized request after navigation. Its
    payload must not populate another selected project's canvas. This predicate
    alone is not evidence that the product UI enforces it.
    """
    if not isinstance(request, dict) or not isinstance(reply, dict) or reply.get("status") != 200:
        return False
    data = reply.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("core"), dict):
        return False
    core = data["core"]
    for key, selected, pattern in (
        ("project_id", selected_project_id, r"proj_[a-f0-9]{32}"),
        ("app_id", selected_app_id, r"app_[a-f0-9]{32}"),
    ):
        if not isinstance(selected, str) or not re.fullmatch(pattern, selected):
            return False
        if request.get(key) != selected or core.get(key) != selected:
            return False
    return True


CASES = [
    ("cold_scoped_replay", "normal", _replay),
    ("same_key_different_parameters", "normal", _changed_parameters),
    ("project_switch_same_key", "normal", _project_switch),
    ("client_authority_injection_after_revoke", "normal", _injected_authority),
    (
        "primary_revoke_before_replay",
        "normal",
        lambda d: _transition_replay(d, "revoke_primary", {"PERMISSION_DENIED"}),
    ),
    (
        "primary_version_before_replay",
        "normal",
        lambda d: _transition_replay(d, "bump_primary", {"VERSION_CONFLICT"}),
    ),
    ("target_initial_lock", "target_locked", _initial_lock),
    ("project_expansion_targets", "project", _expanded_project),
    ("related_initial_lock_no_partial_receipt", "project_locked", _initial_lock),
    (
        "related_revoke_before_replay",
        "project",
        lambda d: _transition_replay(d, "revoke_related", {"PERMISSION_DENIED"}),
    ),
    (
        "related_version_before_replay",
        "project",
        lambda d: _transition_replay(d, "bump_related", {"VERSION_CONFLICT"}),
    ),
    (
        "related_membership_before_replay",
        "project",
        lambda d: _transition_replay(d, "add_related", {"VERSION_CONFLICT"}),
    ),
    (
        "related_lock_before_replay",
        "project",
        lambda d: _transition_replay(d, "lock_related", {"LOCK_CONFLICT", "VERSION_CONFLICT"}),
    ),
    (
        "outer_receipt_tamper",
        "project",
        lambda d: _transition_replay(d, "tamper_outer_receipt", {"VERSION_CONFLICT"}),
    ),
    (
        "stored_core_receipt_type_tamper",
        "normal",
        lambda d: _transition_replay(d, "tamper_core_receipt_types", {"VERSION_CONFLICT"}),
    ),
    (
        "stored_outer_receipt_type_tamper",
        "project",
        lambda d: _transition_replay(d, "tamper_outer_receipt_types", {"VERSION_CONFLICT"}),
    ),
    (
        "stored_graph_boolean_revision",
        "normal",
        lambda d: _transition_replay(
            d, "tamper_graph_revision", {"INVALID_MANIFEST", "VERSION_CONFLICT"}
        ),
    ),
]


def run_contract(factory, case_names=None):
    """Return individual results; any failed obligation blocks integration."""
    selected = set(case_names) if case_names is not None else {name for name, _, _ in CASES}
    if selected - {name for name, _, _ in CASES}:
        raise ValueError("Unknown contract case")
    results = []
    for name, scenario, check in CASES:
        if name not in selected:
            continue
        driver = None
        try:
            driver = factory(scenario)
            check(driver)
            results.append({"case": name, "status": "PASS"})
        except Exception as exc:
            # Do not print exception text: real adapters may carry credentials.
            results.append({"case": name, "status": "FAIL", "error_type": type(exc).__name__})
        finally:
            if driver is not None:
                try:
                    driver.close()
                except Exception:
                    results.append({"case": name + ":cleanup", "status": "FAIL"})
    return {
        "contract": "delivery-graph-adapter-contract.v1",
        "results": results,
        "driver": factory.__module__ + ":" + factory.__name__,
        "product_acceptance": "NOT_IMPLIED",
        "status": "PASS" if results and all(r["status"] == "PASS" for r in results) else "FAIL",
        "limits": "Only the supplied driver was checked. No product/Windows/publication verdict is implied.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--driver", required=True, help="Trusted local synthetic fixture factory MODULE:NAME"
    )
    args = parser.parse_args()
    try:
        module, name = args.driver.split(":", 1)
        factory = getattr(importlib.import_module(module), name)
        report = run_contract(factory)
    except Exception as exc:
        report = {
            "contract": "delivery-graph-adapter-contract.v1",
            "status": "FAIL",
            "product_acceptance": "NOT_IMPLIED",
            "error_type": type(exc).__name__,
        }
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

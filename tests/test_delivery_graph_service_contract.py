"""Real-service contract failures remain failing integration gates, never xfail."""

import copy

import pytest
from delivery_graph_adapter_contract import CASES, run_contract
from delivery_graph_service_contract_driver import factory


@pytest.mark.parametrize("case", [name for name, _, _ in CASES])
def test_actual_service_blackbox_contract(case):
    result = run_contract(factory, [case])
    assert result["status"] == "PASS", result


def test_actual_http_and_cold_store_keep_full_database_and_authority():
    driver = factory("normal")
    cold = None
    try:
        before = driver.observe()
        response = driver.plan(copy.deepcopy(driver.info["request"]))
        assert response["status"] == 200
        # Raw real response is intentionally not a manufactured contract envelope.
        assert "receipt" in response["data"]
        after = driver.observe()
        assert after["receipt_count"] == before["receipt_count"] + 1
        assert after["domain_fingerprint"] == before["domain_fingerprint"]
        assert after["authority_fingerprint"] == before["authority_fingerprint"]
        cold = driver.cold()
        assert cold.store is not driver.store and cold.client is not driver.client
        replay = cold.plan(copy.deepcopy(driver.info["request"]))
        assert replay["status"] == 200 and replay["data"]["cached"] is True
        assert cold.observe() == after
        driver.transition("revoke_primary")
        revoked = driver.observe()
        denied = cold.plan(copy.deepcopy(driver.info["request"]))
        assert denied["status"] == 403 and "data" not in denied
        assert cold.observe() == revoked
    finally:
        if cold is not None:
            cold.close()
        driver.close()

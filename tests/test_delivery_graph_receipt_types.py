"""Historical JSON receipts must preserve scalar types as well as values."""

import copy

import pytest
from test_delivery_graph import fixture, inputs, request

from sim2act.delivery_graph import derive_manifest_graph, plan_change
from sim2act.errors import DomainError


@pytest.mark.parametrize(
    "mutation", ["flag_zero", "retained_revision_bool", "retained_revision_float"]
)
def test_historical_receipt_rejects_python_equal_json_type_substitution(mutation):
    candidate, limits = fixture("multi")
    versions, ids, context = inputs(candidate)
    graph = derive_manifest_graph(
        candidate["manifest"], candidate["actions"], versions, ids, context, limits
    )
    context["graph_fingerprint"] = graph["graph_fingerprint"]
    body = request(graph, "action:left")
    receipt = plan_change(graph, graph["graph_fingerprint"], body, context)
    altered = copy.deepcopy(receipt)
    if mutation == "flag_zero":
        altered["patch_executed"] = 0
    else:
        assert altered["retained_objects"]
        assert altered["retained_objects"][0]["revision"] == 1
        altered["retained_objects"][0]["revision"] = (
            True if mutation == "retained_revision_bool" else 1.0
        )
    assert altered == receipt  # Demonstrates the unsafe old Python comparison.
    with pytest.raises(DomainError) as rejected:
        plan_change(graph, graph["graph_fingerprint"], body, context, altered)
    assert rejected.value.code == "VERSION_CONFLICT"
    assert plan_change(graph, graph["graph_fingerprint"], body, context, receipt) == receipt

"""Result metadata must not report an assumed real-provider request count."""

from sim2act import natural_specs as natural
from sim2act.pa_spec_apps import result_ref


def test_live_reference_omits_unknown_real_count_and_mock_is_unchanged():
    binding = dict(run_mode="mock", snapshot=dict(app_run_id="app-run", instance_id="instance",
        release_id="release"), plan=dict(plan_fingerprint="plan"), draft=dict(candidate=dict(
            namespace=natural.VERSION, actions=[dict(executor=dict(ref=operator)) for operator in
                ("resource.read", "model.spec.requirements", "model.spec.qualifiers", "artifact.save_text")])))
    proved = [dict(operation_id="operation-1"), dict(operation_id="operation-2")]
    expected = dict(namespace=natural.VERSION, app_run_id="app-run", instance_id="instance",
        release_id="release", result_version=2, plan_fingerprint="plan",
        receipt_refs=["operation-1", "operation-2"], model_requests=2,
        real_model_requests=0, citation_status="PASS", semantic_status="UNKNOWN",
        semantic_goal_acceptance="NOT_RUN", formal_publication_enabled=False)
    assert result_ref(binding, proved, 2) == expected
    live = result_ref({**binding, "run_mode": "live"}, proved, 2)
    assert live == {key: value for key, value in expected.items() if key != "real_model_requests"}
    assert live["model_requests"] == 2 and "real_model_requests" not in live

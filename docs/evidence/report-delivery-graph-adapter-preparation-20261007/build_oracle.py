"""Hand-authored oracle, intentionally independent of delivery_graph implementation."""
import json
from pathlib import Path
p = Path(__file__).parent
f = json.loads((p / "canonical-report-fixture.json").read_text())
i = f["ids"]
nodes = [(k, t) for k, t in [("goal", "GOAL"), ("source", "SOURCE"), ("target", "SOURCE"),
          ("action", "ACTION"), ("view", "VIEW"), ("check", "CHECK"), ("app", "MANIFEST")]]
edges = [
    ("goal", "action", "RULE", "compiler_declared"),
    ("source", "action", "RULE", "compiler_declared"),
    ("target", "action", "DATA", "compiler_declared"),
    ("action", "view", "PRESENTATION", "compiler_declared"),
    ("action", "check", "VERIFIED_BY", "compiler_declared"),
    ("source", "check", "VERIFIED_BY", "compiler_declared"),
    ("target", "check", "VERIFIED_BY", "compiler_declared"),
    ("goal", "app", "PACKAGED_IN", "compiler_declared"),
    ("source", "app", "PACKAGED_IN", "compiler_declared"),
    ("target", "app", "PACKAGED_IN", "compiler_declared"),
    ("action", "app", "PACKAGED_IN", "compiler_declared"),
    ("view", "app", "PACKAGED_IN", "compiler_declared"),
    ("check", "app", "PACKAGED_IN", "compiler_declared"),
]
cases = [
    dict(id="source-content-change", changed=["source"], definitely_affected=["source", "action", "view", "check", "app"], preserved=["target", "goal"], reason="source is a current sealed-origin prerequisite even though cold executor reads target only"),
    dict(id="target-content-change", changed=["target"], definitely_affected=["target", "action", "view", "check", "app"], preserved=["source", "goal"], reason="new cold read and proof hash must be rebound before any execution"),
    dict(id="equal-hash-distinct-identities", changed=["source"], definitely_affected=["source", "action", "view", "check", "app"], preserved=["target", "goal"], reason="identity, authority and origin role differ; equal source/target hash is not an identity merge"),
    dict(id="action-content-change", changed=["action"], definitely_affected=["action", "view", "check", "app"], preserved=["source", "target", "goal"], reason="wiring/schema/tool/budget changes reach output and its validation/packaging"),
    dict(id="known-view-presentation-change", changed=["view"], definitely_affected=["view", "app"], preserved=["source", "target", "goal", "action", "check"], reason="hand graph check validates Report output, not view rendering; root may require an additional presentation check without relabeling Report check"),
    dict(id="check-contract-change", changed=["check"], definitely_affected=["check", "app"], preserved=["source", "target", "goal", "action", "view"], reason="old check cannot prove new contract; preserved calculations do not imply acceptance"),
    dict(id="unknown-semantic-edge", changed=["target"], definitely_affected=["target", "action", "view", "check", "app"], preserved=["source", "goal"], uncertainty_scope="associated app; project if dependency set cannot be bounded", reason="explanation and dependency completeness are not certified by finite Report check"),
]
for c in cases:
    for key in ("changed", "definitely_affected", "preserved"):
        c[key] = [i[k] for k in c[key]]
value = dict(kind="manual-report-delivery-oracle.v1", synthetic=True, implementation_executed=False,
    graph_role="manually drawn minimum, not serialized delivery_graph output or normative adapter schema",
    nodes=[dict(id=i[k], type=t, revision=1, status="DRAFT", human_locked=False) for k,t in nodes],
    edges=[dict(upstream=i[a], downstream=i[b], type=t, provenance=prov) for a,b,t,prov in edges],
    actual_read_evidence=dict(status="NOT_OBSERVED", records=[],
        declared_resources=[i["source"],i["target"]],
        cold_expected_tool="resource.read", cold_expected_only_resource=i["target"],
        forbidden_inferences=["permissions imply actual read", "source predecessor read equals current cold read", "equal hash merges source nodes", "no observed extra read proves exhaustive semantics"]),
    cases=cases,
    rejection_oracles=[dict(id=k, expected=e, zero_mutation=True) for k,e in [
        ("wrong-project", "PERMISSION_DENIED"), ("source-revoked", "PERMISSION_DENIED"),
        ("target-revoked", "PERMISSION_DENIED"), ("coherent-rehash-origin-plan", "VERSION_CONFLICT"),
        ("stale-run-completion-fence-version", "VERSION_CONFLICT"),
        ("coherent-rehash-check-record-without-anchor", "VERSION_CONFLICT"),
        ("bool-resource-revision", "INVALID_INPUT_OR_TYPED_VERSION_CONFLICT_BY_FINAL_CONTRACT"),
        ("changed-upstream-reaches-human-lock", "LOCK_CONFLICT"),
        ("same-key-different-body", "VERSION_CONFLICT")]],
    acceptance=dict(state="PREVIEW_ONLY", semantic="UNKNOWN", owner="PENDING", release="UNSUPPORTED",
                    history_retained=True, plan_executes_changes=False, model_calls=0, database_calls=0, network_calls=0))
value["uncertainty_variants"] = [{'additional_edge': {'downstream': 'action_44444444444444444444444444444444', 'provenance': 'model_candidate', 'type': 'SEMANTIC', 'upstream': 'res_55555555555555555555555555555555'}, 'id': 'model-candidate-semantic-association', 'must_not': 'automatically accept semantic completeness', 'required_behavior': 'associated app revalidation uncertainty remains; model edge is not exhaustive evidence'}, {'id': 'resource-set-membership-changed', 'must_not': 'treat only already-read resource identities as complete query dependency', 'required_behavior': 'widen validation without automatically rewriting every node', 'trusted_adapter_event': 'authorized resource collection fingerprint changed', 'uncertainty_scope': 'associated app, or project when dependency membership cannot be bounded'}]
(p/"manual-dependency-impact-oracle.json").write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+"\n")

"""Pure canonical/preflight fixture construction; never opens a Store or model."""
import json
from pathlib import Path
from sim2act.conditional_checks import SOURCE_HASH
from sim2act.contracts import Limits
from sim2act.db import fingerprint
from sim2act.report_manifest_apps import canonical, compile_report

out = Path(__file__).parent
ids = {"project": "proj_" + "1" * 32, "app": "app_" + "2" * 32,
       "named": "app_" + "3" * 32, "action": "action_" + "4" * 32,
       "source": "res_" + "5" * 32, "target": "res_" + "6" * 32,
       "source_run": "run_" + "7" * 32, "extract_run": "run_" + "8" * 32,
       "goal": "goal_" + "9" * 32, "runtime": "runtime_" + "a" * 32,
       "view": "report-fixture.view.decision.v1", "check": "report-fixture.check.conditional.v1"}
limits = Limits(max_requests=4, max_tools=4, max_repairs=1, max_total_tokens=64000,
                max_output_tokens=1024, run_seconds=300)
proof = dict(named_app_id=ids["named"], expected_named_fingerprint="b" * 64,
             extraction_run_id=ids["extract_run"], expected_plan_fingerprint="c" * 64,
             expected_check_fingerprint="d" * 64, source_run_id=ids["source_run"],
             source_resource_id=ids["source"], target_resource_id=ids["target"],
             expected_target_hash=SOURCE_HASH, runtime_id=ids["runtime"], limits=limits.model_dump())
candidate = canonical(ids["app"], ids["action"], ids["goal"], proof)
manifest, action, compiled = compile_report(candidate, limits)
fixture = dict(kind="report-delivery-adapter-fixture.v1", synthetic=True,
               persisted_proof=False, runtime_observations_verified=False,
               origin="actual canonical() and compile_report() pure functions", ids=ids,
               candidate=candidate, candidate_fingerprint=fingerprint(candidate),
               canonical_manifest_fingerprint=fingerprint(manifest.model_dump()),
               canonical_action_fingerprint=fingerprint(action.model_dump()),
               platform_limits=limits.model_dump(), preflight=compiled,
               source_versions=[dict(resource_id=ids[k], content_hash=SOURCE_HASH, revision=1,
                   revision_authority="SYNTHETIC_ORACLE_ONLY; DB has no resource revision column",
                   project_id=ids["project"], declared=True,
                   cold_actual_read_required=k == "target") for k in ("source", "target")],
               stable_ids=dict(views={"0": ids["view"]}, checks={"source.conditional_report.v1": ids["check"]}),
               adapter_context=dict(project_id=ids["project"], app_id=ids["app"],
                   runtime_mode="user_and_project_intersection",
                   current_authorized_resource_refs=[ids["source"], ids["target"]],
                   semantic_status="UNKNOWN", owner_acceptance="PENDING", state="PREVIEW_ONLY"))
(out / "canonical-report-fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
print(json.dumps(dict(status="PURE_PREFLIGHT_PASS", candidate_fingerprint=fingerprint(candidate), database_calls=0, model_calls=0, network_calls=0)))

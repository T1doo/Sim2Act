import hashlib
import json
from pathlib import Path
root = Path('/workspace/Sim2Act-bounded-product-candidate')
out = Path(__file__).parent
locations = [
 ('Report canonical', 'src/sim2act/report_manifest_apps.py', 75, 'two resource IDs in permissions/dependencies; target only data binding; fixed action and single decision view'),
 ('Report common compile', 'src/sim2act/report_manifest_apps.py', 155, 'strict preflight + canonical fingerprint reconstruction; use this before graph derivation'),
 ('Report load', 'src/sim2act/report_manifest_apps.py', 200, 'independent task_extractions/candidate markers + parent/source/check/plan/current authority gate; raw app_drafts alone is insufficient'),
 ('named anchors', 'src/sim2act/conditional_apps.py', 48, 'current target hash/format and source completion/check revalidation; source/target grants stay distinct'),
 ('check anchor', 'src/sim2act/conditional_runs.py', 321, 'check_id and independent event anchor, current result/version/fence and finite check reexecution'),
 ('source completion', 'src/sim2act/conditional_runs.py', 367, 'result fingerprint + check fingerprint source proof'),
 ('protocol current seals', 'src/sim2act/protocol_jobs.py', 137, 'current owner/project/runtime authorization and accepted snapshot/current run gate'),
 ('actual read seals', 'src/sim2act/protocol_jobs.py', 272, 'actual operation_intents/operation args, tool_ref/status/receipt hashes and immutable completion operation seals; scope by exact run/phase'),
 ('Attempt seals', 'src/sim2act/protocol_jobs.py', 258, 'safe response/model/usage/identity/parameters bind current persisted Attempt; never export private reasoning/wire'),
 ('Report history', 'src/sim2act/report_manifest_apps.py', 457, 'marker input/key/AppFP and actual Run request key/project/principal/runtime/phase/payload/limits are rechecked'),
 ('resources physical', 'src/sim2act/db.py', 45, 'ID/project/content/hash/format, no revision column'),
 ('apps physical', 'src/sim2act/db.py', 195, 'candidate/fingerprint/runtime/name, no durable mutable App revision field beyond canonical manifest/action revision'),
 ('view schema', 'src/sim2act/contracts.py', 76, 'component_ref and output_field only; no stored view ID/revision'),
 ('Run versions', 'src/sim2act/db.py', 67, 'version and fence are Run concurrency identities, not resource/view revisions'),
 ('accepted ResourceSnapshot', 'src/sim2act/protocol_jobs.py', 680, 'snapshot revision=1 is server-created accepted snapshot value, not current resource mutation sequence'),
 ('retirement mutation', 'src/sim2act/local_tasks.py', 457, 'resource content/format may change without resource revision column; hash alone does not cover every current status/format change'),
]
evidence = dict(kind='report-delivery-adapter-evidence.v1', observed_source='2cad13afa72e8df6be1aa9c765e4c94586ad0532',
 source_locations=[dict(subject=a,path=b,line=c,evidence=d,source_sha256=hashlib.sha256((root/b).read_bytes()).hexdigest()) for a,b,c,d in locations],
 proposed_adapter_steps=[
  'Current identity + explicit current project/app scope first, then report_manifest_apps.load within trusted transaction; no user-supplied context authorization.',
  'Feed actual validated canonical manifest/actions to shared derive_manifest_graph; add proof origin refs as trusted prerequisite dependencies, not invented executable nodes.',
  'Resolve current source/target authority separately for user and existing runtime via existing intersection gates; carry exact authorized resource IDs and current bytes/hash/format state.',
  'Freeze named fp, independent extraction candidate fp/plan fp/source result fp/check record fp+anchor, actual completed fence/version and accepted contract/limits as audit anchors in server adapter receipt.',
  'Stable logical view/check slots must be assigned by server and reused across content versions; actual check_id is an execution evidence ID, not a new logical graph check each run.',
  'Actual reads must be sourced only from validated completion seals and operation intents for exact current cold Run; predecessor source Run observations are labeled origin stage.',
  'Unknown explanation/dependency completeness stays associated-app uncertainty; graph discovery does not automatically mark bounded Report semantic accepted.',
  'Plan receipt persistence and current version/authorization reread must precede any claim of durable same-key recovery; derive/plan pure module alone supplies no storage.'
 ],
 unresolved_interfaces=[
  dict(name='current source revision authority', evidence='resources has no revision; accepted snapshots hardcode 1', requirement='server version registry or explicitly immutable captured source version with current content/hash/format/status recheck; do not silently substitute hash for revision or accept client revision'),
  dict(name='stable view/check logical IDs', evidence='View schema lacks IDs; check events are per-execution IDs', requirement='explicit server slot-ID mapping and its persistence/reuse contract; fixed one-view Report can use trusted app+decision slot but not changing content hash'),
  dict(name='graph baseline/receipt storage', evidence='no DeliveryGraph persistent integration inspected/implemented here', requirement='root adapter determines namespace/persistence/current expected graph versions; no claim of restart idempotency from manual fixtures'),
  dict(name='Report compatibility on independent e700 branch', evidence='e700 predates bounded_report executor and nullable Scenario/common compile', requirement='normal root integration must bring compatible contracts/preflight/Report source before consuming fixture; do not loosen generic unknown executor/schema checks')
 ],
 boundaries=dict(main_entry_implemented=False, graph_module_executed=False, database_calls=0, model_calls=0, network_calls=0, new_authority=False, semantic_status='UNKNOWN', owner_acceptance='PENDING', scope='read-only offline preparation'))
(out/'adapter-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
files = [p for p in out.iterdir() if p.is_file() and p.name != 'manifest.json']
manifest = dict(kind='report-delivery-preparation-manifest.v1', files=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted(files)])
(out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')

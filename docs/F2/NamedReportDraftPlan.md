# Named persistent bounded Report drafts — isolated proposal and implementation scope

Base: fcea3fdf9ce56dccd3515062f9113a75f6cf686a. Branch: bounded-named-report-draft.
This slice is separate from the frozen CI candidate. PREVIEW_ONLY; formal publication disabled;
source overall NOT_ACCEPTED, semantic UNKNOWN, owner PENDING. It is not AppManifest compatibility.

User flow: technically checked source → sealed finite extraction → name and save a fixed rules-bound
Report draft → fresh page list/open → type a new Scenario → asynchronous actual cold Run → refresh
its actual receipt/history. Saving does not enable a provider or evaluate a Scenario.

## Closed interfaces and authority

Project-bound /conditional-apps POST accepts extraction_run_id, expected_plan_fingerprint,
expected_check_fingerprint, target_resource_id, expected_target_hash, name, request_key only.
List/read/history are read-only. POST /{aid}/runs accepts expected_app_fingerprint, scenario,
request_key only. Explicit retry reuses the original complete body and key.

Server builds a fixed namespace wrapper from current sealed extraction, current source check,
exact registered A-S declaration and current target resource hash. app_drafts and independent
namespace task_extractions store it; app_previews binds actual protocol cold Run receipts.
No new tables, DDL, Principal, Grant, arbitrary code, client Candidate/Report/Replay/gold or verdict.
Runtime is the existing server-selected project runtime. It is a shared engineering authorization
domain, not an independent V5 application principal. Existing source and target grants are checked
on create/read/submit/history and actual worker dispatch. No creator authority is inherited.
Old CSV/agent loaders retain rejection; their legacy list excludes this new namespace.

Default worker has no activated provider and stops WAITING_RESOURCE with zero requests. Tests
may use the existing exact offline InternModel + httpx.MockTransport attempt-accounting gate;
this does not authorize LIVE or establish open semantic correctness.

## Independent oracle and focused acceptance

Use actual HTTP source/check/extract worker receipts. Test responses are hand-authored, kept out
of submitted inputs. Two new typed Scenarios: 500/unapproved → ALLOW; 680/unapproved/no receipt
→ BLOCK with both missing-receipt and approval actions. Compare actual Report/Scenario/Run IDs,
not a UI label or prior source output; finite checks remain separate and owner PENDING.
Fresh jsdom page must obtain the stable saved draft through HTTP without source-session state.
Unknown facts should yield UNKNOWN when exercised; explanation remains NOT_CHECKED.

Negatives: extra client payload fields; changed-body same-key conflict; accepted/lost receipt retry;
wrong project/identity; old-family inspect/preview rejection; sealed plan/check/response tamper;
source or target revoke; target hash drift; denied default provider; app-selection/project/identity
late HTTP response; history must bind exact actual accepted cold payload and receipt.
Principal/Grant row snapshots before/after must remain identical. No full suite, native CI, LIVE,
push, deployment or merge into the frozen candidate. Dedicated SQLite/static checks only.

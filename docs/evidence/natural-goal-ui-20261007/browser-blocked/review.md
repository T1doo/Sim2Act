# Natural goal planning UI contract review

Read baseline 1656752b2e7890a4eaaead63293543669e6c96b8; this is design review, not review of forthcoming implementation. Root owns web; backend owner generation_next_slice owns approval gate. No repository edits, installations, model traffic or permission changes by this review.

## Closed source and acceptance

Keep existing ordinary saved-goal action separate and label the new action as natural-language plan generation, not successful execution. The new action POSTs the exact saved GoalCard version/fingerprint/key to planned-runs; never accept form edits or switch the endpoint of an already uncertain intent. Pin execution kind/path in immutable intent alongside identity/project/card/source snapshot. The current map's key contains identity/project/card only: simply reusing it for both endpoint types could replay an ordinary request as a planned request, or vice versa. Treat ambiguous acceptance as UNKNOWN; first definite 4xx is rejected, later 4xx after uncertainty stays UNKNOWN. No automatic retry, provider selection, LIVE allowance or publication.

Source validation should retain complete r.contract.snapshot.source_goal_card equality with the saved submitted snapshot; generation, current identity, project, card and run-user selection protect both source read and later plan response. Plan loading from history must also work with no active GoalCard, binding the current actual selected Run/source/project rather than fabricating a saved-card selection.

## Actual approval contract (backend owner confirmed)

GET /api/runs/{rid} exposes natural_plan {fingerprint,plan,validation:'VALIDATED',confirmation_required,confirmed}; no raw context/messages. A valid plan waits in WAITING_APPROVAL with zero Operations. POST /api/runs/{rid}/confirm-natural-plan accepts ONLY {expected_version:strict positive int, expected_plan_fingerprint:hex64, request_key:1..100}. Successful confirmation leaves QUEUED; duplicate same-key original-body confirmation does not advance version or duplicate event. Worker revalidates confirmed actual plan/provider receipt/source/current authorization and must not call the planner again. Default disabled provider has no model send. Plan validation is structural/authorization evidence; interpretation is not goal acceptance.

Render exact actual interpretation, assumptions, unresolved questions, steps/dependencies/resource IDs/tool parameters and fingerprint using textContent. Do not render entire model/context messages. Visible ack must start unchecked on every new selection, plan/read/version/source change or read error. Confirm enabled only for current verified WAITING_APPROVAL plan, explicit ack, exact Run version/fingerprint and no in-flight/UNKNOWN confirm. Keep plan generation acceptance and confirmation intent maps distinct. User checkbox by itself is not server acceptance. After confirmed acceptance/lost detail use GET-only read recovery; uncertain confirmation uses identical original confirm body/key, never a new plan/Run or model call.

## Real protected browser execution

Installed Playwright is /opt/codex/runtimes/cua/lib/node_modules/playwright and Chromium /usr/bin/chromium. An actual chromiumSandbox:true/headless launch aborted with SIGABRT and SUID helper configuration error. /usr/lib/chromium/chrome-sandbox is mode4755 owned nobody:nogroup. No no-sandbox/security-bypass flags or system mutation used. No protected renderer, screenshot or UI flow exists for this probe. Real browser flow is BLOCKED, not PASS/SKIP substituting JSDOM. Evidence browser-probe.json/log. A future same-driver run needs an already correctly configured protected browser environment; installation/system permission or Windows CI is not authorized here.

## Bounded real HTTP/Playwright acceptance checklist

Use actual loopback API/fresh full product page and normal Worker with explicit offline MockTransport fixture. No browser page.evaluate mirrors of UI functions: click/fill/check visible controls. Capture actual HTTP body/path and receipts, per-fixture authority/Attempt/Operation baseline; drive worker only via closed test-only action using valid JSON{}. Keep actual timer cadence. Transport faults fetch the original actual response first, then abort/alter/hold in the browser route; verify durable server state separately. No synthetic server result replaces actual worker receipts.

1. Default disabled planning action reaches its actual waiting state with model sends=0 and Operations=0.
2. Saved card v1/full facts/source binding; unsaved editor modifications excluded from body and frozen Run.
3. Planning acceptance has source card/version/fingerprint/mode/namespace exact binding; no automatic candidate.
4. Offline provider valid plan makes WAITING_APPROVAL and Operations remain zero before any ack/confirmation.
5. Exact interpretation and full bounded steps rendered as literal text; HTML/script references do not execute.
6. Plan schema validation and UNKNOWN/NOT_RUN/PENDING semantics remain distinct from success/acceptance.
7. No ack means no confirm POST, no tool execution; programmatic unchecked click must also reject.
8. Checked ack confirms the exact current Run version and plan fingerprint.
9. Confirmation acceptance -> QUEUED; normal Worker produces actual verified tool receipts without second planner call.
10. Final technical PARTIAL/goal NOT_RUN, no application candidate/publication.
11. Lost planned-Run acceptance retains immutable body/path/key and prevents new submission.
12. Malformed/coherently wrong source or planner-policy acceptance is UNKNOWN, not successful receipt.
13. First definite 422 rejected; later 422 after lost acceptance retains UNKNOWN and same original body/key.
14. Accepted planning detail-read failure clears protected fields and uses only GET recovery.
15. Lost confirmation receipt retains original confirm body/version/fingerprint/key; same-key retry is idempotent.
16. Malformed confirmation receipt cannot become confirmed; server history/read demonstrates actual state.
17. Accepted confirmation detail-read failure only GETs existing Run, never confirms/creates again.
18. Changed Run version, plan fingerprint, source snapshot, returned-model identity or current authorization rejects confirmation/execution; Operations do not increase.
19. Cross-owner and cross-project exact actual API access denied; old UI/source/plan/ack cleared.
20. Identity and project ABA held actual plan/Run responses cannot redraw protected data or enable ack/confirm.
21. Selected-card and selected-Run changes during acceptance/detail/history/confirm cannot steal new selection.
22. Ack clears on refresh error, new selected Run/plan/version, identity/project change and cold page.
23. Cold fresh page real task history opens WAITING_APPROVAL plan unchecked, and later final receipts, zero automatic POST.
24. Double-click/in-flight/old detached button cannot duplicate submission/confirmation or revive stale ack.

All functional checklist results NOT_RUN until exact new source/fixture contract freeze and a protected browser can actually launch. Source/receipt hashes and cleanup must accompany any later PASS; save initial failures and close every owned page/context/browser/API child before writing final PASS.

## Development follow-up

Root subsequently implemented natural-goal.js and confirmation gate. New repository tests/natural_goal_ui.cjs and test_natural_goal_ui.py are my only owned writes. The shared driver has ACTUAL_LOOPBACK_HTTP JSDOM mode and optional sandbox:true Playwright mode; only the former ran. Source bytes of 6fbb29b7a09a7483e763692257ba9fec15eadcb3 were stable across first development run: 5 cases PASS / 9.47s (valid29,disabled8,invalid_schema8,cancel7,revoke8). Normal Worker uses explicit hand-written httpx.MockTransport; no LIVE request. Default has 0 sends/Operations. Valid has 1 provider wire/1 real Operation; cancel and invalid/revoked cases execute no Operations. Revocation permits exactly one explicit existing resource Grant revoked/revision increment; all other authority rows equal.

Root then found a configuration-pending form field ordering gap and ack invalidation gap. I added two actual held-configuration checks plus checked->schema/fingerprint error->valid read unchecked regressions. Final valid count expected33. These latest additions have only syntax/Ruff validation here; root will freeze and execute final combined selected cases, and an independent agent reviews product UI. Do not claim old 6fbb29 result verifies this newer source. Actual real-browser remains SUID BLOCKED; no native launch retry/download/system change was performed.

Evidence original run /tmp/natural-goal-ui-development/{pytest.log,junit.xml,pre-source.json,post-source.json}; fixture case receipts /tmp/natural-goal-ui-dev-cases/*/results.json. No repository evidence contains fixture DB/bearer/info credentials from this reviewer. Controller returned, every test API thread joined (launcher assertions). Temporary offline fixture files retained under /tmp only. No PG/full/CI/push.

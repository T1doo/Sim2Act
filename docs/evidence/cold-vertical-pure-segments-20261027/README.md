# Cold fixed pure segments: isolated candidate, not G0 acceptance

The candidate remains **default off**. Only explicit internal test constructors install `_ProducerSegment`; production launchers do not. No real model, real-clock G0, Cold2 or Windows window was executed for this evidence.

## Implementation and safety boundary

Three invocation-local reductions replace overlapping complete encodings inside qualified fixed pure segments: producer publication (three complete pins to two, retaining three typed passes), legacy `_ColdTrialGraph._base` (two content pins to one successful exit pin with both dynamic boundaries), and the adjacent stage-parent check (two complete pins to one, retaining its second dynamic check and every pure relation predicate). Unknown code/schema/serializer qualifications use the original path before publication. Serializer warnings use the original behavior rather than being suppressed. Exceptions invalidate scopes as before; the final second-dynamic-failure regression verifies this explicitly.

Original fresh content, exact type, model/raw, hidden RowMapping data, cross-root alias, SQL/auth/revocation, connection/transaction/scope/epoch/settings/stop, Run/fence/lease/deadline and receipt checks remain. No cross-call PASS cache or mutable graph digest is reused. The candidate registration is detached on invalidation. Qualification resource failure returns to the original path before holding a result.

This is **not** the unfinished seven-family owned-record migration. It issues no whole-run immutable packet and does not need an invented future-producer capacity allowance. Original mutable roots remain fully checked; current-result serialization and invocation-local qualification metadata remain. The separate ownership candidate is not enabled or represented as complete.

## Actual executions and source versions

| Phase | Order / scope | Mock exchanges / entries | Actual result |
|---|---|---:|---|
| Producer-only, archived separately in `../cold-producer-segment-20261027/` | OLD then NEW | 7 / 9 | complete strict synthetic differential, 1 PASS |
| `reverse-pair/` | combined producer/base NEW then OLD | 7 / 9 | complete strict synthetic differential, 1 PASS in 244.72 s; supervisor 245.640 s |
| `final-normal/` | final producer/base/stage candidate only | 6 / 8 | complete normal synthetic chain, 1 PASS in 134.17 s; supervisor 135.024 s |

Total across these three distinct local phases: **20 Mock exchanges / 26 entries; zero real models**. They are not one reused grant or a controlled G0 window. Each source variant built its own configured prefix: the existing software fingerprint hashes source, so an old QUEUED prefix cannot legitimately be relabelled after source edits.

All complete chains use the existing configured test-only environment/account/software substitutions and explicit semantic business clock, actual SQLite Store/Worker/approvals/accounting, and HTTP MockTransport. They cover prepare, first commit, receipt/parse, second commit, five actual settlement writes, `_ModelSettlementRead` post-settlement tail and normal scope close. Attempts/Operations are VERIFIED. This includes synthetic business writes, not a zero-POST UI probe. The semantic clock is not the production clock and cannot certify the original 30-second lease.

The reverse pair has exact outputs, SQL parameters, receipts, attempts, operations and writes equal. CPU 100.576622400 → 94.835588162 seconds (ratio 0.942918801), wall 100.711334290 → 94.934117929 (ratio 0.942635887); codec count 20209 → 18953, output bytes 13744126320 → 12767604325. This single reverse-order observation is about 5.7%, not a stable performance guarantee. Its five compressed frozen sources belong to that intermediate version, not the final version.

The **final frozen version** was checked only for a complete normal chain: CPU 94.564397890 seconds (pre 31.310039628, post 63.250007509), 18582 codec calls / 12427443494 bytes. Actual selections: producer 177, base 1081, stage 371; zero fallback; both scopes inactive and selectors detached. Its summary deliberately has `exact_outputs_sql_receipts_equal: null` and no performance ratio. Do not inherit the intermediate 5.7% as final-version speed evidence. The 577-file before/after manifests are unchanged and final seven source hashes are in `final-sources.json`.

## Necessary local regressions and preserved failures

`unit-originals/` retains original logs/XML, including both red runs: an extra newly introduced dynamic call (removed), then duplicate synthetic seed violating the existing UNIQUE phase constraint (fixture corrected, no product constraint relaxed). The intermediate compatibility run was 42 PASS, not a final-source rerun. Later targeted records are 9 PASS legacy base, 11 PASS stage, 11 PASS final dynamic/producer, and 1 PASS qualification-resource fallback; overlapping tests are not added into a unique-test total. They cover warning/callback ordering, entry damage, hidden-data mutation, alias splitting, cross-call changes, SQL write epoch, scope/stop/dynamic failure and unknown serializer/code fallback. Final complete-chain execution followed the last source change. Ruff on changed candidate/tests and `git diff --check` passed; no whole-repository lint claim.

## Remaining G0 critical path

The original controlled result remains UNKNOWN: second commit → `_recheck` → `_require_run_context_row`, saved at minus lease 0.580261469 seconds; the comparison booleans were evaluated after the exception, not the original short-circuit trace. Original prepare cost was 14.5832 s wall with 3579 codecs / 9.40818 s inclusive thread CPU; source resolution 3.9419 s / 993 codecs. Those nested scopes cannot be added. The original controlled run did not reach the final five writes and post-settlement success tail, so saving 0.58 s alone cannot establish complete acceptance.

`root-key-set-costs.json` attributes fresh encoding to phase and exact root-key sets. It is not content-version identity or exclusive adapter CPU. The final synthetic post tail's 63.25 CPU seconds exposes substantial remaining work, not a necessary lower bound or a production lease measurement. No further window was started to gamble on timing. The remaining engineering condition is a safe reduction of complete fresh post-settlement/typed verification cost, followed by final same-source net evidence and separately authorized real-clock validation. Provider identity/entitlement provenance and overall F2/R0 remain separate unaccepted gates. October 31 delivery risk remains high; no deadline extension or completion claim is implied.

## Review, cleanup and integrity

Independent read-only review accepted the exact final source/actual selection/normal chain with these limitations, and confirmed the reverse pair's strict differential. It ran no extra tests. Both archived child processes exited 0 without timeout or forced kill; test-owned threads were empty, clients/engines closed, selectors detached. Synthetic databases/sidecars/prefix evidence were retained intentionally; this is not a whole-host process audit or deletion claim. No unknown process or lock was touched.

`manifest.json` seals every file in this directory except itself. `execution.json` records actual source manifests and exit metadata; compressed reports retain exact outputs and SQL. Earlier failed evidence and original controlled-G0 logs remain unchanged.

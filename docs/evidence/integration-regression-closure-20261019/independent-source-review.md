# Frozen v11 source/security review — limited PASS

Fourteen-file frozen manifest SHA256: `19ea078022c3d43be9b8851e2d3bf1e54b7a28d99097726a770a7a92a3c51060`. All frozen bytes were hashed/parsed/copied and current file hashes recorded. This report independently reviews the two product deltas and new test; inherited unchanged v10 source conclusions remain bounded by their own seals. No definite P1/P2 found. No whole-flow repair or performance acceptance is granted before actual receipts.

Reviewer actions were read-only source/hash/AST operations. No repository edits, product imports, tests, DB, models/network or process signals were performed. This review directory is the only write target.

## Strict ordinary eligibility after authorization

New _ordinary_generation_reads is an internal read-reuse selector, not an authority function. It returns false outside test-only SQLite, and requires frozen mock mode, exact goal-natural-spec-application.v1 and no activation. It requires exactly three actual MOCK Attempts, parameters of exact dict type and complete absence of the pa_trial_binding key. An explicit null key is rejected. The surrounding version check also requires exactly three None version projections, so mixed/unknown bindings do not acquire ordinary eligibility merely via missing get values.

The two actual call sites are reached only after original source_scope_gate success: _journal_scope_anchor runs after a complete scope proof or after current owner/Grant revalidation of an existing hit; verified_candidate calls source_scope_gate before eligibility metadata reads. The helper does not call frozen_contract/source_scope_gate itself, avoiding incomplete/inflight recursion. Its private standalone shape does not authorize an arbitrary external Run read.

The existing three exact journal/production/PATrial version lists short-circuit before the ordinary helper, preserving their previous selection. New metadata reads contain no generation, claim, sender, reservation, settlement, executor or Grant creation. Full first _verified_candidate, source/history/candidate/seal checks and all existing cost/authority guards still run; eligibility does not replace proof.

## Existing bounded SourceReads reused

_journal_reads now opens the existing token for worker.pa_trial exactly None, Store.test_only, SQLite, mode=mock and live_enabled is False. For non-ordinary inputs, the old _journal_binding and _binding behavior remains. Actual PATrialBinding remains non-journal/nullcontext here as before; its existing trial-local read scope is unchanged. Existing journal/production bindings still call their original _binding check. The connection must still belong to the original engine and be in transaction.

The token retains its original exact Store/connection/driver/transaction/thread/epoch/current-token identity; first completed full proof, required authorities, fresh Grant/owner checks, independent deepcopy results, inflight refusal, exception clearing, write invalidation and transaction-exit clearing. No new cache mechanism is introduced. Parent lease=30, Run=300, owner/fence, model/tool behavior and PG path are unchanged. This shortens repeated read proof inside the existing business transaction; it adds no heartbeat inside that transaction and does not wrap business execution in the renewal lock.

Static delta checks show that in goal_applications only _journal_scope_anchor and verified_candidate change, plus the new eligibility helper; _source_scope_gate, _verified_candidate, history and other original functions are AST-identical. In pa_trial_dispatch only _journal_reads changes. Entire natural_live_admission bytes equal v10: _generation_accounted and trial-stage eligibility are untouched.

## New test is meaningful and bounded

The test creates one actual ordinary prefix via exactly three existing finite MockTransport generation calls. It performs real complete generation proof, counts complete proof calls, checks second-hit independent copy, verifies explicit null is ineligible, writes damaged Attempt history and observes token invalidation plus original DomainError refusal. A fixture-only exception rolls that intentional damage back.

A separate transaction sets actual Grant expiry, advances only the db.time clock by two synthetic seconds with no intervening DB write, and requires GRANT_REVOKED, unchanged epoch, no extra complete proof and cleared token results. This checks current authority on a hit rather than merely comparing cache values. Its use of the existing direct _source_reads scope validates the mechanism/eligibility; the new worker _journal_reads wiring still needs the actual ordinary Source case to complete.

No original assertions are removed, lease/deadline increased, expiry swallowed or recovery/fault matrix expanded. The expiry is a synthetic-clock check of real stored Grant data, not real-wall-time expiry qualification. The test's complete-proof counter calls the original implementation and does not replace its result.

## Remaining execution/identity boundary

The ordinary proof case, mypy and original extra Source case were running or pending when this source report was sealed. Their completed execution/JUnit/stable input and any proof-count observations must be reviewed separately. The existing v10 exact V2 single-node PASS belongs to commit aae3/frozen v10. V11 changes source hashes; branch short-circuit preservation is static evidence, not a new V11 V2 execution or same-hash claim. The v10 rest20PASS/1FAIL and all earlier native failures/interruption records remain preserved.

No Windows, PG, real model/account/semantic/human acceptance or remote CI qualification is granted by this source-only review.

# T0/T1 proposal and actual-window README: document closure

Result: DOCUMENT_CORRECTIONS_ACK_CURRENTLY_BLOCKED_NOT_IMPLEMENTATION_OR_RUN_ACK. The two contract precision findings from the initial design review are closed in the revised document. The initial review remains an unchanged historical original; no implementation or qualification is inferred.

Read final document SHA256:

- NEXT-STEP-DESIGN.md: `c929a8d80780223a7c79f60b2f6e88f9717665cf9242bc6a8020b1bfee7e0978`
- README.md: `65e2a4bb0957767720a1eaea539b8a4ec20d9266a069f202d7d856b6761d6537`

Both are under `docs/evidence/tail-cost-window-20261021/`.

The revised L0 is explicitly the exact committed renewed_until from the existing synchronous renewal at its original location, or its exact locked sequence/worker/run/fence witness. It is not a later runs row or heartbeat state's maximum. The document correctly notes that current runtime.renew discards both branches' return values, so a future exact return/witness propagation is unimplemented rather than an already available contract. No extra renewal or business clock sampling is proposed.

The revised T1 rule explicitly checks L0 and original tight finite bounds immediately after acquiring the write lock, including busy waiting, before protected rereads or result publication, while retaining later original checks and final clock. Current Store.guard's later lease cannot replace it. The initial minimal algorithm now rejects every witnessed Run-column change, including lease growth: normal heartbeat can cause frequent conflicts and may not be disabled to accommodate the candidate. Allowing lease-only growth is a separate, unadopted contract requiring proof. Thus the earlier full-projection-versus-heartbeat ambiguity is closed without silently broadening authority.

The document also explicitly separates SQLite single-writer protection from mutable process settings/stop/registry/memory. These require independent ownership/locking/checkpoint mapping and no-callback proof; database exclusion supplies none of that. Complete actual query/consumer projection and set/negative predicates, no escaping mutable consumer data, new scopes and compatible once-only pre-issuance selection remain enablement blockers. A list of eight dependency families is not mistaken for a completed read-set map. No claim that T0/T1 is already short, bounded for all legacy inputs or fast enough for the original lease is made.

The README agrees with the actual-window result review: UNKNOWN; first commit returned, second failed in original composite Run check; post-exception 20true/2false and original-at-minus-lease 1.1715714931488037, not original short-circuit trace or wall-minus-thirty. Inclusive tail/residual attribution and unknown unreached costs are preserved. Exit calls/returns are distinguished from unsampled exit suppression value and normal original scope completion. Receipt progression and StopBoundary row-state descriptions are explicitly control-flow/mechanism inferences, not separate phase/root/DB observations.

Additional raw cross-check for README figures: first-five codec metrics sum to 5348 calls / 3720455764 successful returned bytes / 14740890900 thread CPU ns. Raw receipt has 6798 disk samples, peak logical2295786/allocated2314240, mean interval0.05040685120523759/max0.12782756800152129 seconds. These match the README and remain instrumentation/sample metrics, not performance or hard-quota qualifications. No reviewer revalidation of the author's entire archive or older-original set is claimed here.

No runtime/src/scripts/tests diff was present in this document-only follow-up. Reviewer performed only document/source/evidence reads and /tmp report writes, with zero product imports/tests/DB/Worker/Mock/G0/launcher executions and zero repository writes. New path status remains CURRENTLY_BLOCKED; this ACK authorizes neither code activation nor another window.

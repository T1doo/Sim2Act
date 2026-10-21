# Next-step design documentation closure

Decision: **ACK for CURRENTLY_BLOCKED conditional design documentation only**. The proposal now explicitly closes both wording/algorithm-precision concerns in NEXT-STEP-DESIGN-REVIEW. It does not close the implementation prerequisites or authorize runtime changes, removal of checks, a new grant or another window.

Reviewed final `NEXT-STEP-DESIGN.md` SHA-256: `c929a8d80780223a7c79f60b2f6e88f9717665cf9242bc6a8020b1bfee7e0978`.

The text now binds L0 to the same original synchronous renewal's exact committed return or controlled sequence/worker/run/fence witness, expressly excludes latest row/max heartbeat state, and calls out runtime.renew's dropped return as an unimplemented forwarding seam. T1 lock acquisition/busy wait cannot extend L0: the first lock-held clock check precedes protected rereads/results, with original later gates retained. The minimum route rejects every witnessed Run change including lease growth; normal heartbeat may therefore cause conflicts and must not be disabled. Any lease-only tolerance requires a separate consumer/fingerprint contract and is not adopted here.

The conditional argument also expressly separates DB writer exclusion from process settings/stop/registry/memory ownership or original-checkpoint synchronization. Full eight-family field/query/absence/phantom/consumer mapping, no escape, scope reissuance, current authorization, persistent fingerprint compatibility, capacity route and post-delta proof remain unclosed. It correctly forbids immediate transaction splitting based on the two accounted manifests or Run CAS alone. This is a coherent safety direction with a stated functional/performance limitation, not an implementation-ready optimization.

The result README was additionally read. Its numerical results, post-exception caveats, scope-exit method interpretation, partial cost limits and cleanup match the already reviewed originals. The final small clarity correction uses the literal evidence field `original_scope_returned=false` (not normally completed); its following section correctly states that the exit method's actual return value was not sampled. This closes the wording suggestion without changing results.

Only source/text reads and metadata hashes were performed in this increment; source diff remains empty. No reviewer code, tests, DB, product, Mock, G0, profile, signal or window was run. No repository file was edited. Prior reviews and original evidence remain unchanged.

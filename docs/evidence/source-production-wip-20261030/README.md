# Source production wiring WIP — not release or full-flow acceptance

Base: `cd65e648cfe9efcc8b5f0382dd89e3c976dac91b`.

The post Source producer now returns an immutable native Owner/Binding and the
Source consumers read static, immutable native views. The original Graph pin
retains the complete metadata, original leaves and shared outside anchors;
input/role/control root identities are continuously bound. Source models leave
the repeated consumer cohort, while the original complete Journal Ledger and
QuotaCursor checks remain. Source business equality/usage stay distinct from
the stronger constructor/handoff/full Slot-storage comparisons. Pre/Generate
and prepublication-capacity fallback retain their full original paths.

The latest completed component run is
`/workspace/scratch/source-production-sealed-code-connect-20261030.log`:
1 passed, 4.75 seconds, at 2026-10-30 12:32 UTC. It uses original SQL producers,
Source usage, archive bodies, source resolution and archive-chain consumers over
synthetic file-SQLite records. It executes no Worker, model call or HTTP sender.
Earlier failing comparisons were retained in `source-production-connect-first`,
`-second`, and `source-production-view-connect` logs under the same scratch root.

The environment disconnected before the boundary-test append/run process was
created. Recovery confirmed the original single test file and no new boundary
log or lingering test process. The 19 changed/new source files were also saved
to `/workspace/scratch/source-production-wip-recovery-20261030` before this commit.

Pending: actual production-wiring independent review; root rebinding and full
Slot storage/alias rejection tests; the complete stage/runtime collector and
existing regression suite; new native-view grammar/mutation tests; refreshed
software qualification (headers have been added to its required inventory);
then exact-source same-large-input G0/G1, cancellation/revocation/concurrency and
reopen measurements. The current qualification JSON is deliberately still the
previous source, so this WIP is not a qualified production target. No Windows
validation, fourth CI run, paid request, deployment, main update or Release.

The previous full Worker result remains 97.42/118.62 seconds for two Cold
settlements, with only 1.38 seconds on the latter. It is not new-source evidence,
and does not meet the original performance goal. The 30-second writer admission
budget and 120-second settlement interval are distinct and are unchanged.

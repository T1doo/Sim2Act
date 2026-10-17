# Continuous CSV revisions: early WIP review

Base: `ce3fa86677cdaa58e076cc03e15a9b5414fd1e77`. This is a read-only static review of an unfrozen worktree. It is not execution or final implementation signoff. Sampled file hashes are in `proof.json`. No repository files changed, no tests or Worker/model execution run.

The common paired journal and explicit namespace dispatcher are acceptable. I did not find a concrete partial re-signing bypass of the common Preview/CHECK/Job/event/Release anchors in this WIP. The old `effective` and `calculate` function ASTs are unchanged. Normal SOURCE Release instance creation still rejects. The private CHECK path revalidates current saved v2 preview, exact Reference, parent Release and deterministic key. New context rejects CHECK-pinned instances and requires the parent SOURCE original business instance. Parent resolution uses historical bound with no child snapshot override.

Two issues were reported to root:

1. `parent_scope` mixes Release IDs with preview recursion tokens in one eight-slot depth counter. Each v2 ancestor consumes both forms, so valid chains hit the limit before specification revision eight. Separate Release ancestry depth from preview recursion detection.
2. Historical `definition_graph` calls `graph.logical`, whose external rule/check fingerprints include hashes of all current Python registry files. An unrelated software change alters historical v2 reconstruction even though its saved rules did not change. Historical overlay should freeze unchanged rule/check source versions; current-work software changes remain checked by current graph validation/explicit derive.

The proposed connection-local completed-parent proof cache is reasonable only within the same connection/live transaction/write epoch/user/Release/limits (thread identity recommended), after scalar ownership/source authorization and with fresh collected authority checks on every hit. Use the existing conservative all-non-SELECT epoch counter; cache only completed successful proofs and deep-copy results. Recheck transaction and epoch after authority checks; no incomplete/cyclic/failed result can be reused. Fresh current Goal, instance and graph checks and tool dispatch/commit reads remain outside this optimization.

Root reported plans to correct the depth counter and add this bounded cache; those changes were not yet sampled by this report. Historical registry behavior remains an explicit pending implementation review point. No final blocker-free conclusion is made for the unfrozen implementation.

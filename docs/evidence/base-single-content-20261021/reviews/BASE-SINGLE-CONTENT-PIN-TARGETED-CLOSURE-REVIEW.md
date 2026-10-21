# Native _base — targeted closure source review

Read-only review of `freeze-targeted.json` (9 files), without executing code, imports, tests, database, Mock or signals. No repository edits. **Original three P2 findings substantially closed; two narrow callback-qualification omissions remain before a final code ACK.** Author tests were still running; this report does not attest their outcome.

Reviewed source hashes:

- `_cold_base_segment.py`: `707d85b35a898c327296f37f5c787f566b7394d67645bffbc4dd0bc0290bd8a5`
- `natural_spec_runtime.py`: `18d7d4ffd750d4dc03716289356dab5f0fe1972a44d4b197acb972bae28ba680`
- `cold_accounted.py`: `85450c64e96a3a96abb22101069582781175fe267e26b425344039bec4a729f5`
- new targeted test: `7c073e7b0cc2cc470910eba155d562394db069be2bb200e2c97728b24f0e49ae`

The original instance shadow issue is addressed by static resolution on actual trial/mode/scope instances. Public CGR.check now calls its fixed class dynamic implementation. The private complete/generation proxies retain issuance-origin identities checked before any iteration, so replacing a proxy with one wrapping a foreign Mapping declines fast eligibility without dispatch. Private native tables, roles, headers, active booleans, frame and allocation receive the needed exact representation gates. Initial mode dynamic failure now obtains the content check while graph/mode remain active, before outer invalidation; the raw-plus-stop mixed-order example is explicitly tested against old behavior.

Two remaining concrete P2 paths were sent to the sole writer:

1. **Model catalog helper callback precedes the delayed full pin.** `fixed_serializers` invokes `gate._trial_typed_nested_classes()` before serialization/full entry. `_GATE_NAMES` omits that function and its `_trial_typed_classes` dependency. Replacing either with a recording callback leaves the current eligibility witnesses satisfied. With simultaneous unused raw drift, the old path rejects before invoking this helper; the new path invokes it in qualification first. Add these two exact existing functions to the existing code witness and verify fallback/raw-first rejection. No general code-tampering framework is requested.
2. **Binding properties read before exact binding type.** `_base_pure_ready` obtains `self.graph.binding`, then reads `.contract` without first requiring exact original `ProductionTrialBinding`. A foreign object with a recording `contract` property therefore runs during eligibility. No worker modification is needed: the old CGR dynamic header would reject `worker.pa_trial is not graph.binding` first with zero property calls. Require the exact binding class before any of its attributes are read, then retain the existing exact contract/caps and four-string gates.

The new targeted test source otherwise has useful precise oracles: old/new 2→1 codecs with identical family/run/typed/dynamic call sequence and zero SQL; mixed raw/model/stop comparisons; six endpoint damage cases; unqualified dump/schema/nested serializer retaining dual pins; seven foreign representations declining without callbacks; original error identity and sticky scope invalidation. The nested serializer case correctly allows legacy acceptance when the compiled parent serializer does not actually dispatch that replacement. This source assessment is not a claim that the author test batch has passed.

The proposed fixes are within the same representation/code qualification boundary and do not require root migration, changing default paths, weakening dynamic/content guards or a G0 window. A subsequent frozen incremental source review can close them, followed by the already requested complete configured semantic A/B under its disclosed virtual clock.

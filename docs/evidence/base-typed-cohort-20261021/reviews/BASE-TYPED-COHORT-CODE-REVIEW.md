# Base typed cohort: initial code review

Result: LIMITED_PRODUCT_STATIC_ACK_PENDING_FINAL_HASH_AND_TEST_EVIDENCE. No product P1/P2 identified in the read patch. The source-only design review remains applicable; this review is not an execution instruction, grant/window, benchmark or deadline qualification.

Baseline: `f18d6845db4a5ebdb5b71b745462b575cc47cfc0`.

Read SHA256:

- `src/sim2act/cold_accounted.py`: `87b0c464866ac038140d615182d1dc552c83dd53cbf629a9bad2b4973bad017e`
- `src/sim2act/natural_spec_runtime.py`: `22eec3d7823126396084fee19c0e65d259c15ec166c9e19b5be50377f4198dc7`
- `tests/test_cold_base_cohort.py`: `bfd1c08f58b9d6696ff6800096a8c2b24aada5bb796aa179ae8fe62c94aebbfc`

Product findings:

`_ColdTrialGraph._base` is unchanged. Its first original CGR check, exact worker/connection check, sole `_typed_parameters` call, second original CGR check and BaseException invalidation remain. The new local native selector uses exact mode/candidate types and `owned_ready is True`; no public/env entry, skip parameter, reusable witness or ambient state is added. `_base_parameters_current` checks exact graph/candidate/mode linkage and runs the original dynamic and link predicates. Non-native/default/nonready branches retain their original calls. Existing public entry readers retain full self-pins.

`_pin_stage` retains its original first full pin, ownership test, dynamic/link checks and exception-close wrapper. The extracted `__stage_current` is the same complete relationship body, now using self.graph after the wrapper already proved identity. Both native Base stages reuse that private body without dropping Generate family/run, raw/metadata, Source job/binding or Cold extraction relations. Its exact extraction shape check is already part of the reviewed composite body; the original owned stage-model path also requires that shape before acceptance.

The new fixed `_base_stage_models` mirrors the original owned `_graph_trial_stage_models_from_raw` path in source order: mapping and stage shape, frozen model hold, Generate family, optional Source family, optional extraction model helper. The independent admission helper is unchanged. The runtime's final original `_trial_typed_values(models)` is unchanged. The original Family._root → scope._current → mode._dynamic leaf lifecycle checks remain live. On exceptions during the Base cohort, original graph invalidation closes its exact owned frontier/mode; no late fallback was added.

Test-source observations, separate from author runtime results:

The test constructs a real issued synthetic SQLite native segment and an actual _ColdTrialGraph Base shell, with both owned stage facts. The old adapter reinstates original public family/stage assertions and independent stage-model reader. Expected complete owned-cohort codec counts are 15 versus 2; independent public reader calls still must encode. This shell sets `trial=None`: it does not exercise full original trial-prefix typed fields, prepare, commit or G0. Five injected changes after the original final typed pass require Base's second check to reject; four between-Base-call cases capture only the second Base error and rethrow that same object for original cleanup. An AST test locks the unique private caller and unchanged two-check Base shape.

Evidence wording refinement sent to author: the comparison currently records family, run, typed-hold and typed-values in four independent lists. Equality proves each category's internal sequence, not a single combined interleaving by itself. The source's combined order was independently checked here. Either add one shared ordered trace in these same observers after the running batch ends, or keep final runtime claims limited to separate category sequences and attribute cross-category order to static review. This is not a product defect or a request for another test suite/window.

Initial author test run was in progress at review time and no result is asserted here. Final hashes/logs remain to be reviewed. Reviewer performed source/diff reads only, with zero product imports, tests, database opens, Worker/Mock/G0/launcher execution and zero repository writes.

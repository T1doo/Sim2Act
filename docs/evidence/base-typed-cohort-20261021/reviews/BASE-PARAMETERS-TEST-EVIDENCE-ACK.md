# Base parameter collection: final frozen evidence ACK

**ACK for the author's final frozen local test evidence and its unchanged reviewed source.** No remaining blocking discrepancy was found in the inspected hashes, logs or JUnit. This supplements `BASE-PARAMETERS-CODE-REVIEW.md`; it is not G0, deadline, performance, production qualification or new execution authority.

The reviewer only read source/test text, manifests, logs/JUnit and hashes. No tests, DB, product, Mock/model, G0, profile or signals were executed and no repository file or grant was written.

Base HEAD: `f18d6845db4a5ebdb5b71b745462b575cc47cfc0`. Independently read current hashes match both `frozen-before.json` and `frozen-after.json`:

| File | SHA-256 |
| --- | --- |
| src/sim2act/cold_accounted.py | 87b0c464866ac038140d615182d1dc552c83dd53cbf629a9bad2b4973bad017e |
| src/sim2act/natural_spec_runtime.py | d0140af82c18f1b5181e6ffa929189d7dbd9ac49431a980710792c31d62628c7 |
| tests/test_cold_base_cohort.py | 5a26147d2bcd8079c1f820ecae579ff8a065e2744e6aa6b32074dcbcae4aba6e |

The final author log records **129 passed**, one existing Starlette deprecation warning, 227.74s. JUnit records 129 tests, zero failures/errors/skips, 227.736s. Independent testcase counting gives 14 base-cohort, 30 stage-pin, 27 native, 22 receipt and 36 SQLite tests. Ruff reports all checks passed on the current three-file scope; mypy reports no issues in two source files. These are author-run local/helper/synthetic SQLite checks; the reviewer did not rerun them.

Final test-only additions from the preceding reviewed 12-case version include end-of-typed-cohort `max_output_tokens` and links mutations. Their exact source text was inspected. The final seven after-cohort cases require the callback to have fired and `_base` itself to leave phase INVALID; the four between-call cases separately capture the actual second-call rejection and rethrow the same exception through cleanup. A merely later outer-scope refusal or unexpected first-call error cannot satisfy those assertions. The interleaved family/Run/typed-hold/cohort trace remains equal, and the complete dual-family/dual-stage case records 15→2 codec calls, 11 family predicates, three Run predicates, five holds and one typed-values pass. Public independent assertions still self-pin; the private collector has only `_base` as repository caller.

The original 11-case development batch is preserved as **10 passed / 1 failed**, 16.79s: stop-after-typed was rejected only at outer scope and `_base` remained COMPLETE. The corrected 12-case development batch is separately **12 passed**, 16.99s. Neither historical batch is upgraded or combined with the final 129 as additional independent tests. Current source includes both original outer full graph pins, final complete typed cohort and cheap owned dynamic/link checks at both ends of the native pure segment. No allowances, lease, codec, launcher or guards were changed by this patch.

The measured base shell has real issued families and stage facts but `trial=None`, `platform=None`, and no live-source/context observations. It is **not full native constructor/prepare/commit integration**, and its count reduction is not an end-to-end speedup. Unchanged trial/release/use/admission branches were inspected statically. Existing SQL/typed/full-codec accounting exclusions and logical-unit/non-RSS limitations remain. The next actual bounded validation, if separately user-authorized, must still establish both original commits and normal final-context return with all original deadlines; first commit or wall time below 30s would not suffice.

Original artifacts under `/tmp/sim2act-base-cohort-20261021/tests/`:

| Artifact | SHA-256 |
| --- | --- |
| frozen-before.json | f78802a7ff3a52dfd22cda57bb8e83a3ced31836af7dbcb3600d9190a74cb312 |
| frozen-after.json | 9f917146143139776f19d7423f66bd770e9ae44bbb93407c14f5cc33964ba86e |
| frozen-final.log | ab529636b388cae5f605f81855cf2c2c86504ec4bdccbe5cf5da24534638c4c2 |
| frozen-final.xml | 00312c82a01ced54f51254705e30e1c7489391cd0fa368632e4c192edce99015 |
| initial.log | efb62a9d23259025a7efe3e86e7fe9bfe8506ccc42712637a21c83971537ad0d |
| closure-dev.log | ba4a907b273b391e48e99d0021e2bc7f77079777111afc17241452b993b136e1 |

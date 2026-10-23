# Cold whole-frontier comparison candidate: withdrawn

**No G0 pass, no complete candidate equivalence pass and no performance improvement are claimed.** The tested candidate is `0c36b88fbead2fe07f8a60cdc51cbbc4f2dafd62`, directly after `fd73d3fb73a7a74af60c2911209a8e3ca31bd4d7`. All seven candidate files were withdrawn after the single bounded run ended. Active `src/`, `scripts/` and `tests/` are byte-for-byte back at fd73: [861-file restoration vector](source-restoration.json). The candidate commit, complete binary patch, seven source snapshots and failures remain inspectable.

## What was implemented

The default-off native frontier retained its original expected SHA and original new-root hashing. An optional **fresh whole-envelope immutable event projection** encoded exact types, insertion order, shared references, string/bytes identity relationships, float bits, complete RowMapping keys/data/safe index and complete Limits. One memo covered the fresh PB projection, inputs, role limits, phase and binding metadata. No mutable source reference escaped into a retained baseline; every invocation read the graph again.

Independent bounded selection preceded verification. Unsupported/over-budget selection retained the original SHA verifier; a selected verification mismatch/exception did not retry. These limits belonged to the optional extra work, not the owned capability ledger, business acceptance domain, CPU, RSS or whole process. Baselines were scope/hash bound, discarded on exact new roots and released at close. New-root publication rechecked the old domain. Baseline publication required original-SHA confirmation followed by a fresh whole-envelope self-comparison. The private value-return branch rejected foreign projected maps. No business/origin byte export was replaced by the event protocol.

No lease, transaction, SQL, authorization, revocation, Run/fence, stop or final-clock gate was removed. No real-clock launcher or G0 window was opened. See [design and limitation](design.md).

## Actual local verification

The files in [originals](originals/) preserve each execution separately; these are not one combined suite or all tests on a final production version.

| Execution | Actual result |
| --- | --- |
| Component initial | 24 PASS / 1 FAIL, 0.21s. Test incorrectly assumed SQLAlchemy RowMapping deepcopy preserves pickle aliases; assumption corrected, failure retained. |
| Component corrected | 25 PASS, 0.23s. Strict type/alias/hidden-data/float-bit/cycle/budget/no-foreign-callback tests. |
| Initial real SQLite integration | 6 PASS, 8.78s. |
| Extended SQLite integration | 9 PASS, 13.28s. Includes real PB caps/key identities and unknown adapter selection. |
| Publication-binding run | 9 PASS / 1 FAIL, 14.48s. New fault injector changed source but not the actual projected table, so did not inject the intended transient drift. |
| Corrected targeted publication tests | 2 PASS, 3.08s. Injected B→A into both actual tables; rejected before baseline publication, foreign projection rejected. |
| Existing supervisor units | 7 PASS, 0.05s. |
| Frozen full pair | **1 FAIL**, 440.93s pytest; see below. No retry. |

The tiny real-SQLite component screen included selection/projection/comparison: 400 calls per arm, 20 alternating batches, 15,128 original bytes/call. Initial sums were original 2,832,047ns vs candidate 13,784,748ns; corrected sums 2,262,686ns vs 14,102,105ns. Both screens were slower, **not a full-tail ratio or prediction**. Ruff and diff whitespace checks passed before freeze; the archive retains the exact frozen source.

## Single full-pair result

Command on frozen 0c36, clean worktree:

```
.venv/bin/python scripts/run_cold_row_semantic_pair.py --case frontier --output /tmp/sim2act-frontier-complete-pair-20261023
```

One original configured prefix, two independent first-Cold copies; explicit synthetic business clock and existing three test-only qualification substitutes. Real Store/Worker/SQL/approval/ledger paths, HTTP limited to Mock. Hard admission caps **7 Mock exchanges / 9 entries**, no automatic retry; outer **600 seconds + 10 cleanup**, sampled **64 MiB** disk monitor (not native quota). Original lease30/Run300/TTL and all runtime gates unchanged. Cold2/W5 and real model calls forbidden.

The original arm produced its complete report, strict outputs, SQL/parameters, receipt and original final sample. It reached prepare, both commits, receipt and normal scope return: **43.357651307 thread CPU seconds / 43.598850574 wall seconds**, **8062 codec calls / 4,682,215,371 returned bytes**, **275 qualified base entries**, 7735 SQL statements and two Run predicates. These values belong only to that arm.

The candidate arm did **not** produce a report or strict output/SQL/receipt files. The actual exception is:

```
tests/test_cold_configured_semantic_tail.py:188  self.clock.healthy()
tests/cold_semantic_clock.py:87
AssertionError: Semantic regression exceeded real 300-second test budget
```

This is the existing test-clock helper's independent real-time budget, not the production lease predicate and not outer 600-second timeout. The traceback places it after the original context returned and `scope_returned=True` was assigned. That supports only a **control-flow inference** about return; the following assertions and final A/B comparisons were not executed. Candidate CPU, codec count, actual selected-route count and strict final equivalence remain **UNKNOWN**. No values are reconstructed or borrowed from the original arm. A heartbeat thread also reported the same budget assertion; its warning is preserved.

[Supervision](originals/supervision.json): `FAILED_OR_UNKNOWN`, exit1, stop_reason=null, **443.411774160s** total, **7 exchanges / 9 entries / 2 Source delegates**, zero automatic retries. Sampled peak **10,216,064 bytes**, 4418 samples, actual intervals 0.100188–0.105120 seconds. **564 frozen files unchanged**. Self-owned process group absent; no supervisor errors or signals required; cleanup elapsed 0.000051748s. This is process cleanup evidence, **not a passing test-level normal-cleanup assertion**. Fixtures were preserved, not deleted or resumed.

## Disposition and remaining gates

The Python event projection has no acceptable complete-tail result and no demonstrated net benefit. It was removed from the active tree, including its optional switch and test-only supervisor branch. The pre-existing 300-second helper was not relaxed and this test was not rerun. The original gates remain. No old UI/native verification was repeated.

This failure does not prove a 30-second G0 is impossible or that a source-owned immutable representation is unsafe. It rejects this implementation for adoption. A next implementation must reduce whole-graph work **including selector/baseline overhead**, retain full source alias relations and fresh dynamic/exit gates, and produce a complete old/new tail before any real-clock qualification. No new C leaf, cache, transaction split or lease extension is implied by this archive.

The independent real-account path remains blocked at `production_evidence.resolve_account` (`SOURCE_MISSING`): an authoritative same-account identity/entitlement and enforceable no-new-charge source is still missing. Developer JSON, a token or synthetic facts cannot provide it. PG/current-provider/real-clock G0/owner semantics and overall F2/R0 remain unverified; none are raised by these tests.

## Readback

- [Full run inventory](originals/full-run-inventory.json): **17 originals**, 10,216,873 bytes, including both actual SQLite fixtures, prefix fixture, old strict records and all logs. [Lossless archive](originals/full-run.tar.gz) was read back member-by-member against every length/SHA.
- [Candidate patch](originals/candidate.patch.gz) and [seven candidate files](originals/candidate-files.tar.gz) match Git 0c36 exactly.
- [Manifest](MANIFEST.json) covers archived evidence bytes. [Independent review](independent-review.md) separates pre-run design ACK from failed execution and restoration review.

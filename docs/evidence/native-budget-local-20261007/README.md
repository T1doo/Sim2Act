# Sequential fixture preparation reuse — local evidence only

Base e828c066ec63689fe5de5d66f650eda33c0086e8; final source ff58011ad804fb41cb93205344a541f62babe783. Only three test files changed; product, native driver, workflow, PowerShell, permissions, runner, cache and all timeouts/output slots are untouched. No push/CI/full runtime suite/LIVE request.

Windows run37621453354 / product b2328e4 was CANCELLED912s at15min. Engineering741s / pytest730.12s (1028PASS18SKIP), Edge cancelled110s with incomplete new receipts. Read the original checked evidence under windows-bounded-native-b2328e4-20261007. Four global gate cases total53.31s; repeated registered browser initial seed setup costs are also visible. Old shared cases were broadly slower in this run, so total growth is not attributed entirely to the added code.

Final global cases each retain their own complete old sealed database/files/clock/experiment/receipt. The module fixture performs normal seed + actual old4Mock source/review/extract/cold/default/recover once, closes its stores, and yields an immutable template. Copies start with exactly the same file hashes, four Attempts and five jobs, including experiment markers. Every original ordinary/-O/project child and actual Worker probe remains; QUEUED-zero and pool/Attempt/authority fingerprints are checked. The template is rehashed after cases and module teardown. Registered-generation cases independently copy a normally initialized closed seed and keep all original source/generation/cold/revoke/tamper assertions. No mutable case state is shared, new registered successful Run/generation is not seeded, and no marker is removed to bypass a gate.

The first candidate using mutable sequential global state is retained as history (`candidate-groups.log`,21.45s); it was superseded for isolation. Final timing samples are in comparison.json. Baseline first sample is4cases20.76s +6cases14.37s =35.13s (two launches). Second exact baseline combined10 cases41.66s; final candidate identical10 cases22.57s and20.26s. All PASS/0SKIP. Sequential runner samples have load/noise and differing initial launch count; local savings12.56–21.40s are not a Windows guarantee. Both baseline and candidate use the same owned interpreter and unchanged product sources. Detached baseline source tree and own venv are retained locally, not published as recovery bundles.

Commands for combined groups:

```
python -m pytest -q tests/test_global_experiment_gate.py tests/test_product_integration_fixture.py tests/test_registered_generation_browser_fixture.py --basetemp=<owned unique root> --durations=15
```

The detached baseline command additionally overrides pythonpath to its own src; child imports use the unchanged identical product package through this task's venv. No editable old-tree import is installed. All1046 ordered collected nodeids match exactly (collection-receipt.json); collection is not full runtime regression. Four final independent global probe receipts retain actual errors and unchanged seals.

Budget remains NOT_RUN: a net Windows saving S must exceed12s + unknown unfinished native cost U + desired margin M. No local latency multiplier can establish S/U. Keeping source/cold/report phases or reordering them earlier cannot turn incomplete tests into job success. A future controlled execution-design study can measure isolated PG fresh-schema DDL and native phase timing before considering overlap; this candidate contains neither overlap nor DDL change. No budget increase is proposed.

Decision is **NO_GO for another CI on this evidence**. See budget-decision.json and Plan: proven Windows saving0 leaves912+U; using unverified Linux20s still leaves892+U without margin. A complete Node150+historical npm13/emission7 planning allowance plus15s reserve gives967s before unknown seed/other overhead. This is an execution envelope, not a new measured Edge duration. The candidate may be independently merged as safe fixture reuse, but does not remove the900-second blocker.

# Isolated native producer handoff — partial wiring, NOT qualified

Base: 239fbea5a9df7c605fd9a20af4c3363ebf0f78b8. Normal development branch only.
No launcher, complete prepare/commit, G0, Cold2/W5, browser, CI, model or Mock transport was executed.
SQLite fixtures seed synthetic facts through the existing local TestClient; this is not a zero-DML database test or provider attestation.

## Actual implementation

Direct native copying retains exact model/container types, per-capture DAG aliases, model __dict__/raw aliases, and complete RowMapping keys/data including hidden positions. It never thaws _Image. Foreign index keys are iterated without invoking hash/equality; only the original safe lookup is rebuilt. Unknown mutable quoted_name.quote is unsupported rather than borrowed. Each handoff has a fresh memo; old mutable source identities are not used across versions.

The real _ColdTrialGraph now explicitly receives optional _owned_models, guarded as isolated test-only SQLite. All 18 original _graph_trial_produced call sites retain their original producer/guards/order and rebind both actual model and raw cohort to the transferred pair. Source observation returns the exact new model to both callers; already transferred Source pairs are freshly checked and reused rather than copied a second time. RunCheck context stores its paired new model/raw. _base, dump and producer entry check current native serializer/schema qualifications before presenting copied models to serializers. Unknown qualifications and original validation errors close the new owner and invalidate the graph. Default callers install no owner. No full guard, dynamic/SQL/authorization/clock/lease/fence/epoch boundary was removed.

This is a mutable native representation held privately by the experimental bridge, NOT a language-enforced immutable object and NOT a proof of a read-only/no-escape consumer closure. Existing output/public byte contracts are unchanged. Byte equivalence is demonstrated only for the tested Limits/RowMapping cross-root graph and actual Source/Generate row inputs, not all seven families.

## Actual validation (not cumulative unique test counts)

Commands: .venv/bin/python -m pytest -q tests/test_cold_settlement_owned.py --junitxml=<matching XML>; final combined command also includes tests/test_cold_base_single_content.py; targeted command selects test_real_base_source_and_context_adopt_one_pair_without_second_source_copy and test_native_full_entry_exception_releases_owner. stdout/stderr and JUnit originals are preserved here. These logs were copied after the runs; there is no independently recorded per-run pre/post source manifest. source-manifest.json binds the final candidate, not an invented historical timestamp.

- first: 19 PASS / 1 FAIL, 7.12s. Real write-epoch rejection left owner active because current() was outside the cleanup try. Fixed in candidate.
- second: 20 PASS, 7.14s, before later review changes; not final-version acceptance.
- third: 21 PASS, 7.27s, before Source/quote and cleanup fixes; not final-version acceptance.
- fourth: 23 PASS, 10.42s, before final cleanup additions; not final-version acceptance.
- final combined: 54 PASS / 1 FAIL, 60.40s. Runtime source matches source-manifest; the component module docstring was corrected after this run to describe its explicit opt-in import (executable definitions unchanged). Pre-doc-correction component SHA256: 2460e1f00db6bd1b737b46338eaeae5c95c0db422e1ff11d07aa76845aabe383. Source boundary fixture used an unlisted 'isolated-source' root; the ORIGINAL native continuation whitelist correctly rejected it. No product gate changed to make it pass.
- targeted: 3 PASS, 2.68s after changing the fixture to existing commit:first roots and adding two whole-entry cleanup cases. Product executable definitions unchanged from final combined run; test source differs by this fixture correction and added cases. No claim of a single 57-PASS run.
- Ruff check of the component and its test passes; git diff --check passes. Existing runtime file is not claimed to have a repository-wide Ruff/typecheck PASS.

Tests cover direct old-byte/cross-root alias equality, real SQLite Approval producer and cohort rewiring/default identity, later fresh version after original mutation, actual Source/Generate accounted batch consumed by the original pure archive-chain verifier, cycle/nonfinite/unknown rejection, write drift, capacity/partial-constructor failure release, unknown serializer no-call rejection, and exact native Source/RunCheck boundaries under real CGR/_base. The latter uses an explicit synthetic SourceVerificationResult and existing issued fixture, not a trusted provider producer or full settlement chain.

## Independent review and remaining implementation

Existing readonly reviewer next_ui_slice_review inspected the saved source without tests/network/writes. Final limited source ACK: original/default order retained; source rebinding, fixed serializers, quote layout and full native error cleanup corrected; no definite new default-path blocker found. This is not performance or execution qualification.

NOT CLOSED: full _ColdBindingGraph content/dynamic-reader separation; journal/Source/Generate and nested complete/stage/raw source unification; nested gate/archive additional producers; complete Run/role Limits/call/raw/parsed/receipt plus outer _ModelSettlementRead settlement tail; whole-run pre-issuance capacity/LEGACY routing. Current finite per-copy ledger closes on overflow and is explicitly NOT a compatible production acceptance-domain proof. Bounds here remain fixture allowances, not product limits or RSS promises. Later stages need explicit fresh handoff versions and no mutable-source id/PASS reuse.

Consequently no guard exemption, accepted-domain replacement, runtime enablement or net benefit is claimed. The candidate currently adds copy/qualification work while retaining all old checks. A timing comparison now would measure incomplete extra work, not an admitted optimization. Full tail cost/benefit must wait for actual consumer and capacity closure; this is an implementation remainder, not a new user permission request. Production account SOURCE_MISSING remains a separate gap, and this synthetic experiment does not change it.

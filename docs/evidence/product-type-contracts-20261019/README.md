# Existing source type-contract repair evidence

[Implementation, exact scope and remaining failures](../../F2/ProductTypeContracts20261019.md).

Baseline is `5f5f964906792433d51140871d9d7b7aab365de0`. Full original mypy reports 31 errors in 10 files, checking 113 source files; the frozen candidate checks the same 113 files with zero errors. Eleven product files change, including the shared private exception evidence contract. Type configuration, locked dependencies and test source are unchanged.

[Raw evidence](raw-evidence.tar.gz) and [package receipt](package-receipt.json) preserve author source snapshots, full before/after type output, unchanged full Ruff failures, exact command records, JUnit/stdout/stderr, synthetic SQLite artifacts, passive observations, public schema/serialization comparisons, observer errata and independent reviews. Generated caches are excluded. Pytest convenience links are inventoried and not archived as links.

Author seal: `253de8ccbde6458d33437d58b17d1385a00b7c19b1fca41c2881111f3866b1f4`, 1,588 regular files / 59,723,526 bytes plus 47 convenience links. Original author root: `/workspace/mypy-product-types-20261019`. Original independent review roots: `/workspace/mypy-product-types-review-20261019`, `/workspace/mypy-product-types-v2-review-20261019`, and `/workspace/mypy-product-types-correction-review-20261019`.

[Independent source review](review/final-independent-review.md), [V2 fixture attribution](review/independent-attribution.md), and [final regression supplement](review/final-independent-supplement.md) are also directly readable. The supplement preserves both baseline failures, the successful candidate isolated rerun, and the distinction between Worker heartbeats and actual Run lease renewal.

The actual selected batch remains **60 PASS / 2 FAIL**. Original HEAD reproduces both failed assertions; an unchanged candidate isolated MD rerun subsequently passes. No failure is deleted, marked expected, or relabeled as a passed batch. The full Ruff gate remains **FAIL with the same 117 diagnostics**. The full type gate is PASS. Read `author/qualification-summary.json`, `author/observer-limitations.json`, `author/baseline-regression/retry-1/post-run-observer-erratum.json`, and the independent reports in the archive before attributing causes or aggregating counts.

All execution uses synthetic inputs, Mock models/transports and local SQLite. Real provider requests are zero. No new Windows, PostgreSQL, native/browser, remote CI, real entitlement, semantic/human acceptance, release or deployment evidence is claimed. Existing old missing review evidence is not recovered. Commit/push and independent remote SHA verification receipts are maintained outside these immutable seals in `/workspace/mypy-product-types-delivery-20261019`.

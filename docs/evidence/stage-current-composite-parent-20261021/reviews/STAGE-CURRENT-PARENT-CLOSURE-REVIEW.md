# Third stage parent: limited source and evidence ACK

**ACK for the frozen single-call-site runtime change and the author's local evidence below. No remaining blocking finding was identified in this scope.** This is not a G0 result, performance/lease acceptance, completed receipt continuation, or execution grant.

Base HEAD is `e4dddb1c8fd9a67a622e5d69c8637e07a38f8836`. The reviewer independently read the complete source diff, relevant helper/predicate code, test changes, author logs/JUnit and hashes. No test, DB, product, Mock, model, G0, profile or signals were executed, and no repository file or grant was written.

Final source `src/sim2act/natural_live_admission.py` SHA-256 is `84195d0061f965b8f1cc2e1bc385941c2739e09dce02293596b3025f14b4433a`. Final test `tests/test_cold_accounted_stage_pin.py` SHA-256 is `9265b2ea628a34c9a93604e6688c41eada81dd2974845b08f8d13bdaf21a5392`. Both match the final closure manifest/current files. The complete runtime diff replaces only `_graph_stage_current._parent_pin`'s original full-pin/stage-raw pair with the already-reviewed composite helper. No other source, launcher, guard, prefix, codec, native/receipt protocol, profile, budget or deadline was changed.

The composite retains original first full CGR/frontier pin, then all dynamic/frame/link and stage/family/Run predicates for exact ready native mode. Default/non-native paths still perform the original pair. The same lexical pure join does not issue a reusable pass; later calls still make a fresh full pin. Scope leaf checks and public assertions remain. Typed cohort validation still follows the parent, and all original `_graph_stage_current` approval, authorization, current-pointer/SQL/callback-return, recipe/origin, fence/stop, authority and deadline gates, plus invalidation-on-error, are unchanged. The runtime now has exactly three explicit composite call sites: stage-current, run-context and Source resolver. No frontier wildcard or pass cache was introduced.

The original targeted batch remains **28 passed / 2 failed**, 30 total, 46.50s (JUnit 46.502). Its codec assertions counted two extra first-use encodes outside the parent. The corrected local test observes the exact original lazy release-pointer addition and its separate two-codec span through the real stage reader; it then compares old and new adapters with the same root set. It does not merely loosen the assertion. Source observes old/new total codec 376/226 with 25 parents; Cold observes 754/526 with 38 parents. Every measured parent is exactly 7/1 codec calls. Family/Run sequences, authority fingerprint and returned job agree (Source family/run counts 78/51; Cold 119/39). These are call-count observations on isolated synthetic SQLite helpers, not an end-to-end speedup or timing promise.

The final broader author regression is **115 passed**, one existing warning, 207.52s; JUnit is 115 tests, zero failures/errors/skips, 207.516s. Independent testcase counting gives 30 stage-pin, 27 native, 22 receipt and 36 SQLite tests. This batch binds the earlier test hash `a6bcdedb5f92fa69a662fbee2840cb98f10dfcccbfd09468b28233a928d85627`, independently matched by the saved byte-for-byte `before-assertion-narrowing.py` backup and frozen before/after manifests. Source was the same final `84195...` hash.

After that batch ended, the test's four Source/Cold × mutation/revocation cases were strengthened to catch the actual second-call DomainError inside the scope, rethrow that same object through cleanup, and require it to be non-None outside. An unexpected first-call/scope-entry error therefore cannot satisfy the test. Independently reading the backup/current diff confirms only this test function changed. The author then ran those four cases on the final `9265...` test hash: **4 passed**, one existing warning, 7.20s; JUnit 4 tests, zero failures/errors/skips, 7.203s. Source remained unchanged. These overlapping batches are not 119 independent tests, and the 115-test batch is not represented as a whole-suite run of the final test-file bytes.

Ruff passes on the final closure. Mypy passes the one unchanged-since-broad-run source file. No repeat of the broad suite is needed to claim the narrowly stated evidence: 115 on the earlier test bytes plus four changed cases on the final bytes. Historical failures remain preserved. This review does not establish full native prepare/two commits/context return, either new receipt root, G0 or original final deadlines. A duration below 30 seconds or first commit alone would not substitute for that complete outcome. Any later single bounded window remains the parent's separately user-authorized operation with its unchanged protections/profile/limits and exact frozen grant; none is created or expanded here.

Evidence under `/tmp/sim2act-stage-current-parent-20261021/tests/`:

| Artifact | SHA-256 |
| --- | --- |
| frozen-before.json | 28d412db795afb22140e5996cc3803717f744917c49ea68207f0be74bde5de76 |
| frozen-after.json | 60ed99a5fb1fa2470e128da8c32e11e9331e279c456f67979e39836de4b8ea3a |
| frozen-final.log | fde95a00534552e91ca173b295f9fdfd2497fdba7fcb5d8d9e21e8d15407ee1d |
| frozen-final.xml | 0e0f26a937880bd9ca165241fbf16fd145b5d971333fbf28690a4924c70ac2db |
| closure-before.json | 520019853057f49c690dc4888e6b4423f6049834e83f96c2bd6ea4a3537b2077 |
| closure.log | 3e8fa1961fc0ba919c947174411b2277f2a95b6da07b9e0d79564bc6069039f9 |
| closure.xml | b3f2de8608f7debe0bc1de2154f620045d3edd53ff9847b38a34b6374501a64d |
| ruff-closure.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| mypy-frozen.log | 5d4b6d285b77932e3d08212c3b4974d0a803f98ec60408ac6ccf6a063fa6c19e |
| targeted.log (failed historical batch) | 0bca3fbbe21549c2065dd03894f7d79e1a3ad80d6a88446b291ac0e4afcba954 |

Earlier static/pending review is retained separately in `STAGE-CURRENT-PARENT-CODE-REVIEW.md/json`.

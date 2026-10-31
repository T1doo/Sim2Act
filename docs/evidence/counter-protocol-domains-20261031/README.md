# Counter fixture failures: complete classification and contract repair

Application source remains **d6d07d574015c02a4a86341d492ea0628c9cc2d7**, preserved evidence HEAD **d058eeb7938af476c87accc3e4d82e464e4134ec**. This stage changes test fixtures/contract coverage only; it makes no product-performance claim.

The old24 failures occurred before counter execution: an origin-reuse fixture left construction-only callback stubs installed, violating the real Source code witness. Restore those stubs before entering the counter scope. The FULL25-case control now produces **13PASS/12FAIL on both c6a42c783fd92818654b02e5fb469675877c632a and d6d07d57**. Every case outcome and first failure message matches, not just the first case. Raw XML/logs and exact source path/test hash are preserved.

| Group after fixture restoration | Cases | Current and c6 outcome | Correct domain |
| --- | ---: | --- | --- |
| Default packet hit / fewer pins | 3 | FAIL | Owned seed yields View; old raw segment requires dict/RowMapping and list. |
| Real RowMapping combinations | 8 | 4PASS / 4FAIL | Unseeded mutable mappings work; an independent mapping is not the owned seed node. |
| Missing collection | 1 | PASS | Actual original operations query remains. |
| Bad loaded values | 6 | PASS | Extra slot, duplicate/wrong anchor, wrong mode/context and repeated ordinal still reject. |
| Late mutation / original core exception | 2 | FAIL | No core entry in owned domain, so these callbacks never fired. |
| Unsuitable snapshot carrier | 1 | FAIL | quoted_name value is already refused by canonical Source audit; the counter snapshot was never reached. |
| Unknown copy / JSON | 3 | 1PASS / 2FAIL | Copy/serializer change violates Source code witness; JSON default change uses original fallback. |
| Foreign key | 1 | PASS | No foreign equality callback. |

Repair preserves the original25-case raw matrix in **counter_loaded_cases.py**, including every core count, SQL, row identity, duplicate/mutation, original exception-object and late-pin assertion. A mandatory fresh interpreter simulates ONLY the documented optional Source extension being absent before imports. It asserts real raw representations/qualification, runs all25 cases with0skips and verifies the child JUnit contents. No product gate or available() function is monkeypatched. The unsuitable counter snapshot now explicitly uses an UNSEEDED reader, avoiding an unrelated earlier canonical-seed rejection. The original seeded+unsupported combination is independently retained as an explicit early refusal test.

The shared seeded_reader fixture now honors use_seed=False: it does not secretly create an owned seed first. This is a fixture correction, not relaxing the product constructor's ownership join.

Default native ownership is separately exercised: complete original fallback and immutable-node identity; independent SQL mapping rejection; all three mutable job representations really hit core; original late mutation and exception object; six malformed-value cases versus forced original path; missing collection's real SQL; changed Source code rejects before foreign dispatch; original JSON fallback; job-root/audit-alias/owner/limits/scope/epoch mutation; real finite-interval stop; and retired PRIVATE producer alias changes versus still-live outside alias refusal. A pure read scope is not itself a running settlement, so stop testing explicitly enters the existing finite checkpoint condition; no authority/READY is fabricated.

Final combined run:34 outer PASS in29.89s, including one mandatory wrapper which executes25 raw child cases, and33 default-native cases. One subsequently added seeded canonical rejection case PASS0.83s. These are distinct from the pre-repair25-case control and are not a whole-repository green claim. Independent readonly review found no must-fix contract/test omission. No code, clocks, timeouts, permissions, model calls, Windows CI, PC or main/Release were changed. Model calls0. This does not newly qualify PG/live/Windows or solve the approximately45second writer.

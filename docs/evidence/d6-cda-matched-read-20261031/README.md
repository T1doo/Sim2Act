# Fresh exact-source d6/cda comparison

Keeper HEAD during both runs was `2082be487c62cf7529f5cbb4bedfdb17f934a62f`, clean before and after. Both exact Git exports, all source-file hashes, C/header equality and identical native binaries were checked. The same original large synthetic fixture recipe, interpreter, hash seed, passive observer and diagnostic binary were used sequentially, with no parallel measurement or intermediate candidate. Real UUIDs and clocks differ; this is not byte-identical data or repeated statistical sampling. Observer overhead is included.

| Exact source | Cold | G0 read seconds | Writer seconds | Total seconds | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| `d6d07d574015c02a4a86341d492ea0628c9cc2d7` | 1 | 35.227723 | 51.885513 | 87.114109 | COMMITTED |
| same | 2 | 33.670817 | 50.194315 | 83.865620 | COMMITTED |
| `cda0a740559cf4e1880366ed48d49ab58831b340` | 1 | 34.392091 | 52.186511 | 86.579413 | COMMITTED |
| same | 2 | 34.628712 | 50.499105 | 85.128328 | COMMITTED |

Candidate-minus-baseline totals are -0.534696 / +1.262709 seconds, writers +0.300998 / +0.304791 seconds. This pair demonstrates no net improvement, but is insufficient to prove a stable causal regression. Earlier nonadjacent timings are not substituted for this pair. Neither source meets a stable 30-second G0 target; the 30-second writer-admission/first-DML lease and 120-second settlement deadline remain distinct and unchanged.

The original test passed twice, each invocation containing two Cold saves and seven FixedMock requests, zero real model requests. cda's **first** new-process read-only reopen then passed before evidence archival/database queries. Run SUCCEEDED, one persisted result version, two Cold VERIFIED attempts, and saved HTTP output equals both app output and typed result. Main database SHA256 `6e78a5d5a7e3592bca80d8b80fd7512fabd26c63a3206b2caec541e0de545478`; logical SHA256 `2502a4be60b93ae0344c5fc107f78e933b98813a4fe28bc3c1858bbb0cef5abe`. The readonly connection created an empty WAL; absent-to-empty is reported explicitly, not claimed physically identical. Nonempty WAL must remain identical. The prior unchanged cda source's real G1 writer-cancel proof remains in `../g0-owned-pre-read-20261031/`; it is not a new cancellation measurement from this matched pair.

## Original 24 failures versus the complete 25 cases

`counter-original24-complete25-crosswalk-20261031.json` joins **each exact testcase name** across original, restored d6, restored c6 and repaired raw runs. Original 24 failures all used the construction fixture with stale origin stubs. The 25th case, `test_foreign_native_keys_are_refused_without_equality`, is fixture-free and passed originally. Restoring construction-only stubs makes 12 of the former 24 pass; the remaining 12 fail identically on c6 and d6. Thus the full control is 13 PASS / 12 FAIL, not 12/24 or a claim about one representative failure. After correcting the raw/native test domains all 25 raw cases pass, zero skips. The original assertions and default native counterexamples remain; see the separate complete classification in `../counter-protocol-domains-20261031/README.md`. c6 JUnit lacks classnames because its suite was outside the invocation root; the join uses its full exact 25 testcase names, not an empty classname filter.

## Bounded decision and next code scope

The matched observer's largest named exclusive bucket remains prepare (G1 d6 13.692 / 12.858 seconds, cda 14.644 / 13.409), with uncovered residual 18.924 / 18.660 versus 19.635 / 19.353 seconds. These nonoverlapping buckets are in the comparison JSON; nested graph/typed costs must not be added to them, and residual is not attributed to IO/fsync.

Readonly review rejected sharing a mutable left/right projected dict: a PEP 669 function-entry callback can mutate only `actual`; original independent projections reject, while an aliased pair could pass. Combining native strict-equality validation traversals is technically plausible but its actual default-path time share is unknown. Making SourceView a comparison leaf is also unproved: its owner already uses immutable inventory; remaining reducer-produced tuples retain callback/alias/work semantics. Neither speculative candidate was enabled or measured as a speedup.

The planned code change retracts only the unproven owned read-fusion activation while preserving the 24/25 test-domain repair, original raw read domain, and Registry/unknown-callback safety checks. It will be frozen and tested separately; this evidence commit does not claim that change is implemented. The first attempt to start that command was rejected by a disconnected exec transport; on recovery Git was still clean at keeper HEAD and no retraction test XML existed. No unknown process was stopped or restarted.

Archives contain only synthetic pytest databases/inputs. Exact injected credential values were checked internally and absent; no secret values are printed. Linux/SQLite/test-only Mock evidence does not newly qualify Windows, formal PG or actual live-model semantics. No timeout, permission, main, Release, Windows CI or user-PC action was changed.

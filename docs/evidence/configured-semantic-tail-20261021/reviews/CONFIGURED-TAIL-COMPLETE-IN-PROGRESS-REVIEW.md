# Configured synthetic tail: frozen source and partial results review

Status: **limited code ACK; complete-suite evidence pending.** No identified new P1/P2 in the reviewed changes. This supplements, rather than replaces, the earlier 12/14 checkpoint review. The reviewer performed only file reads/hash/comparison and wrote this report; no product import, test, Mock, database opening, process signal or repository edit.

The five test and two product SHA256 values read from `freeze-complete.json` match the current files:

| File | SHA256 |
| --- | --- |
| tests/cold_semantic_clock.py | 0a5e8964b62762209b24fa97a6bde49727a60ef84eb0463d7330b63579d0511d |
| tests/cold_configured_tail_fixture.py | 2d1923883f5bb8539b53b8c9ee24ff5b11f863d3c6110e9090039c179b210e0f |
| tests/test_cold_configured_semantic_tail.py | bf5197fe58b9176a9f3abb4effdd62679bb170ff215ce1438b85bd538a6853a7 |
| tests/test_cold_semantic_clock.py | 96e3e9314f74be25617fdf955ef5d4d4ccfb168308435905043a97a45ff342a5 |
| tests/test_cold_tail_output_encoding.py | 20a301b45d3f5c99f98c2312ec0f2eac5710008f82c32c9e1409a68f7fc733c4 |
| src/sim2act/_cold_policy_segment.py | ad7ee006d6596d41b3ed5511119609ac773a8eb75ccedf242ca74b0e9fb44751 |
| src/sim2act/natural_spec_runtime.py | 6f91a55bdfbb37fc1b9f571d030692087b664c078dcd9b043844c1e8b379dcc4 |

`git diff --stat -- src scripts` is empty. The source comparison named old/candidate changes only the two policy wrappers back to their original guarded policy calls; the other current native/typed implementations are shared. It is not an A/B against the entire historical runtime.

The explicit checkpoint now preserves **7 exchanges / 9 method entries / 2 delegates**, including the additional failed diagnostic-encoding case. MockCap checks the **13/15** development-suite cap before dispatch; each of the six subsequent cases permits at most one exchange and one method entry. Final expected totals are checkpoint-prior plus six, hence **13/15/2** for this frozen input. No accounting reset or failed Cold database restoration was found. The original untouched prefix byte hash remains the selected template. The changed cap is a local synthetic test allowance, not real-account authority or a production grant.

`checkpoint-after-report-error.json` SHA256 is `2f1d3aa4821a1919b728cab23aed7423796a6ee23d2efb3641492a3cfe2dae01`. Its reconstructed provenance and prior failed cases must remain disclosed. Template row predicates remain the owner's reported read-only reconstruction; the reviewer did not open the database.

The diagnostic encoder explicitly represents an exact SQLAlchemy `quoted_name` by text and quote flag, including dictionary keys; bytes and list/tuple distinctions retain tags. It rejects other unsupported values. Business context/source fingerprints and actual output equality remain separate. The additional pure encoding test checks JSON serialization and preservation of both quoted-name flags. No business value conversion was added.

At review time the `old` and `candidate` files in `pytest-complete/test_complete_configured_old_c0` each record actual prepare, both commit returns, the precisely filtered Cold receipt, and normal original context return. Both record no error, two Run predicate calls and 7735 observed SQL statements. `complete-original-outputs.json` is byte-identical between them (SHA256 `01cb964d2d5ae30239ae15b5cd56705cf435e16eb326f6bb9106cdfc79bc76e1`). These observations and their observer placement support a successful configured virtual-clock C1 semantic tail for each arm. They do not establish W5/Cold2/business completion, production qualification or real-time G0 success.

The observed codec counts are **8373 → 8337**, returned bytes **4920607268 → 4894540040**. This is a local instrumentation delta, not CPU/RSS/speedup proof or complete accounting of new helper work. The positive reports' business time is `1800000300.0`, explicitly `real_clock_acceptance=false`.

Already-read negative files: final-expiry records two commits/receipt but the original post-scope deadline DomainError and no normal context return; mutation records only first commit and exact `VERSION_CONFLICT: Native mutable frontier changed`, with `fault_applied=true`. The reviewed code also requires precise source-revocation rejection and a real SQLite CHECK-275 same-transaction rollback with zero persisted probe rows. Unknown errors do not satisfy these negative oracles. Their complete final outcome, final ordered SQL equality, cumulative totals and final thread cleanup require the terminal suite result and final summary, which were not yet available for this partial ACK.

The prior union-thread cleanup correction remains intact. Case result files are written before their `finally` cleanup, so their presence alone is not cleanup proof. Final suite assertions are required. This report authorizes no execution or retry and does not manufacture an integration pass while the run is still in progress.

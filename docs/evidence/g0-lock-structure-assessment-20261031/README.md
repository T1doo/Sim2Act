# Long-writer structure assessment

Application remains **c6a42c783fd92818654b02e5fb469675877c632a**. The observed clean source HEAD was **393f39d3259e0f4f8534f080ddc10070107f8fe9**, with no `src/tests` difference from that application. **No runtime optimization or cross-epoch reuse was enabled in this round.** The small pure-compilation plan was measured and rejected as an insufficient long-lock fix. The larger expected-post bridge is specified below but is not implemented or qualified.

The preceding real-clock acceptance remains separate: two G0 reads **28.606365 / 30.158634 s**, atomic writers **42.875907 / 46.210886 s**, totals **71.483225 / 76.369980 s**. Actual locked-cancellation G0 was **28.026949 s**. Those saved/reopened/cancelled fixtures were fixed Mock, not real Intern or formal PostgreSQL. See [the preceding acceptance](../g0-effective-single-publication-20261031/README.md). The original 30-second admission/first-DML interval and finite 120-second whole-settlement policy are unchanged; neither sample establishes a stable 30-second solution.

## Bounded measurements

1. Original binding component with its full ancestry oracle, five fixed Mock exchanges, two real pre/post Graph lifetimes: exit 0, test duration 38.147 s. Post first binding took 9.033 s; the measured natural `expand` and `compile_candidate` exclusive times together were about 0.03258 s. Moving this pure calculation cannot materially shorten that path.
2. One complete Cold through the original five writes, original `_model_settlement_read`, closed proof, VERIFIED Attempt and COMMITTED original transaction: exit 0, test duration 144.258 s, six fixed Mock exchanges, zero real requests, no Cold2. This is **explicit virtual business time**, with existing synthetic environment/account/software/heartbeat fixtures. It is CPU/structure diagnosis, **not real lease acceptance or first-process reopen evidence**. Core Graph, `advance_model`, settlement and receipt callees were not replaced by this diagnostic.

The observed G1 context lasted **43.916816 s**. The following times are exclusive among the named observer targets, not independent inclusive sums:

| Target | Calls | Exclusive seconds |
| --- | ---: | ---: |
| Structural selector, including qualification and native comparison | 10,254 | 12.712827 |
| Complete typed cohort validation | 3,307 | 5.346373 |
| Graph dynamic validation | 12,066 | 4.661905 |
| Settlement proof check, own work | 407 | 4.472626 |
| Receipt reconstruction, own work | 3 | 3.909735 |
| First binding, own work | 1 | 3.131097 |
| Actual graph encoding | 815 | 2.915626 |
| Binding facet, own work | 1 | 2.199586 |
| SQL execution | 8,175 | 1.029045 |
| SQLAlchemy commit | 2 | 0.001622 |
| Measured natural expand plus compile | 29 + 20 | 0.059203 |

Natural expand plus compile account for approximately **0.135%** of the G1 context. This excludes neither their input checks nor hidden time by subtracting nested inclusive figures. It is a bound for these measured functions, not an assertion about every compiler in the repository.

The structural-selector target does not separately time its configuration qualification and native content comparison. It is not evidence that all 12.7 seconds could be moved or removed. SQL commit is measured at `Connection.commit`, not as a separate fsync trace.

The observer remained active after the G1 context closed until the original `advance_model` returned. All named exclusive targets sum to **43.919344 s**, including **0.002528 s** beyond the G1 context. This tail includes commit-related work. Do not describe the entire sum as an exact decomposition of only the G1 context. Observer overhead is included; errors and open stacks were zero.

## Why the current lock cannot simply be released

`_sqlite_model_snapshot.transaction` already performs G0 in one WAL read transaction. `promote` retains that driver/transaction; the first actual UPDATE starts the measured writer interval. Five writes and all original post checks then precede one atomic SQL commit.

| Work | Required current position or condition for moving it |
| --- | --- |
| Attempt/operation/app-state writes and two events | Preserve the original atomic transaction and actual rowcounts. |
| Actual VERIFIED Attempt/Operation, wire/usage/receipt and journal chain | Read actual post data; an expected value alone is insufficient. |
| Protected-read authority, approvals, revocations, owner/version/fence, stop and both clocks | Retain fresh checks at their original boundaries, including before protected reads and before commit. |
| Source/Generate lineage and pure semantic reconstruction | A pure owned result may move only after complete current data/code/schema dependencies and actual post effects are proven equivalent. |
| Mutable Graph and typed-cohort integrity checks | Keep full checks while any consumer still observes the original mutable objects. A saved identity/hash/PASS cannot replace them. |

Existing Graph, audit seed and reader objects bind the original nonce, epoch, phase, driver and transaction. Reattaching them to G1 violates their contracts. The existing `ContentPlan` still calls full `spec.bound` in `read_current`; merely enabling it does not remove G1 reconstruction.

## Tested refusal boundary

The new lifecycle-only counterexample uses a fresh real SQLite WAL Store, original `transaction/promote`, exactly five UPDATEs and `total_changes + 5`. A diagnostic callback registered through the original SQLAlchemy event API changes a Python dependency on the fifth write; the transaction commits, while complete `OwnedValue.matches` correctly rejects the changed input. **This is not the product's five-write, authority or full-G1 acceptance test.** It demonstrates the absent callback-purity proof at the lifecycle layer.

The two existing borrowed-snapshot/ABA counterexamples also passed. They show that a later complete Graph check after values are restored does not recover the semantics lost by a borrowed intermediate comparison. The three cases passed in 4.62 s. The new executed test SHA is recorded; XML/log alone are not a before/after frozen-source envelope.

## Minimal structural implementation boundary

The next candidate is an owned **expected-post data plan**, retaining original G1 as a differential oracle until the following conditions are implemented and tested:

Subsequent status: [the implemented SQL endpoint shadow](../expected-post-shadow-20261031/README.md) now observes and replays actual W5 against a complete G0 backup alongside original G1. It reports DATA_MATCH only, keeps reuse disabled and leaves the six larger dependency/authorization gaps open; it is not the full bridge described below.

1. Capture complete pure dependencies: full ordered query results, duplicates, missing-row/range results, complete raw model/row values and all relevant code/schema/serializer configuration. If a reader uses external bytes, those actual bytes belong to the closure too. Do not reduce the set to already observed row IDs or hashes.
2. Prove the same WAL snapshot upgrade and actual writer ownership/lifetime. Record exact original DML shapes, bound parameters, rowcounts and complete postimages. `total_changes + 5` is necessary at most; it is not the certificate. Unknown triggers, UDFs or callbacks must retain the original path or fail safely. Do not clear security callbacks to qualify a path.
3. Give G1 a **new** Graph/scope/Binding. Re-read and fully compare actual post dependencies with the expected owned data, then reuse only complete pure data outputs. Do not transfer Graph/reader/seed, authority, permission results or PASS; do not combine independent role/facet alias domains. Old mutable aliases must be retired across all consumers or remain completely checked anchors.
4. First run the original G1 as oracle and prove equality plus refusal for extra writes, changed source/recipe/goal/limits, negative/range insertions, unknown callbacks, revocation, version/deadline changes and cancellation. Decide fallback before replacing output; late unexpected changes invalidate/roll back rather than replaying producers or SQL. Keep all original dynamic checks and atomicity.
5. Only after closure and independent review should one complete Generation/Source history family replace its repeated pure reconstruction. Then measure the original two real-clock Cold saves, immediate first reopen and real writer-lock cancellation. No claim about speed is justified before those results.

No user permission is missing for this engineering. The blocker is the not-yet-implemented equivalence and effect proof, not free-model authorization. No fifth Windows CI, PC operation, main/Release/deployment, new fee, credential, security permission, training or real-model request occurred. Private synthetic DBs remain private; only byte hashes and diagnostic summaries are published.

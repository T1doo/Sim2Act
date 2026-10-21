# Accounted private component — independent candidate review

Decision: **ACK_UNINSTALLED_COMPONENT_ONLY / NOT_READY_RUNTIME_INSTALLATION**.

No remaining safety blocker was found for committing this unused component and the exact old-body extraction within the authorized scope. This ACK does not authorize installing a consumer branch, removing a pin/cohort/full scan, changing a deadline/transaction, or opening another Mock/model/G0 window. The complete current consumer path still uses its old checks.

## Scope and verification actually performed

Read both new modules, the complete new test source, changed original dispatch code and parent-run raw pytest/lint/type-check/tripwire records. Independently performed a stdlib AST comparison against HEAD's original dispatch wrapper; no product imports or test execution were used for that comparison. This reviewer did not run tests, prototypes, profile, DB/fixtures, Mock/model/G0/launcher or signals, and did not write the repository. Only this `/tmp` directory was written.

Baseline HEAD: `df957ac17bef8e5e186980ea355f506f352b4a54`. The parent is the sole source writer. SHA bindings and repository status are recorded in `REVIEW.json`; the conclusions apply only to those candidate bytes.

| Candidate file | SHA-256 |
| --- | --- |
| `src/sim2act/_cold_accounted_values.py` | `f74bee1711f15886990dfd43f412edbac1829109ee13dd02be47db8ce9631275` |
| `src/sim2act/cold_accounted.py` | `a6a15ddec7012a65bbbaeccb60a05a3df8dd3d0dbb0b24b95e20f5db297d78d8` |
| `src/sim2act/pa_trial_dispatch.py` | `d8548009bd5bc4b8edadff0face636cde6a0b452a982c588fd779c51c03a26a6` |
| `tests/test_cold_accounted_component.py` | `4d6e1e965175e66916e52f8ba5508d8ed6b41cdbfe9fafbd993f60102784c905` |

## Issuance, lifetime and fixed accessors

The issuer calls the original `_graph_stage_accounted`, captures complete values, compares the owned **full business shape** with the original `cold-trial:accounted-{role}` raw pin by explicit structural equality, and then performs the original full graph check plus current frame check before registration. This closes the initially found hole where a self-consistent returned model could drift from its already verified raw snapshot before copying. The third-Capture mutation regression exercises that exact distinction.

The lifecycle stamp binds exact graph, Store/connection/transaction, scope/nonce/token, binding/driver, phase/epoch/change count/thread and schema. `_frame` now also checks actual `driver.in_transaction` and the original `_source_reads_current` state predicate, rather than accepting an SQLAlchemy transaction object after its underlying transaction ended. `_scope_for_graph` is explicitly pre/test-only/SQLite, uses a controller context and keeps original full checks. The stamp is continuity evidence, not a fresh Grant/Run/lease authorization decision.

Issued handles are exact private identity keys in a per-scope registry. Wrong/unissued/cross-scope/role handles fail; scope closure or lifecycle failure clears registrations. `issue` has a private tentative registration while it checks all three/two aid associations; the handle is returned only after these pure checks succeed. Every `BaseException` closes the scope and clears all prior handles, so a failed association/producer does not publish a partial successful result. No IO/await callback was introduced between registration and association validation.

Frozen fixed views validate exact Family/Node/schema types, exact integer node index/range and identity with their registry's packet before reading fields. The Node itself is a frozen dataclass with constructor checks. Arbitrary `==` and `!=` on Nodes reject; view/record equality rejects. Foreign nested wrapper fields therefore cannot reach attribute/index/hash callbacks through the reviewed entrypoints. The final extra wrapper/ref regressions cover the previously found corner. These are ordinary input-type barriers, not a claim to defend arbitrary rewriting of trusted Python code.

The content packet is recursively immutable and contains no mutable source/container/model references. The **scope controller intentionally retains the original graph for lifecycle validation**; a Family/View can reach that controller through private internals. Consequently this is a fixed-data-access API guarantee, not a claim that its entire Python reachable object graph contains no old graph. Future consumers must be audited to use the fixed accessors and never read raw data through scope internals. That consumer closure is not installed or proved here.

## Value representation and four leaves

The value module keeps the reviewed per-call active/completed memo, cycle rejection, longest shared-path height check, explicit resource bounds and flat node references. It preserves surrogate strings using surrogatepass accounting and ASCII escaped encoding. It has no thaw/materializer. `_equal` compares admitted node contents with a per-call pair memo, independently of node numbering, sharing and dictionary order, while preserving numeric/container tags. Registry packet identity checks are provenance checks; they do not substitute for domain equality.

The four adapters preserve the relevant admitted-domain predicates:

* Stage usage reads all requested aid data, reconstructs exactly the original normalize-usage rules for known/partial/unknown/None and exact nonnegative integer tokens, compares complete checked/actual values and usage, keeps expected status and settlement values.
* Source row keeps explicit controller/offline mode, VERIFIED status, model agreement, accepted true and non-null settlement. Mode comes from context, not a row-based inference or default production downgrade.
* Source exchange still invokes the original strict parser, response archive and usage normalizer on original bytes. It retains exact max-token integer and stream checks, UTF-8 character versus byte counts, wire/archive metadata, complete raw response/usage, raw-versus-canonical settlement rules and token equality. Output is an immutable projection of the original canonical fields; no packet digest replaces wire or business hashes.
* Archive chain independently snapshots the still-protected full Ledger and resolved receipt/bodies for pure comparison. It retains two-item counts, ledger order/halt, verification/live flags, source run, unique aid matching, complete Slot and checked membership, every wire/capture/canonical field and private request/response bytes at the corresponding index. It does not reduce the join to public hashes.

Source row/exchange choose the issued family's Slot instead of accepting an arbitrary independent slot argument. Their equivalence is therefore conditional on the complete producer/association relationship. At future installation the outer current-ledger/source-key/authorization checks must still establish this relationship; an owned leaf alone does not replace them. The archive-chain regression separately checks a full external Ledger Slot mismatch.

The new scalar/domain comparisons are intentionally stricter than some old Python numeric equality outside the producer's exact schema. The test explicitly shows a float `request_bytes` accepted by the old pure body but rejected by the new adapter. This is disclosed as invalid-domain hardening, not falsely labeled all-Python-input equivalence. Nullable usage/response now reject via the domain path instead of an accidental AttributeError.

## Existing execution-path extraction

Only `pa_trial_dispatch._graph_pb_archive_chain`'s existing pure comparison body is extracted into `_archive_chain_from_facts`; the old wrapper now calls that helper. `STATIC-EXTRACTION.json` is this reviewer's independent proof: the five pure top-level statements match the original AST; the four arguments and `_guard` forwarding are exact; inlining the helper yields the entire original wrapper AST, including original prefix/typed checks, final guard, try/exception invalidation and predicate/guard order. The helper adds a private stack frame; unchanged traceback depth or arbitrary private-function monkeypatch behavior is not claimed.

Read-only source search found no import/call of the owned component from existing runtime modules; the new component imports its private value module only. Existing runtime checks are not exempted. It would be inaccurate to say **all** existing runtime source is untouched, since the dispatch pure-body extraction is a real, narrowly verified refactor.

## Observed tests and limitations

Parent raw records show first 32 passed (0.53s), expanded 36 passed (0.55s), and final 38 passed (0.59s), with zero monitored tripwire attempts. The preceding 38-case result before the portable-checkout test edit is preserved separately. Final ruff says all checks passed; final mypy reports no issues in the two new source files. Earlier lint findings and 13 mypy annotation/NamedTuple issues remain in raw records. This reviewer read these results and did not independently rerun them. Tripwires cover test setup/body/teardown after imports, not a general import-time sandbox.

The final test resolves its repository through the imported runtime module's source location instead of the initially hardcoded `/workspace/Sim2Act`; the archived `/tmp` copy and repository test have identical bytes.

The test source is explicit about its limits: original producer and full CGR check are stubs around synthetic complete rows/real fixed types, with the real C codec raw pin and real pure `_source_reads_current` predicate over fake DB lifecycle state. Archived exchanges supply bytes; no original complete G0, real DB transaction, Store/Worker/model instance or model transport is executed. Tests establish the new local mechanics and selected real pure-leaf differences, not original producer admission, current revocation/fence/lease handling, W5/postwrite rollback, end-to-end consumer equivalence or G0 performance.

Bounds are explicit caller obligations with no production defaults. Full Run/Attempt JSON and hidden-storage accumulation still lack a proved product-scale bound mapping. That fact alone continues to block runtime installation. Full family occurrence/consumer migration, final complete manifest/pin and post_graph/origin/software-audit compatibility also remain unimplemented. Existing full checks and persistent fingerprints must stay until those conditions close. This component is neither a lease extension nor a cross-transaction cache/capability.

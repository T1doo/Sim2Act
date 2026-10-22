# Explicit fresh RowMapping native leaf, default closed

Base `26f85067b3596e5ff2f5cdd6f152ba676dfc83a6`, same Sim environment,
one writer, clean initial worktree, live development remote equal to base.
No G0, complete Cold chain, Mock, real model/HTTP/account, Cold2 or W5 was run.

## Retained candidate

`_cold_row_native_impl.c` implements only the original
`_cold_graph_row_storage` leaf. The explicit loader checks exact CPython build,
ABI, executable, headers, C source and binary, original Python source hashes,
the installed SQLAlchemy implementation hashes, canonical types and original
descriptors. No automatic discovery, install, production routing or grant.
The original typed visitor source/pins, runtime, Pickler class/method, marker,
tags, protocol 5, fresh stream/memo and all dynamic gates remain unchanged.
The builder's new explicit `--component row` option uses the installed compiler;
default typed output still has SHA256
`a9c32db0f64ab4a8f901a5c7c5dc3cf32cc72c67573437f38b7ec306459510f2`.

Each call rechecks implementation globals/code, MRO and static descriptors.
The C leaf uses the original C getsets/member getter, without assuming private
SQLAlchemy structure offsets. Reads/checks retain the original order:
parent/data/index, combined storage predicate, keys, complete key predicate,
safe-index iteration/range predicates, final coverage predicate.
Keys/list and data/tuple are the original objects, including all hidden data;
only the original safe lookup projection is rebuilt. Original safe key and
position objects, ordering and collision/overwrite behavior are retained.
Foreign index keys are traversed without hashing/equality or position checking.
Large integer positions produce the original validation error, not a new
OverflowError. Exceptions propagate without retry; None selection exits C
before calling the original single-argument Python function. This replaces
neither the Pickler method nor its real self, unlike the rejected experiment.

## Optimization subdomain, not new business limits

Eligibility is at most 64 visible keys, 64 index entries and 8,192 total Unicode
characters across keys and safe index keys. Exact dict storage, measured by
the fixed immutable built-in C `dict.__sizeof__` descriptor, is at most 8,192
bytes before *each* index or class-namespace scan. Namespace scans also retain
their logical work bound. No private dict version/result/PASS cache is used.
These qualify only added native work. They are not RSS/CPU/full-graph limits.
Data is returned intact, not scanned/truncated to fit eligibility. Oversized or
unknown layouts go through the complete accepted Python path before lookup
allocation. Invalid content retains its original rejection; there is no
post-failure downgrade, retry or narrowed business acceptance.

Independent review identified that live dict length does not bound dummy-entry
scans. The final code checks actual table storage. Regression witnesses include
20,000 inserted keys deleted down to one, plus class namespace churn in an
isolated read-only child process (avoiding permanent capacity changes in later
timing samples). Both select legacy and still accept the complete original row.

## Final frozen validation

Four source SHA256 values are in `frozen-sources.json` and were checked unchanged
after both final processes. The reviewed C source is
`33668b01ba979ae90dc12c7f83e9433f97d63aa2778c3bea47261da37a55409d`.
Release binary:
`d3fe559a0f5b11d958c11a6785828f422119b1294330adf30fe8a9023923b748`;
ASAN binary:
`71d82103c0a91686b6a73760619b0d2df90a122f2fd69a9b7691d7ad9f8f246e`.
Both actual binaries match the loader's separate fixed pins.

- Final normal: **130 passed**, 5.43s, row component plus unchanged original
  row-storage/fingerprint regressions.
- Final ASAN row component: **42 passed**, 5.38s, no address error reported.
  `ASAN_OPTIONS=detect_leaks=0:abort_on_error=1`; this is not leak detection or
  proof of no leaks. Its timings are not performance evidence.
- Both processes had a 60s outer timeout and ran sequentially. Test tripwires
  prohibit Worker, model construction, real and Mock transports. SQLite is new,
  isolated and test-only with synthetic upstream fixture facts. Clients and
  engine close in fixture finalizers; the own child exits within its 10s cap.

Coverage includes exact bytes and cross-root aliases, hidden mutation and
index relationships, foreign keys/positions, cycles/unknown reducers through
the unchanged validator, mixed-error order, bool and arbitrarily large integer
positions, partial construction/getter errors, native-error non-retry/recovery,
unknown callbacks/code/layout selected before projection, initial descriptor
and type alias rejection, wrong binary rejected before extension initialization,
both sparse-storage witnesses, and stable type/function reference counts.

The initial development run had 27 passes and two test-construction failures
(a replaced str affected an earlier type predicate, and a replacement code
object had free variables). The fixed pre-storage-bound version had 32 passes;
the intermediate storage-bound version had 125 passes including default
regressions. These original logs are preserved and are not final qualification.

## Same-input component cost, including per-call qualification

The final normal batch uses actual SQLAlchemy mappings from isolated SQLite:
2 Run rows, 5 Attempt rows, 18 Grant rows, the complete actual PB contract
projection, and direct keys/data aliases into a Run row. Exact output is
**38,864 bytes** in both paths. No visible-row reconstruction or Pickler change.

Seven alternating samples, 1,000 fresh complete encodes each, thread CPU:
Python median **0.116011194s**, native candidate **0.076914039s**, about **33.70%**
lower for this batch. All seven candidate samples were lower. The measured
scope includes the Python wrapper, fresh per-call static/schema/table-budget
checks, getters and lookup, plus the same stream/Pickler/memo and encoding.
It excludes one-time build/load/provenance checks; those are explicit setup.
Counters include 175,125 native projections/validation selections and zero
legacy selections in this batch; legacy is exercised by separate regressions.
The extra 100 direct projections test reference stability.

This is not the complete Cold input, whole-chain improvement, stable production
benchmark or G0 deadline evidence. The old full profile's 4.761695283s inclusive
row-storage interval cannot be assumed removable or multiplied by this ratio.

## Next complete A/B proposal, not executed here

The component result and independent review support preparing one frozen
**configured synthetic semantic-clock** pair using the existing shared prefix
and independent new SQLite copies. Keep both arms' typed/backend, clock and
all guards identical; change only the explicit test row-helper route in the
candidate arm. Preserve the actual Pickler method/self and existing core
function identities. Imported legacy helper aliases remain legacy; do not
claim complete replacement of every consumer. Assert actual native counts,
base qualification counts, strict outputs/SQL parameters/business bytes/
receipts, both commits, normal scope return and final deadline predicates.
No profiler or core-function wrapper that silently changes eligibility.

Proposed cap: one process, shared prefix plus two Cold1 cases, **7 Mock
exchanges / 9 entries** total, no retries; 600s overall plus 10s cleanup, 64MiB
sampled disk monitoring (not a native quota), no real HTTP/model/account and no
Cold2/W5. Use the existing three clearly synthetic configured substitutions,
semantic test clock only, original lease/Run/TTL and authority/SQL/transaction/
fence/stop/final gates. This proposal authorizes no real-clock G0 or production
qualification and was not executed in this component task.

Raw stdout, JUnit, cost JSON, source freeze and build receipts are compressed in
`originals/`, with archive hashes in `manifest.json`. No binaries or databases
are committed. Independent review is recorded separately; no reviewer ran or
loaded the component. Official references consulted:
[SQLAlchemy 2.0.48 BaseRow](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_0_48/lib/sqlalchemy/cyextension/resultproxy.pyx),
[PyDict_Next](https://docs.python.org/3.12/c-api/dict.html#c.PyDict_Next).

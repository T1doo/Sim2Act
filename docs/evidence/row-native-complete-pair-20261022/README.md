# Native row semantic pair — completed, no net speedup demonstrated

Frozen candidate: `41db710bfe613a5721271abd1ab23013aba0c9a9`.
One authorized launch completed with `COMPLETE_SYNTHETIC_PASS`, 1 pytest pass
in 115.29s; supervisor elapsed 116.305554s. No retry or additional window.
This is configured test-only SQLite with a synthetic business clock, **not
real-clock G0 or production account/source qualification**.

Both arms completed prepare, first commit, receipt, second commit, normal
scope close and the original final semantic-clock gate. Strict type-tagged
outputs, SQL sequence/parameters, exact receipt and final samples matched;
context/source business fingerprints matched. Each arm retained 275 qualified
base calls, 1,137 base dynamic checks, 8,062 codecs / 4,682,215,371 encoded
bytes, 7,735 SQL statements and 8,038 qualified typed-native calls. The native
row arm actually selected the new C leaf 134,643 times, with zero fallbacks.
The original Pickler and core witnesses remained unchanged.

| Same configured input, ordered pair | Python row | Native row |
| --- | ---: | ---: |
| Worker owner CPU seconds | 42.145114605 | 42.799218895 |
| Worker wall seconds | 42.400231160 | 43.033051907 |

The candidate was **0.654104290 CPU seconds slower (1.552%)** in this pair.
One ordered instrumented observation does not establish a reliable regression
size, but it does not support full-chain performance acceptance or another G0
attempt. Component timing is not extrapolated to this chain. The candidate
remains explicitly loaded and default closed; no production enablement.

Actual usage: 7 Mock exchanges / 9 entry admissions / 2 source delegates,
zero real models, no Cold2/W5 or real HTTP/account calls. All run/lease/TTL and
other original guards remain unchanged. The 64MiB sampled disk monitor recorded
15,852,259 bytes over 1,159 samples; actual intervals ranged
0.100176671–0.103246990s. This is not a native disk quota or an RSS bound.
The supervisor confirmed source hashes unchanged, no supervision error,
cleanup in 0.000051399s, and its own process group absent; a later read-only
probe also found that group absent. The fixture confirmed no new live thread.

Raw logs/XML, grant, source freeze, progress, supervisor receipt, pair result
and both strict traces are preserved under `actual/` as lossless gzip files;
`actual-manifest.json` includes original and archived SHA256. No database,
native binary or credentials are committed. `result-summary.json` is a compact
index into those originals. The existing Starlette/httpx deprecation warning
does not change the pass result; no dependency was installed to silence it.

Limits: this pair covers the normal synthetic tail, not real-clock 30s lease
acceptance, production SOURCE_MISSING resolution, W5 five-write rollback,
Cold2, leak detection or all negative cases under full-chain execution.
ASAN component evidence below used `detect_leaks=0`. No performance or
production readiness claim follows from the semantic pass.

## Preserved preflight record

Base `2189e6d356c8d5c91560ede92f0f0298a4867f27`. This preflight commit
does not contain a new complete A/B result. Product default remains closed.

Parent independent review found missing dynamic `int` identity eligibility.
The original helper's position predicate uses globals/builtins int; the C
implementation used exact PyLong directly. The fix adds the int identity to
the explicit loader, native factory and every schema check. The previous
indices remain unchanged; array sizes and reference cleanup are synchronized.
Unknown int chooses the original function before native projection, not a new
business rejection. No unrelated monkeypatch framework or guard changes.

Targeted tests: 9 passed / 35 deselected (0.43s), including runtime.int and
builtins.int rebinding, equal original DomainError, single legacy selection,
loader refusal, and successful restoration. New-source component: 44 passed
(3.78s); ASAN 44 passed (5.55s), leak detection disabled. These results do not
inherit the previous candidate's full-chain or component timing claims.

The proposed one synthetic pair reuses the existing configured prefix and
PairObservation. Both arms use the same qualified typed backend; only the
candidate row-helper route changes. The Pickler method/self, core identities,
all guards, business outputs/fingerprints, SQL parameters, exact receipt,
two commits, normal scope close and final business deadlines remain checked.
Expected base qualification remains 275, and actual row selection is recorded.
No real-clock G0, Cold2, W5, real HTTP/account/model, fee or permission change.

Supervisor starts in a new directory with a new single-use technical test
marker, freezes source hashes, and permits one child only. Caps: 7 Mock
exchange admissions / 9 entry admissions, total 600s plus a shared 10s cleanup
deadline. The existing semantic clock's own 300s healthy check remains tighter.
Only test-only SQLite and the existing three synthetic qualification
substitutions are used. The 64MiB directory disk check is sampled, not a native
quota; actual sample intervals and peak are recorded. No automatic retry.

Pre-start independent review caught two supervisor issues before any Mock:
progress path mismatch and exception paths bypassing cleanup/receipts. Parent
now passes the exact progress path; each admission atomically replaces the
progress file. All post-spawn work has one try/finally, sticky diagnostics,
own process-group-only cleanup and no signal-permission bypass. Exit 0 alone
is insufficient: exact 7/9/2 progress, one complete semantic result, unchanged
sources and confirmed process-group cleanup are required. Missing/UNKNOWN or
receipt errors cannot become success.

Pure supervisor shims: 7 passed (0.05s). These tests launch **no process**, send
**no signal**, and perform **no Mock/DB/model** call. They simulate PID-receipt
write failure, sample failure, child timeout, final-receipt write failure,
exit-0 without result, signal permission denial, and source-read failure.
Simulated denials are test data, not an actual environment permission denial.

Raw preflight logs/XML, build receipts and source hashes are in `preflight/`
with hashes in `preflight-manifest.json`. Actual A/B evidence, when available,
must be added separately after the single authorized launch; no old result
or component percentage substitutes for that run.

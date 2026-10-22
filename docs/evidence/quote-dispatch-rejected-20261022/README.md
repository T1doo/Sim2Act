# Rejected optional quoted-name dispatch experiment

Product base and restored implementation:
`797472edb24dbf1ea36e634f547237231ee5c0cb` (the ASAN loader repair).
This experiment is **not retained in src, enabled, or performance-qualified**.
Archived source/patch exists only to explain the negative result. Do not treat
the archived extension as an approved backend or install/load it automatically.

## Why this operation

Read existing identity-preserving complete owner-thread profiler originals in
`../schema-stream-cpu-20261021/originals/profile-run/test_one_complete_identity_pre0/`.
There was no new complete-chain profile or Mock run. In that instrumented run,
C Pickler dump had 8,062 calls, 19.415121942s exclusive / 28.09095324s inclusive;
Python reducer_override had 2,137,411 calls, 1.821300515s exclusive /
8.675831298s inclusive; row_storage had 134,643 calls / 4.761695283s inclusive;
limit_values had 95,484 calls / 2.110925364s inclusive. These intervals overlap;
they are not additive and do not establish uninstrumented savings or G0 margin.
The old profile does not itself count quoted-name branch invocations.

The attempted native leaf performed only exact known quoted_name conversion,
preserving the original marker and co_consts tag **identity**, tuple shapes,
protocol 5, fresh C Pickler/memo/stream and all original row/limit helpers.
Unknown bindings, types, string slots or function code selected the original
Python reducer before conversion; no native-exception retry or graph cache.
It was wired only in a test encoder, never in CGR or the default runtime.
Installed compiler only; no SDK, dependency, permission or license additions.

## Bounded component results and limits

Each process had a 60-second outer limit. All actual test processes terminated
normally in under two seconds. Execution tripwires prohibit Worker/model,
real HTTP **and Mock**. SQL used a new isolated test-only SQLite fixture with
synthetic upstream facts. No account resolver, complete prepare/commit chain,
real clock G0, Cold2, W5, model exchanges or production actions were executed.

Initial development test invocation: 8 failures due to missing required quote /
Limits constructor arguments and a reference baseline taken before GC; this
was not an execution-path success. Corrected invocation: 7 passed / 1 fixture
argument failure. Their original logs/XML remain archived.

The first implementation interned names per reducer invocation and constructed
the candidate class each encode: 27.270186ms vs 12.471822ms per 500 quote-only
encodes, slower. Hoisting immutable field-name objects reduced that cost; its
8-test component run passed, but constructing the candidate code class each
encode still made comparison asymmetric (18.569541ms vs 14.493970ms).

Final fair quote-only comparison hoisted both code classes, retaining a fresh
stream, Pickler and memo each encode. Seven alternating samples of 500 encodes
of 128 distinct quoted_name values: median old **13.125196ms**, candidate
**12.486243ms** (about 4.87% lower in this component). Actual counters:
448,128 native quote dispatches, 3,501 original Python dispatches. **8 passed**,
0.44s total. This tiny quote-only input is not the complete Cold graph.

One actual isolated SQLite batch retained complete RowMapping objects from
Run (2 rows), Attempt (5), Grant (18), and a fresh full actual PB contract
projection. No visible-pair reconstruction or hidden-field omission.
Output was exactly equal, 38,826 bytes. Seven alternating samples of 100
encodes: old **12.406384ms**, candidate **12.214347ms**, about 1.55% lower
with substantial sample variation. Counters increased by 29,400 native /
18,200 Python dispatches. **1 passed**, 1.99s total. This mixed batch does not
prove a stable improvement, complete-tail improvement, or a 30-second margin.

## Independent rejection and actual witness

Reviewer found the native callable's changed-code fallback passed `self=None`,
whereas the original reducer receives the actual Pickler. An additional bounded
test deliberately rebounded the reducer code to encode `self is not None`.
Both codecs completed, but their bytes differed:

- old SHA256 `cbe6f3a49b0cc33163a1996928d21bf478b24a71cf5411add51915635c4bfe0a`
- candidate `11fee92219817d4b9aab15daf4c5126b3fefac61a852e7ef91b6ffc3bb527f92`

The witness passed its **expected non-equivalence** assertion (1 test, 0.18s).
It disqualifies this fallback claim; it is not candidate qualification. It also
does not establish that all native dispatch optimizations are impossible or
that 30 seconds cannot be met. The small/noisy mixed benefit did not justify
expanding this candidate into a binding-descriptor implementation. No ASAN or
full-chain run of this rejected candidate was claimed or needed for enablement.

The writer restored only its own C changes; no product pins were changed.
Final C SHA256 is
`c1b0f48779febbfcec6e9316c8f27f31bff34f926eb667cdfa1a5b173d51ce2d`,
runtime `c06226860b7690daff210be62e69433eb2a174f4a63b90ba3d18304b2fca0f12`,
and ASAN adapter
`88acc02096e9592aed65c673d2f4d3579be00e80dbcf5cdd7c75018138ba2e28`.
No product source differed from the independently reviewed ASAN commit after
restoration. No benchmark-only pin or unsupported native API remains in src.

The concrete next technical choice, if continued, is a separately proven fresh
RowMapping/Limits leaf adapter with real Pickler binding, complete storage and
all current validation, rather than a dispatcher-only substitution. This is a
possible implementation boundary, not a proven speedup or authorization to
relax pins, leases, transactions or dynamic gates. Existing C Pickler traversal
and output of every fresh graph remain necessary under the current wire/pin
contract; this experiment did not remove their cost.

`originals/` contains final candidate C/test source, product diff, build
receipts, all process stdout/XML, and cost JSON, compressed without binaries or
databases. Source for the earlier pre-hoist development revision was not kept;
its receipt/logs cannot be treated as the final candidate revision. Hashes of
archived files are in `manifest.json`.

Primary references consulted: [Pickler reducer_override](https://docs.python.org/3.12/library/pickle.html#pickle.Pickler.reducer_override),
[C function binding API](https://docs.python.org/3.12/c-api/structures.html),
[PEP 699](https://peps.python.org/pep-0699/). No private dict-version cache was
implemented; the fixed code names were hoisted, not mutable graph results.

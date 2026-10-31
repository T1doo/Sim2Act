# Native code witness repeated-namespace work

Frozen application **545227cea9978e8b3a109e2314d0eb3a2c04a13a**, preserving receipt source68c27fdde3d60f0f84bb45b4b0efbaab82ef2d07/evidencef207f6e39e96555731635f08633b1ca5f530cd6b and faster historicalfb60. No business branch, authority check, write, deadline or C interface was removed.

Functional acceptance passed: two large saves, first fresh-process reopen and actual locked-writer cancellation rollback. The local qualification cost is lower, but full settlements are one shorter/one longer than same-profile68c; consistent whole-chain acceleration is NOT demonstrated. G0 sample29.047897/29.936107s leaves only64ms on the second; writer45.080062/47.635530s remains above30. This is not overall performance completion.

## Same-fixture sequential diagnostic pair

Original fixed-order fb60→68c exports use exact source manifests, identical three loaded extension hashes, Python3.12.14/SQLite3.53.1/hashseed0 and identical passive profiler. No concurrent benchmark. Seven fixedMock responses per full chain, zero real calls. Dynamic UUIDs/clocks and some request/response bytes differ; not byte-identical data or a controlled frequency/cache experiment. Original stopped wrapper and observer setup failure are preserved. Two small prelude epochs plus two large epochs explains the wrapper cardinality correction; baseline did not rerun.

| Version | Cold | G0 read s | Atomic writer s | Total s |
| --- | ---: | ---: | ---: | ---: |
| baseline | 1 | 30.189312 | 45.702530 | 75.892731 |
| baseline | 2 | 37.038457 | 48.883942 | 85.922852 |
| receipt | 1 | 30.057293 | 45.838036 | 75.896151 |
| receipt | 2 | 30.213952 | 45.988700 | 76.203121 |
| candidate | 1 | 29.047897 | 45.080062 | 74.128828 |
| candidate | 2 | 29.936107 | 47.635530 | 77.572110 |

Pair first total75.892731→75.896151 is effectively unchanged; second85.922852→76.203121 is9.719730s/11.31% shorter in this sample. Both68c G0 routes OWNED. Some gain occurs in unchanged-count G1, so the whole gain cannot be attributed causally to receipt protocol. Owner-thread CPU is99.4–99.6% of wall in both samples; observed throttling is tiny, but clock frequency/cache effects remain uncontrolled.

Second G0 new native qualification1.698528s includes preload.356920 and metadata publication.464667; nonpublication budget work.000716 is not the main hotspot. Second encodings816→863 (additional43,165,481 bytes), dynamic8699→8372, select7537→5530 plus2041frontier, typed2997→2957. First G0 and both G1 encoding volumes/typed/select counts unchanged. Projection returns are not encoding counts.

## Minimal production implementation

Within each fresh native verify_code call, each family keeps up to64 exact namespace pointers. First use scans every current key for exact Unicode; subsequent use in the same pure witness/constants C segment avoids that same key scan. Every function/code/default/keyword-default/closure/constant value remains checked. Class witnesses are fully checked and the next family starts empty: possible foreign class-key equality callbacks cannot carry an old scan result. Full table uses original scans, no allocation or cross-call PASS cache; GIL requirement, GC and exception handling are unchanged.

Actual diff independent review found no freeze blocker. Fresh isolated native regressions include1/64/70namespaces, between-call mutations, foreign hash/equality nonexecution and a class equality callback mutating a previously checked module before the next family. Combined91 passed175.58s, zero fail/error/skip; earlier18 overlap. Existing Source/receipt code/default poisoning, revocation/stop and original protocol checks remain.

Isolated old68c→candidate→old68c→candidate qualification batches report median CPU44.0055/33.8894/47.1119/33.7645microseconds per call. This is local qualification only, not extrapolated full-flow savings. Loaded binary hashes and complete chain counts are in candidate-5452-profile.json; frozen application SHA is in candidate-5452-run.json/measurements.json, and actual C source/binary pins are in native-identity.json. Default optional clang build failure is explicitly preserved; final existing-GCC build and source hash were actually checked. No Windows build claimed.

## Frozen candidate acceptance and limits

Original two large saves COMMITTED; both actual OWNED; immediate first fresh-process reopen compares saved HTTP/app/typed result, exactly one version/effect, both Cold attempts VERIFIED, all7attempts and logical/main identity. Empty-WAL lifecycle is reported separately from physical identity; nonempty WAL requires exact bytes. Real G1 writer cancellation first proves independent SQLite BUSY5, status/cancel HTTP responses and rollback, preserving prior history/received row/resources/archive with no settlement/rejection/new typed data. Final RECONCILING/RECEIVED is not terminal CANCELLED. Cancel G0 30.851245s, interrupted writer3.716060s,total34.568297s; statusHTTP200 .161048s/cancelHTTP200 .202085s. Thus even G0 remains above30 in that cancellation sample; no robust30second claim. Normal7Mock/cancel6Mock,0real; no cancel call-count profile is claimed.

Candidate measurements above are one frozen real-clock engineering sample, not SLA. Original30second admission/first-DML lease differs from120second complete G0+G1 settlement; neither extended/reset. G0 below30 alone does not solve long atomic writer or establish full original performance goal. SQLite/test_only/Mock evidence is not formal PG/live model/semantic goal/target Windows EXE acceptance. No fifth Windows CI, PC operation, main/Release/deploy, paid fallback, new credentials/security permissions.

Candidate vs same-profiler68c deltas (negative is shorter):
- Cold1: G0-1.009395s, writer-0.757974s, total-1.767323s.
- Cold2: G0-0.277845s, writer+1.646830s, total+1.368989s.
These are observed settlement samples, not the whole-chain elapsed time or proof that the original30second lifecycle goal is complete.

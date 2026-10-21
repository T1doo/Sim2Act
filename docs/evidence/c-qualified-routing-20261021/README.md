# Qualified, explicit synthetic C projection route

Parent: `f77593e01caaed413252010c119af9051268471a`.
This is an opt-in **test-only SQLite** encoding candidate. Default product
calls retain the original Python typed visitor. No real-clock G0 was run.

## Actual release result

One frozen, complete configured synthetic A/B passed: **1 passed in 117.39 s**.
It built a new original configured prefix, then ran one Python C1 and one C C1
in separate SQLite copies, with the existing explicit semantic business clock.
Only the fixture's original environment/account/software qualification
substitutes were used. It is not a real production account/source proof.

Both arms completed prepare, first commit, receipt, second commit, normal read
scope close and the original final deadline gate. Strict output (including
bool/int and list/tuple), business fingerprints, full SQL/parameters, exact
receipt storage and final clock samples match. The original helper was not
replaced, and the existing `_base` identity qualification stayed active.

| Measured same interval | Python | Qualified C |
| --- | ---: | ---: |
| Main-thread CPU, `worker.once()` to pre-W5 TailStop | 43.732164740 s | 43.032715942 s |
| Wall time, same interval | 43.994863476 s | 43.315996060 s |
| Native projection selections | 0 | 8038 |
| Python selections after entering selector | 0 | 0 |
| Qualified base entries | 275 | 275 |
| Base calls / dynamic checks | 569 / 1137 | 569 / 1137 |
| SQL statements / Run predicates | 7735 / 2 | 7735 / 2 |
| Codec calls | 8062 | 8062 |
| Cumulative codec output bytes | 4,682,215,371 | 4,682,215,371 |

The observed CPU delta is **0.699448798 s / 1.5994%**, from one Python-first
pair. It is not an order-balanced statistical estimate or a lease/G0 result.
This interval is also different from the earlier 33.4 s Cold-context-only
measurement; do not subtract those numbers. Cumulative encoded bytes are not
disk usage or peak memory. No reduction in full graph serialization is claimed.

The final pinned ordinary component test used the actual PB contract and the
same fresh projection plus original C pickle, including eligibility overhead:
five alternating-order samples of 1000 calls. Median CPU:
`0.125379793 -> 0.098803690 s` (about 21.2% for that input/component).
All 5001 selections (including the initial correctness comparison) chose C.
This local percentage must not be applied to whole-tail or old profile totals.

## Qualification and fallback contract

* `load_candidate` is explicit. Before native import it checks the exact current
  CPython **3.12.14 build string**, SOABI, interpreter binary digest, pinned
  headers, C source digest, build command, and an independently pinned release
  binary digest. A sidecar's self-reported digest alone is insufficient. The
  module exports its source/version and `PyThreadState` size/offset witness
  (`288 / 28 / 36`). Unknown provenance selects the original implementation.
* A private issued, slotted handle prevents instance method shadowing. The
  runtime uses the fixed class entry, and checks helpers/backend identities;
  unknown callbacks cannot dispatch through a replacement `select` method.
* `input_bytes` first uses a C-only remaining-stack probe **at the original
  caller frame**, before Python selector/catalog frames. Below the conservative
  128 reserve it calls the original helper at its original frame depth. The
  selector then reads the actual thread's Python and C remaining budgets. It
  never writes those counters or changes `sys.setrecursionlimit`.
* The nonrecursive, bounded fresh scan counts **actual visitor calls**, including
  scalar leaves and memo hits: at most 255 visits and 4096 metadata/edge work
  units. Every current path is charged weight 1 per visit, plus 1 for each tuple
  generator; `64 + 4 * path_weight` conservatively covers the Python visitor,
  metadata/generator/helper frames and C recursion demand. Insufficient budget
  or scan capacity selects Python before any C projection, never a new business
  depth/size rejection.
* Only exact native scalars/containers and catalog models with the standard
  Pydantic layout qualify. Static MRO namespace keys are gated before lookup;
  lookups preserve errors. Metaclass fields descriptors are excluded. The
  `__dict__` getter and three model slots must be standard; absent slots, unknown
  descriptors/layouts, foreign keys, malformed storage and cycles go back to
  the original visitor for its original error order. Qualification never calls
  custom input descriptors.
* The exact CPython 3.12.14 GC implementation schedules collection at allocation
  and runs it at an eval breaker. This bounded C-only region has no Python eval,
  GIL release, user getter, or internal signal-poll point: visits stay below the
  existing 256-call poll interval. An entry signal check precedes fresh scanning;
  it does **not** claim to drain every pending GC or pending call. Signals/GC can
  run before/after this short region; the GIL alone is not the proof. No GC
  setting, pending state or interpreter counter is suppressed.
* There is no cross-call graph PASS, digest or object cache. Namespace witnesses
  and active/completed-node state live for one scan only. C re-reads/copies the
  current values with the original scalar/key identities, order, DAG memo,
  active-before-seen check, tuple/list distinction and two None omissions.
  A chosen C projection exception propagates once; it is never retried in Python.

The same scoped handle feeds the two original graph-read construction paths
through the worker's explicit private test option. It grants no model/account
access. Old fingerprints, reducers, SQL, authorization, lease/Run/fence/stop,
transaction and final-clock gates remain in place. `natural_live_admission.py`
is unchanged. There is no environment-driven production enablement.

## Validation and failures

Final release qualification suite: **12 passed in 6.38 s**. It covers mixed
models/containers and DAG aliases, bytes, 1500-deep Python fallback, actual low
remaining Python stack, extreme remaining stack with partial model/error
equivalence, descriptor and metaclass callbacks exactly once, incomplete model
slots, foreign class-namespace keys without hash/equality execution, forged or
shadowed handle rejection, per-call freshness, namespace/model reference-count
stability, unknown builds before import, and original-frame fallback.

An earlier 70-test debug run covers existing base safety cases; it precedes the
final qualification fixes and is not presented as a final-version 70-test run.
The final C/runtime implementation then passed 43 ordinary tests and 44 tests
with the existing ASAN-instrumented extension. Those 44 tests preceded the
last loader restrictions. Extension instrumentation did not instrument the
interpreter; leak detection was disabled. Neither is a no-leak proof.

**Final optional ASAN loader limitation:** a subsequent final-version check has
**12 setup ERROR in 2.43 s**, retained in `final-pinned-asan.*.gz`. The existing
runtime is mapped as `/usr/lib/x86_64-linux-gnu/libasan.so.8.0.0`; the frozen
gate requires the symbolic-link spelling
`/usr/lib/gcc/x86_64-linux-gnu/14/libasan.so`. It conservatively returns None, so
the qualified fixture and twelve test bodies do not start. The raw backend
fixture had already initialized the instrumented module; do not call this
“zero native initialization.” This is an optional ASAN selection false negative,
not a C memory-access report or a release A/B failure. The earlier 44 passes
cannot be inherited as final-loader ASAN qualification. The implementation was
kept frozen after A/B; no extra Mock run was opened for this tool limitation.

Other preserved development failures include the too-shallow low-stack test
(`100` remaining still met a `92` need), and a reference-count regression that
found missing `PyType_GetDict` NEW-reference releases (`+500 / 100 calls`). Both
were fixed and directly covered before the frozen release A/B. No failed run
is counted as a pass. All compressed logs/XML and original record hashes are in
[receipt.json](receipt.json).

## Bounds, cleanup and review

The full pair used exactly **7 Mock exchanges / 9 entries**, including the new
shared Generate/Source prefix and two C1 arms. The parent command bounded it to
600 s plus 10 s termination cleanup. It did not retry. Real HTTP transports were
denied; real models, Cold2, W5, fees, new credentials and permissions were zero.
Original lease 30 / Run 300 / TTL 1800 and all predicate values were preserved;
the explicit semantic clock is not a production clock modification.

Both clients/stores/clock workers were closed by the fixture, thread cleanup
was asserted and the process exited 0. SQLite originals and evidence remain in
the isolated `/tmp/sim2act-c-qualified-20261021/qualified-ab` directory. Observed
artifact file sizes total 15,775,716 bytes after completion; this is not a native
disk quota, peak RSS measurement or claim of monitoring a real G0 window.
No unknown/external process was terminated.

Read-only independent review (zero product/test/DB/Mock execution) acknowledged
the [frozen code](C-NATIVE-QUALIFIED-ROUTING-FINAL-CODE-ACK.md),
[actual full A/B result](C-NATIVE-QUALIFIED-AB-RESULT-ACK.md), and the
[nonblocking ASAN loader limitation](C-NATIVE-FINAL-ASAN-LOADER-LIMITATION-ADDENDUM.md).
Code/semantic ACK does not prove stable speed or real 30-second admission.
The next performance decision still requires the original real-clock criteria;
this delivery neither authorizes nor starts another G0 window.

Official source references used for the bounded C-only argument:
[CPython 3.12.14 GC scheduling](https://github.com/python/cpython/blob/v3.12.14/Modules/gcmodule.c),
[pending work/eval breakers](https://github.com/python/cpython/blob/v3.12.14/Python/ceval_gil.c),
[Python/C recursion accounting](https://github.com/python/cpython/blob/v3.12.14/Python/ceval.c).

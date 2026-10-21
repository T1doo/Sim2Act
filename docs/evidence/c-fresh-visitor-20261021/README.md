# Explicit, default-off C fresh visitor

Parent commit: `a19dff9c5bbca792559905388177618543482dcb`.
This delivery adds a buildable optional CPython 3.12 component, an explicit
offline adapter and differential tests. It does **not** change
`natural_live_admission._trial_typed_storage`, `input_bytes`, the C Pickler,
production routing, schemas, dynamic gates, transactions or deadlines.

## Actual toolchain and build

The same saved environment has `/usr/bin/cc` (Debian GCC 14.2.0), CPython
3.12.14 and its `Python.h`/`pyconfig.h` under
`/opt/codex/runtimes/codex-primary-runtime/dependencies/python/include/python3.12`.
Setuptools is absent. No installation was attempted. The standard-library
builder executes the existing compiler with `-shared -fPIC -O2 -Wall -Wextra
-Werror`; it writes the binary only to the caller's explicit output directory.

```sh
.venv/bin/python scripts/build_cold_typed_native.py --output-dir /tmp/cold-native-build
COLD_NATIVE_TEST_DIR=/tmp/cold-native-build .venv/bin/python -m pytest \
  tests/test_cold_typed_native.py tests/test_cold_typed_storage_alias_contract.py -q
```

The runtime never searches for or automatically imports this binary. The
adapter requires an explicitly supplied backend. Unknown helper identities use
the Python path **before** native work; native exceptions propagate without a
Python retry. No permission/capability qualification or production selection is
created by building it.

## Implementation and evidence

Each call obtains fresh class catalogs in the original order, creates its own
active/seen sets, visits every current value and creates fresh containers.
Completed-node memoization lasts for that call only. Scalars and current key
objects retain their identities, including aliases into the surrounding input
graph. Exact types, field coverage, selected fields, the two None omissions,
list/tuple distinction, DAG aliases, active-before-seen cycle rejection and
metadata short circuit order are retained. Dict/list iterators remain live;
there is no early shallow snapshot, value patching, cached digest or PASS.

The extension holds the GIL for Python-object work, uses recursion guards and
periodic signal checks, and preserves the pending exception during cleanup.
This does not make a mutable graph atomic. The actual original C Pickler and
RowMapping reducer remain unchanged. Tests compare their bytes, including
hidden row data/index aliases shared with the projected contract.

Final frozen component hashes, the release binary hash, raw-record hashes and
measured samples are in [receipt.json](receipt.json).

The independent reviewer inspected the frozen source and raw normal/ASAN
records without executing tests. The [final component ACK](FRESH-C-TYPED-VISITOR-FINAL-COMPONENT-ACK.md)
is limited to this explicit offline component, retains the recursion
qualification block and recommends no additional full chain for this delivery.

| Actual run | Result | Scope |
| --- | --- | --- |
| Final ordinary interpreter | 32 passed, 5.44 s | 28 explicit native tests plus original four Python counterexamples |
| Final ASAN extension | 32 passed, 6.47 s | Same final source/test set, existing GCC ASAN runtime, no memory-access report |
| Earlier debug allocator / `-X dev` | 31 passed, 5.81 s | Final C source; before the last RowMapping test and warning cleanup |
| Ruff / diff whitespace | passed | Added Python files / repository diff |

Coverage includes all four original alias/copy counterexamples on C, strict
types, fresh mutation visibility, DAG/cycle, unknown types, mixed-error order,
incomplete storage, metadata reads and exceptions, bypass of overridden
instance/metaclass getters, descriptor-driven list append/dict replacement and
resize, post-gate foreign omission keys, bad bare-C ABI, fail-closed require,
signals, repeated cleanup and deep recursion. These are finite differential
tests, not a proof for arbitrary callbacks or every allocation failure.
ASAN instrumented the extension, not the host interpreter; `detect_leaks=0`, so
this is not a leak-sanitizer or whole-interpreter memory-safety claim.

The component CPU experiment uses the same actual configured PB contract,
fresh projection **and original C pickle** on both sides, no profiler, three
samples of 1000 calls per implementation. Python seconds:
`0.127002868 / 0.124587116 / 0.119987135`; native:
`0.058049864 / 0.059969367 / 0.058258495`. Medians:
`0.124587116 -> 0.058258495` (53.24% lower for this component/input).
This contract is not the complete G0 cohort. Neither the percentage nor the
absolute delta can be applied to the earlier 8086 calls / 16.96 inclusive CPU
seconds. No complete-tail, G0, lease-margin or throughput improvement is claimed.

## Qualification still open

CPython's C recursion budget differs from Python frame recursion: the supplied
1500-deep case is rejected by the Python visitor and accepted by C; the
20000-deep case is rejected by the C recursion guard. Thus this is **not** a
universal drop-in equivalent and must remain off in production. No arbitrary
depth cap or new business rejection was added to the original path. A future
selection contract must establish the exact supported recursion/resource domain
and actual call site before substitution. A shallow full-chain success cannot
close this known qualification gap. No new full chain was run this round.

## Failures retained, not counted as passes

The first pre-freeze build crashed on a minimal dict / the first PB test.
Existing ASAN diagnosed reading a NULL builtin `tp_dict` at the original C
`project` line 211. The fix obtains strong references to the two immutable
builtin descriptors with the public attribute API, checks them and releases
them. The original failure is preserved as a labelled tool-output excerpt in
[initial-failure-excerpts.txt](initial-failure-excerpts.txt); it is not a new raw
log or a claim that the overwritten initial binary was retained.

The next run was `2 failed, 21 passed`: one synthetic omission fixture lacked
required raw fields, and its 5000-deep recursion test incorrectly assumed the
installed C recursion budget matched Python's. Fixture fields were completed,
the actual deep behavior was tested and the qualification difference is now
explicit. Raw failed logs/XML are archived alongside successful ones.

All processes from these component tests exited. Local clients/stores close in
the normal fixture teardown; the initial crashed process's descriptors were
closed by process exit. No unknown/external process was touched. There were
zero Worker/model/Mock exchanges, full-tail chains or G0 windows, no grant, no
real account/model/network business call, and no new credentials, fees or
permissions. Test transport/Worker/model entry points fail if invoked.

Official API references used during implementation:
[iterator protocol](https://docs.python.org/3.12/c-api/iter.html),
[reference counting](https://docs.python.org/3.12/c-api/refcounting.html),
[exception handling](https://docs.python.org/3.12/c-api/exceptions.html),
[type objects](https://docs.python.org/3.12/c-api/type.html).

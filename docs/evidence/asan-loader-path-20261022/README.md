# Fixed ASAN preload identity (2026-10-22)

Base: `41e7be81bd6240f3727c099685b50d01dfbc5262`. Same Sim environment,
single writer, clean start; live development remote equalled HEAD. No model,
Worker, Mock, account, G0, Cold2, W5, installation or permission changes.

The previous final ASAN failure is preserved unchanged in
`../c-qualified-routing-20261021/`. Its loader searched for GCC's symlink text,
whereas Linux reports `/usr/lib/x86_64-linux-gnu/libasan.so.8.0.0` in maps.
The fix accepts only that fixed canonical path or the fixed GCC14 symlink
spelling, with the existing pinned runtime SHA256 and an executable mapping
of the same device/inode. Hash and stable metadata are read from the same open
file descriptor; identity/content changes reject. Reading-induced atime updates
are allowed. The loader does not discover, install or load other libraries.
Interpreter, ABI, source, headers, command, binary digest and private issuer
checks remain. Release does not enter the ASAN gate.

Existing installed compiler rebuilt both unchanged C binaries, reproducing the
release `a9c32db0f64ab4a8f901a5c7c5dc3cf32cc72c67573437f38b7ec306459510f2`
and ASAN `3cca77d9b8eecc2d8f583bff44bd7a80be914011a9952c038c10a8a4d3d68b89`
digests. Isolated build receipts are archived. Initial invocations used the
base interpreter lacking pytest and exited before tests; their logs are also
retained. All test runs then used `.venv/bin/python`.

Targeted release: **51 passed, 1 skipped** (9.79s). Targeted ASAN:
**52 passed** (12.06s). These independently ran concurrently, so their timing
and embedded component benchmarks are not performance evidence. After the
same-fd and atime refinement, final loader tests: release **15 passed, 1
skipped** (0.15s), ASAN **16 passed** (0.24s). A same-environment restart removed
the temporary final four-case logs before archiving; after checking no old
processes remained, only the loader tests and identical builds were repeated
under persistent `/workspace/sim2act-asan-loader-20261022/`. Earlier archived
logs remain unchanged. Positive ASAN assertions pass the actual preload
gate and load the qualified backend; negative gate assertions forbid extension
initialization. Cases include link/canonical spellings, absent/deleted/neighbor
paths, non-executable mapping, inode/device mismatch, malformed maps, wrong
digest/link, and metadata changes. ASAN used
`detect_leaks=0:abort_on_error=1`: no claim of leak detection or absence of leaks.

Commands, stdout and JUnit XML are compressed in `originals/`, hashes in
`manifest.json`. No full semantic chain or real-clock qualification was rerun
for this loader-only fix. Old G0 status is unchanged.

References: [Linux maps fields](https://docs.kernel.org/filesystems/proc.html),
[Python file descriptor stat](https://docs.python.org/3.12/library/os.html#os.fstat).

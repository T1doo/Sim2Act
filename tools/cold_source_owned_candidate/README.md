# Uninstalled Source ownership candidate

This directory preserves ongoing core ownership work. Nothing under `src/`,
`setup.py`, the worker, or the desktop imports or enables it. It does not shorten
production graph checks, hold a permission, or prove a performance improvement.

The candidate captures Source models and complete row/raw storage using one
identity memo. Its data contains only immutable builtins and original immutable
leaf references. A separate native binding retains shared outside anchors and
scopes owner identity to nonce/epoch/phase. The direct native image/current
matcher checks exact catalog types, all model storage, field-name sets, row keys,
all data positions, safe indexes, original leaf identity and bidirectional
aliases, including the outside boundary. Numeric cycles and unreachable image
nodes are rejected separately from completed DAG aliases. Automatic GC is disabled only during
the bounded native live read and restored on all exits, preventing tracked
temporary allocations from running GC callbacks inside that interval. Hash equality does not replace content.
The binding is not graph liveness, SQL authority, or a cached PASS.

**Known failing handoff condition:** the native verifier still trusts the
Python-provided synthetic-leaf flags. A forged flag can make an ordinary leaf
accept an equal clone. `probe_untrusted_virtual.py` reproduces this and exits 1
on the current build. Native consumption positions must establish synthetic
qualification independently; unused/invalid carrier, catalog and virtual
metadata must also be rejected. Until closed, this is not a complete handoff
proof even when its supported-input regressions pass.

Still required before production: fixed schema/callee/config qualification;
atomic publication/cleanup on the actual graph; fresh Ledger Slot joins; every
Source consumer migrated; unknown/capacity fallback before publication;
mutations at all publication boundaries; and the original large-flow comparison.
The current diagnostic tests use synthetic SQLite fixtures without model calls
or Worker execution. They are not end-to-end acceptance.

Explicit Linux CPython 3.12 check (does not install the extension):

```sh
.venv/bin/python tools/cold_source_owned_candidate/build.py --output-dir /tmp/sim2act-source-candidate
SIM2ACT_SOURCE_OWNED_CANDIDATE_DIR=/tmp/sim2act-source-candidate .venv/bin/python -m pytest -q tools/cold_source_owned_candidate
```

Windows build/qualification is pending. This candidate must not enter a desktop
release or be presented as the full Source-family migration.

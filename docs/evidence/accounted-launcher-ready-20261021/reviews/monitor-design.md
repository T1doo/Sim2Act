# Launcher profile preparation: independent static design review

Decision: **ACK_NARROW_PREPARATION_DESIGN; NOT_READY_FOR_EXECUTION**. The proposed VFS-independent protection unit and explicit finite profile are appropriate preparation. Required protections still need same-interpreter passing evidence, the complete config is not yet specified, and no grant/window is created or approved here.

Scope: read-only current guard/launcher/unit/candidate/budget source and earlier review evidence; write only this `/tmp` report. No code, tests, DB, Mock/model/Worker, G0, prepare/commit, profile or signals were executed by this reviewer; no repository files were changed. HEAD observed: `09b58a414a6db0665de759ff77dfb51bb2b735b7`. This is a design review rather than a frozen implementation ACK.

## Four skipped tests and the actual protection gap

The four existing skips have one shared `G0_UNIT_NATIVE_LIBRARY` dependency:

1. `test_native_vfs_local_sql_only` installs the old VFS.
2. `test_native_size_cap_and_sticky_open_failure` tests old per-file hard limits/sticky native faults.
3. `test_native_rejects_linked_database_before_touching_target` tests old VFS link handling.
4. `test_child_io_closes_uri_alias_attach_and_unbounded_python_write` also installs VFS before exercising the still-relevant child-I/O controls.

The current monitored launcher calls `install_child_io` directly, without `install_vfs` or `same_sqlite_api`. Its SQLite subclass/authorizer, Python audit hooks, aliases and network denials do not intrinsically need the optional native VFS library. Therefore the first three skipped tests are not failed qualifications for a claimed hard quota: the actual contract is explicitly sampled 64 MiB. They must remain honestly skipped and must not be relabeled passes. The fourth skip does leave relevant composed child-I/O behavior without that mixed test's execution evidence; isolate it rather than changing interpreter or silently reinstating a VFS requirement.

Minimum new unit design:

- A fresh standard-library SQLite-only subprocess under **the same `sys.executable` used by the launcher**, with its own parent-created temporary directory; no alternate `G0_NATIVE_UNIT_PYTHON`, VFS library/API discovery, product/fixture/Mock imports or G0 business path. Parent cleans the unit directory after child exit because the audit hook intentionally remains installed for the child's lifetime.
- Positive patched connections through the intended `sqlite3.connect`/`sqlite3.dbapi2.connect`/`_sqlite3.connect` paths must be the guarded subclass on the sole exact DB. Ordinary local create/insert/commit before arming, SELECT and ROLLBACK after arming must work.
- URI/factory/other-path rejection, ATTACH denial, pre-arm-primed cached DML and direct DBAPI DML denial, authorizer non-disarmability, raw FileIO write denial and DNS/socket/process boundaries should fail at the intended gate before the prohibited action. These are unit SQL/adapter checks, not an actual G0 run.
- **Captured pre-patch raw connect alias must have its own terminal child case.** The audit `sqlite3.connect/handle` event occurs before the unguarded connection finishes initializing. Current source explicitly relies on an uncaught Boundary ending that child. Do not catch it and continue using the process or claim successful native-handle cleanup by calling close on an uninitialized handle. Expect the appropriate Boundary/nonzero exit and absence of any continuation marker; process termination is the cleanup boundary.
- Test the actual composed layers relevant to the launcher. `install_child_io` audit denies connect/bind/DNS/process events; `install_network_denials` additionally patches socket send/HTTP synchronous and asynchronous handlers/model fallback. Do not claim audit alone proves every send method is blocked. Existing separate pure network and owned-group cleanup units may supply their own evidence; a local fake HTTP/model namespace is sufficient to verify hook rejection before original callbacks without importing a business transport or creating a model.

The current authorizer cached-SQL test and real owned-dummy-process cleanup test already use `sys.executable`/actual SQLite or owned subprocess behavior. Keep these meaningful checks and existing scope/identity failures. Bind final unit source/logs to the same launcher/guard/interpreter/SQLite extension hashes that will appear in the frozen description. A missing, skipped, failed, mismatched-interpreter or wrong-SQLite qualification for a **required** protection is a refusal to start, not a reason to swap interpreters, assume the same native API or count optional VFS skips as success. This review does not request running the skipped VFS build/matrix.

## Proposed finite profile: permissible ceiling, not qualification proof

The proposed bounds are explicit finite values: nodes 60000, edges 120000, depth 128, leaf bytes 8 MiB, private encoded bytes 64 MiB; resident logical units 512 MiB and peak logical units 1 GiB. A required field is still missing from the proposal: exact positive **`integer_bits`** must also be chosen and frozen. It cannot be silently inherited from a fixture or inferred from JSON size. Runtime recursion/digit restrictions may make this admitted subdomain smaller; depth128 is not a promise to accept every depth128 source value.

Proposed work ceiling `2 * 8 * (2*nodes + 2*edges + 2*encoded_bytes + 1)**4` can be encoded as an exact integer with a named/versioned formula and explicit operands. `_Arena.classify` charges `8*(joint_packet_nodes + joint_packet_edges + joint_encoded_bytes + 1)**4`, so the inner expression bounds that one charge when both family packets meet the per-packet bounds. The additional factor two is a chosen margin/ceiling. It does **not by itself prove** that all projection, full-frontier sizing, snapshots, equality, encoding, Source JSON and continuation charges fit. No CPU duration follows from a fuel value this large.

Likewise the bounds are not an all-inputs-fit promise. At the maximum two-packet node count, the arena's node term alone is `8192 * 120000 = 983040000` logical units, already greater than 512 MiB, before its edge/scaffold/packet/continuation reservations. Such an input should fail admission into OWNED and take pre-issuance LEGACY, while preserving all original validation. This is legitimate bounded optimization selection, but not proof the complete actual Cold input will be OWNED. Once issuance starts, capacity/protocol errors remain fail-closed without fallback/replay.

Private `encoded_bytes=64 MiB`, resident512 MiB and peak1 GiB are different logical/memory accounting domains from the existing **64 MiB sampled on-disk directory budget**. They neither expand that disk contract nor establish process RSS/GC/allocator/native heap or original SQL/full-guard memory bounds. The proposed profile must be described as a finite experimental ceiling with full-input eligibility/OWNED still unproven, not a derived production allowance or performance qualification. Original lease30/per-Run300/TTL1800, six/eight exact prefix, 480/120/600+10 and no real network/model remain unchanged.

Profile identity, complete exact bounds/limits, the formula version/operands/evaluated integer, test/runtime/source provenance and disk policy must be frozen in the **same description and exact-match grant**. Default profile must remain None/legacy; wrong/unknown profile or mismatched config cannot be accepted by a generic old consumed grant. No caller-supplied executable expression, implicit giant fixture allowance or unreviewed interpreter is part of this design. This preparation creates no such grant.

## Minimal honest outcome record

Use fixed bounded scalar records at the existing target/call boundaries, not per-pin logging, extra scans, serializations or DB reads:

- Frozen profile/config identity and selected route `NOT_SELECTED / NOT_REACHED / LEGACY / OWNED`; for LEGACY a fixed admission capacity/unsupported reason if actually captured, otherwise explicitly unknown. Do not invent a reason after the selector has discarded its exception.
- Original first-binding and candidate-selection milestones; original first-commit entered/returned and second-commit entered/returned separately. Mark returned only after the actual original call returns. A helper replay, `phase=COMPLETE` alone or two iterations of a lower helper loop is not both complete commits.
- Whether original graph context exit/final check completed; existing static W5-before-stop label remains a static boundary statement rather than a newly invented observed write counter.
- Original finite/stop diagnostic when available, preserving its clock/end/deadline/lease values and named minimum; otherwise NOT_REACHED/UNKNOWN. Do not perform new protected reads or infer deadlines from the outer 120-second timer.
- Bounded native ledger/route/peak/work/release summaries from already maintained scalar state, captured before losing lifecycle evidence, plus existing Mock counters, authorizer denials, parent sampled disk/time and owned cleanup evidence. No raw facts, graph reconstruction, extra profile or whole-RSS claim is needed.
- Selected-context errors retain UNKNOWN and undetermined original/candidate provenance unless separately proven; preserve the original exception object/cause and existing cleanup. A completed context with LEGACY is not native acceptance, and OWNED with an expired lease is not success.

These fields can support a later concrete review of one proposed execution. They do not establish full input fit, complete prepare/commit behavior, a G0 speedup or authority to consume a new window now.

# Native row semantic pair — frozen preflight

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

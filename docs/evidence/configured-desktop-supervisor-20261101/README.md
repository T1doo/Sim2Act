# Configured desktop supervisor: source integration and real cloud slice

Source: `1d4835a4c32e9ca68916eab9e99ac8d7afb8b895` on
`dev/cloud-g0-live-20261028`, parent `b319d53a0e7797ce2d29207a6aeac7b2705f665f`.
The source was committed after these exact application bytes passed review and
regression. The final ten-test flow includes the additional user cancellation
assertion; the core 96-test run predates only that test assertion, not a different
application implementation. Manifests still bind the exact new source inventory;
no authorization, approval, source pin, lease or commit guard was removed.

Implemented the installed configured supervisor and native host route, sharing
the original manage.py config/approved-selection prechecks. API and Worker are
separate owned processes. Both roles bind private receipts to session/role/PID;
activation requires both real role READYs. Parent STOP/EOF follows ordinary
service shutdown, not process kill or a fabricated user-cancel state. Global
clean stop requires actual matching role STOPPED, exit 0, both output EOFs and
finished readers. Undrained preflight or heartbeat, identity failure, timeout
and unknown exit retain the claim. Original worker branches all register their
real heartbeat handles. Configured origin/profile identity includes complete
connection namespace options; unknown/cross-binding profile state is preserved
and refused before navigation.

`actual-test-only-processes/` contains actual controller receipts from Linux
CPython 3.12, original API/Uvicorn and original Worker in distinct processes,
loopback HTTP and an explicit TEST_ONLY SQLite fixture. The positive flow:

1. Create project and CSV (`A,10` / `B,20`), publish the existing deterministic
   internal sum application, run it and save `SUCCEEDED` / sum `30`.
2. Retry the original request key and receive the same Run.
3. Prepare a separate CSV report through the normal API; cancel it before
   confirmation using its actual version; observe `CANCELLED`, no result.
4. Stop both owned roles normally, verify matching receipts, exit 0 and both EOFs.
5. Start a new controller/API/Worker process trio against the same directory;
   retain the same origin, original sum result/material, original Run key and
   cancelled result. Stop via parent EOF with the same complete receipts.

The saved `actual-test-only-processes/database-final-observation.json` records
the read-only method, SQL, exact DB digest and counts: one SUCCEEDED and one
CANCELLED Run, zero model attempts and zero reservations. All data is generated
project test material; no real provider or private user document is involved.
Controller timeline values are monotonic elapsed time since Popen;
`stopped_elapsed_seconds` is not latency measured from a STOP request.
The actual blocked-app-heartbeat test separately proves that the old two-second
join does not make a still-live sender disappear from service cleanup.

Evidence scopes (overlap; do not add these counts as unique tests):

- `final-dual-process-flow.xml`: 10 pass, zero failure/error/skip, 16.936 s.
- `reviewed-core-regression.xml`: 96 pass, zero failure/error/skip, 37.918 s;
  original config/selection, finite lease/commit/cancel and qualification negatives.
- `locked-ui-regression.xml`: 27 pass, zero failure/error/skip, 35.295 s;
  JSDOM actual HTTP/worker UI protocol, not pixels/native Windows. Its 37 cached
  dependency versions matched the existing engineering lock; no download.
- Original broad 9 failures are retained. Eight were a missing fixed Node
  dependency path and were resolved for the complete 27-test UI run. The remaining
  PB diagnostic replaces protected callees after immutable contract issuance and
  fails before dispatch. The parent b319 source fails the same exact test at the
  same PB entry check (`parent-same-pb-diagnostic-failure.*`). Neither this test nor
  the production integrity check was weakened. This is a still-failing diagnostic,
  not a claim that the full repository suite is green.

Independent source review found and then confirmed fixes for incomplete heartbeat
ownership, query namespace binding, unbounded preflight observation, shared
cross-configuration browser profile, and parent/child libpq default differences.
The reviewer ran no PG, Windows or model execution and did not modify source.

The frozen C# host compiled with the existing pinned Microsoft compiler,
.NET Framework references and WebView2 SDK on Linux. See actual compiler logs and
`host-build-result.json`: AMD64 managed Windows GUI EXE, 32,768 bytes,
SHA256 `29ce9e931ba6365a09260d8ad06bd68843c7cb7a44f9fdb870c291e384230c13`.
This is an internal **host component**, CROSS_COMPILED_NOT_WINDOWS_EXECUTED.
Its local component archive is 290,771 bytes, SHA256
`327fd227f44216c8acfdc4383cc1bfaed614f665f2a68d6bdc11fac126cd43f8`.
No new end-user preview/installer or Release was made.

Not run: configured PostgreSQL, new native Windows window/profile acceptance,
new same-version complete Windows assembly with PostgreSQL dependencies,
P-A/P-B live-model workflows through this supervisor, full R0 AT01–27/F3 and
large-Cold performance remeasurement. Existing PG configuration/selection is
not injected here. The old 042ab21c complete portable predates this source and
omits psycopg; it remains unchanged and cannot be relabelled as this integration.
The existing project-license/redistribution review is not replaced or decided.

Windows CI cumulative budget remains **487 / 900 runner seconds**, no new run.
No main/Release/deployment/PC/system setting or credential change. These results
reduce the missing configured desktop lifecycle implementation; they do not lift
R0 or final Release qualification.

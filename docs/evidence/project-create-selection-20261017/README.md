# New project selection and material target — 2026-10-17

This is a separate product slice after delivered cross-Release download SHA17b8b8cff345c96885dfb18dd52f4ae1a6b54454. It follows the project/resource scope in docs/平台产品设计.md§2,§5 and the FirstUse create/save workflow. Existing project creation and resource Save APIs and authorization policy are reused. No new executor, Grant semantics, schema, or backend mutation path is introduced.

Frozen source2acb62e5bcc2c596bcb591d109433243691aeecb changes only product app.js. Creation uses the actual returned project ID, then performs the existing complete project change event and awaits that refresh. All existing resource-preview/download, project impact and recovery listeners run. A project selection generation prevents late automatic selection after manual project ABA; identity plus connection generation blocks old identity callbacks. Project list generation drops older list responses. The first pending request disables creation and blocks an extra submit before its first await. These pending guards do not implement new durable creation receipt recovery.

## Actual red baseline

Baseline8ac81a931b425e7d58d34d3c9105bd916dc778ff added only isolated tests; product bytes matched17b. One actual full-page authenticated ASGI/JSDOM execution failed RC1, JUnit6.290s. It recorded the returned B ID, actual current A ID and visible A context; subsequent explicit FileReader Save really POSTed A/resources, and a read-only SQL oracle confirmed the new synthetic material belonged to A. The pending duplicate click also actually produced a second creation POST. Full originals are preserved. This is a visible executed reproduction, not a static diagnosis. Final test additionally exercises a submit event during the held reply.

## Executed product acceptance

Only tests/test_project_create_selection.py three parameters are the product acceptance gate, each with a fresh synthetic SQLite fixture and real authenticated ASGI APIs, full served JS, JSDOM and actual FileReader:

- create-save: create B while A selected, hold accepted reply, attempt duplicate click/submit, use returned B as current selection, refresh B, explicitly save exact UTF8/CRLF synthetic file to B, verify current context/material list and one creation POST plus one Save.
- late-manual: hold the actual create response, manually select other→A, then hold the actual post-create project-list GET and repeat other→A. B remains discoverable while the latest manual A selection/material scope stays current. One creation POST.
- late-identity: after the accepted identity-A creation is held, use the real identity switch/connect controls to identity B. Delivering the old reply neither selects nor lists the new A-owned B project, nor repaints A material. One creation POST.

Every parameter checks all48 tables: every original row remains unchanged, every project_id=A scope is exactly equal, only the expected tables gain rows, the new project is exactly returned B, the new principal is exactly its runtime, all added grants target B, and only create-save adds exactly its one B resource. Existing backend creation policy legitimately creates the runtime and own artifact.save_text Grants; the report does not claim zero new Grants. Worker/model calls are0; no execution/release/approval POSTs occur.

Author3PASS/0FAIL/0ERROR/0SKIP, RC0, JUnit12.878s:21 checks,124 API requests and4 POSTs across three distinct cases. Pytest's current-directory symlink is excluded from counts. Independent3PASS/0FAIL/0ERROR/0SKIP, RC0, JUnit13.112s at the exact frozen source, with13 file hashes identical before/after. Its report and full originals are preserved. Independent repetition adds zero unique nodes.

## Additional old focused test did not pass

One additional tests/test_background_poll.py attempt failed RC1/JUnit1.986s at phase reached after four health checks. The same unmodified driver run against app.js copied directly from delivered17b also failed in that phase. Its synthesized health fixture uses lower-case up; both delivered and current product validators require upper-case UP, and this slice does not change that code. A later old catalog URL mock also statically predates metadata_only; that path was not dynamically reached/diagnosed. The raw failures and frozen baseline copy are retained. This old synthesized harness is not counted as a passing gate, and the adjacent previously-covered recovery matrix was not repaired or rerun. The new three actual HTTP cases and independent review are the limited feature conclusion.

## Provenance and boundaries

Originals manifests map each new source/log/XML/DB/result/proof to archived size/SHA256; deterministic gzip has mtime0. SHA256SUMS covers repository evidence except itself. Verification compares archived bytes, decoded originals and these slice live originals only. Full command, terminalRC, JUnit, source before/after and independent report preserve provenance. Earlier evidence batches are not mass-reverified.

PG, native browser/Windows, real models, semantic/business scenarios, remote CI/Actions, deployment, unknown create receipt/retry recovery and other family/fault matrices are NOT_RUN. No old full-disk independent-report gap is recovered by these reports. No release publication or deployment occurs.

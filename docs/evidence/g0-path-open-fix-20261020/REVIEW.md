# Path.open adapter independent review

Decision: **ACCEPT_LOCAL_PATH_OPEN_COMPATIBILITY_FIX_NO_BUSINESS_RETRY_AUTHORIZATION**. No material blocking finding in the reviewed patch.

Base HEAD: `f2d21775ff1cd9119cd900b07217b4dc96b6484a`. Reviewed source hashes are recorded in REVIEW.json and remained unchanged before/after the independent test. Only g0_guard.py and test_g0_guard.py had tracked changes.

CPython 3.12.14 pathlib.py:1006-1013 forwards buffering, encoding, errors and newline positionally to io.open. The old adapter rejected these normal arguments. The new explicit signature accepts those defaults, resolves default/locale encoding only to UTF-8, and retains strict UTF-8 byte conversion. Explicit strict and UTF-8 aliases have equivalent encoding semantics; UTF-8-SIG and non-UTF-8 codecs cannot pass the canonical codec-name check. No newline option other than None is allowed.

The exact original two root log paths and mode "a" remain required. Binary, update, truncate, create and other modes remain denied, as do nondefault buffering, custom opener and closefd=False. Reads delegate through the original io.open. Writer allocation, byte reservation, short-write handling, byte caps and I/O-error propagation are unchanged. The patch does not alter product code, auth, deadlines, Mock/G0 budgets, launcher or prefix. g0_bounded.py and g0_prefix.py match their prior reviewed hashes.

I independently ran exactly:

`PYTHONPATH=scripts/diagnostics .venv/bin/python -B -m unittest test_g0_guard.FixtureOpenInterfaces -v`

Result: **8 passed, 0 skipped, exit 0** in 0.003 seconds. The tests exercise actual Path.open, io.open and builtin open with real temporary files and the same two patched open entrypoints, both original log names, Unicode, default/explicit signatures, negative options/path/mode cases, strict/type errors, byte budget and underlying I/O failure. They import no Sim2Act module; each test checks this. Raw independent output is INTERFACES-INDEPENDENT.log.

Parent evidence read separately: BEFORE.log reproduces the old adapter error including pathlib forwarding; PURE-UNITS.log reports 31 total / 27 passed / 4 skipped; RUFF.log reports success. I did not rerun the wider suite or native checks.

This resolves the demonstrated local interface incompatibility. It does **not** establish a successful business prefix or G0 result and gives no business end-to-end guarantee. No new fixture, DB, transport, Mock, G0, launcher or window was executed by this reviewer. The old failed run and consumed grant remain unchanged; a retry under the same upper bounds still needs fresh explicit execution authorization.


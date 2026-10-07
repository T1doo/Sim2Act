# Optional DOM dependency probe correction (local candidate)

The original Windows CI [37574285701](https://github.com/T1doo/Sim2Act/actions/runs/37574285701), source `00a469693144c657192506b52c3de24bdc06d135`, ended FAILURE: 900 PASS, 6 SKIP, 1 FAIL. Its existing optional `require.resolve('jsdom')` probe exceeded the unchanged 10-second deadline in CPython's stdout-reader join. The trace does not establish why the process/output reader was delayed. Root cause beyond that observation remains UNKNOWN. [Original terminal evidence](../task-history-publish-20261007/ci-result.json) and decoded failure excerpt remain preserved.

The bounded candidate removes unused stdout/stderr pipes from the two existing dependency probes by directing them to DEVNULL. Only returncode was consumed. This removes the observed output-reader path; it is a proposed remediation requiring Windows verification, not proof that the underlying delay is solved. The 10-second deadline, missing dependency skip rules, uncaught TimeoutExpired failure, and actual HTTP/DOM driver output capture and assertions remain unchanged. No product, browser sandbox, workflow, credentials or permission changes.

Local results:

- Two existing affected modules: 19 PASS, 1 warning, 33.00 seconds.
- Explicit missing jsdom environment: 2 SKIP, 1 warning, 0.16 seconds; existing optional dependency behavior.
- Both modules plus four negative cases: 23 PASS, 1 warning, 34.66 seconds. Each real probe is exercised with synthetic missing-dependency and TimeoutExpired outcomes; the latter must raise, never skip.
- Initial negative fixture run: 2 FAIL, 21 PASS. The HTTP test imports subprocess/shutil inside its function, so patching nonexistent module attributes failed before the probe. Corrected fixtures patch the shared stdlib modules. Both logs retained; no product defect is inferred from this fixture failure.
- Ruff and git diff check PASS. Independent review confirms normalized AST identity outside probe output destinations, unchanged deadlines and execution oracles.

Protected Edge was skipped after the original engineering failure; new PNGs NONE, pixels NOT_RUN. No new push or CI run, no real model request. The steps/wait-reasons slice `9f30cd2e009211fd983d98ef8103ca5448e8dba5` remains a separate local commit and is excluded from this candidate. Protocol whitespace and unpublished activation changes are excluded. Full P-B, F1, AT02, Win11 and formal release are not signed off.

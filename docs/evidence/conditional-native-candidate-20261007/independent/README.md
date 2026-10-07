# Independent conditional native candidate review

PASS for local candidate only. Final shared actual HTTP/JSDOM oracle: 22 checks, 1 passed (13.88s); initial 20-check run retained (14.67s). No product edits, push, CI, real model, experiment preparation, new identity or authority performed. Exact SHA256 in review.json.

Resolved during review: planned bad human report check absent initially; shared oracle now additionally checks fact edits invalidate prior evidence and wrong report remains FAIL with semantic UNKNOWN/user PENDING. New optional jsdom probe originally captured output; now DEVNULL with unchanged 10s timeout, actual driver capture retained. Both old 20 checks preserved in order. Probe timeout still raises failure; missing dependency skips original way: independent 2 passed.

Additional proof: console-negatives.cjs extracts the actual internal-ui expectedProtocolError callback and verifies 10 cases. No pageerror, cross-origin/other project/source, 500/404, unexpected script, or old protocol409 is newly ignored. Fixture negative log independently verifies full-row exact resource two-field changes/restoration and atomic rejection of repeated controls; no authority was restored or created.

Reproduce from /workspace/Sim2Act-conditional-native:

```bash
NODE_PATH=/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules /workspace/sim2act-pb-venv/bin/python -m pytest tests/test_conditional_native_oracle.py -q
/workspace/sim2act-pb-venv/bin/python -m pytest /tmp/conditional-native-independent/test_probe_negative.py -q -o pythonpath=/workspace/Sim2Act-conditional-native/src
node /tmp/conditional-native-independent/console-negatives.cjs
```

No new PNG/output slot. Existing protocol26 helper, Windows runner/workflow, product src and cleanup unmodified. Conditional result nested in existing protocol-results.json. New phase does seven bounded fixture CLI calls, two protected renderer audits and real 2700ms polling wait. Entire existing browser helper limit remains150s, browser step4min, job15min and predicate12s. Local DOM runtime does not establish aggregate Windows capacity or native safety/pixels. Linux protected SUID launch remains BLOCKED; Edge/pixels/Windows aggregate/new CI remain NOT_RUN. Evidence copying should omit fixture databases and artifact directories.

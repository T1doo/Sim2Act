# Warm workbench: task hierarchy and explicit result states

Base: `ef678365900f079971928f1a4631da0e6256cd82`.
This slice changes three frontend source files only. No backend, approval,
request body/key, lease, model or G0 behavior changes.

- Task history now separates the complete goal summary, persisted technical
  status, saved submission mode, accepted time and short ID. The original
  identity/project callback and safe action remain in place. Unknown modes and
  states remain explicit; technical SUCCEEDED never means semantic acceptance.
- Result presentation keeps all four original semantic/review/owner/publication
  values, with distinct warning emphasis for UNKNOWN and waiting values.
- Warm separators, scoped task form focus/disabled states, and a 140–160ms
  disclosure/button transition complete this reading surface. Reduced-motion
  disables transitions; no animated progress, result or success is fabricated.

## Actual evidence

`plan.json` was saved before four local Node commands. `execution.json` records
their exit codes, elapsed times, and identical before/after source hashes.
Each command ran once and exited 0:

| Local command | Scope | Assertions | Elapsed seconds |
| --- | --- | ---: | ---: |
| `node tests/workspace_task_hierarchy.cjs` | Real template/controller, synthetic GET adapter; text injection, status/long-text structure, old-button scope, read failure, CSS declarations/contrast | 10 | 0.853076 |
| `node tests/protocol_reading_view_ui.cjs` | Original controller + DOM/MutationObserver; sealed synthetic Source output, four states, invalidation, hidden next actions, polling disclosure retention | 17 | 0.417163 |
| `node tests/resource_directory_scope.cjs` | Existing current-project directory failure/late response/identity regression | 15 | 0.394007 |
| `node tests/workspace_density.cjs` | Existing scope navigation and original form placement/focus regression | 6 | 0.430521 |

These are four processes and 48 assertions, not 48 independent integrations.
The four tests' adapters recorded 5 + 22 synthetic GET calls, with zero HTTP,
POST, Worker, model or G0 calls. The separate preview generator has no adapter
request trace: its fixed call graph invokes three synthetic GET adapters per
version; this static count is not part of the 27 recorded test calls.
All JSDOM windows closed in `finally`; no server/browser/CI
was launched. New status color ratios on their declared solid backgrounds:
active 6.986160, uncertain 6.221348, error 7.289125, technical complete 7.456255.
They do not prove all rendered text contrast or geometry.

## Before/after preview and limits

[Before](before.html) and [after](after.html) are self-contained **static DOM
previews, not screenshots**. `preview.cjs` uses the original/current product
controllers, same sealed synthetic Source payload, and identical explicitly
synthetic history labels/times. CSS is source-bound and embedded; scripts are
removed; CSP blocks network and form submission. Controls do not connect to a
backend. `preview-manifest.json` records all four asset hashes per version and
each HTML byte count/hash. A viewer can resize these files, but no viewport
layout, native keyboard behavior or animation frame rate was verified here.

Previously captured PNGs were inspected to identify the log-like task list;
they are older source versions and are not evidence for this patch. The existing
local protected-browser sandbox prerequisite remains unresolved. No browser
retry, sandbox change, new CI/device window or download was attempted.

Independent source review is limited to this UI diff and the recorded scope.
Current pixel acceptance and native smoothness remain **NOT VERIFIED**.

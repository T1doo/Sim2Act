# First PostgreSQL failure: retained before any product edit

Frozen source: 42b7a992524d9f2e00136711c70cb4e16f3e419b.
The first failure marker is test index 1377 (zero-based):
`tests/test_natural_goal_ui.py::test_natural_goal_actual_http_ui[valid]`.
The actual Node failure is `Cannot read properties of null (reading checked)`
after the `validation-failed actual response projection closes controls` check,
when rereading the valid plan should show a fresh unchecked acknowledgement.

Read-only diagnosis while the original full suite continues:
`showRun` advances `runSelectionGeneration` for both foreground selections and
background polling. A foreground read clears its displayed result immediately;
a timer read starting during its API/async plan render supersedes its generation.
The foreground returns without rendering a complete plan, while the timer may
still be awaiting I/O. Explicit action completion can therefore expose an empty
confirmation area. Background polling is real page behavior, not a test-only
fault. This is a hypothesis to verify after preserving the complete first round.
No source or original test edits or parallel retry were made during the full run.

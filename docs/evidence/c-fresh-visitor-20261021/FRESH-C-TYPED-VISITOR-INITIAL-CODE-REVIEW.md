# Optional fresh C visitor: initial code review, not final ACK

Only static inspection. Reviewer did not build/import/execute C or Python candidate code, tests, DB, Worker, Mock or G0 and changed no repository files. Default runtime remains unmodified. No production or execution-window approval.

The first C draft read by the reviewer used borrowed descriptors from builtin `tp_dict`. The author subsequently reported an immediate segfault and an ASAN diagnosis at that lookup: this interpreter's builtin `tp_dict` was NULL. Reviewer did not independently execute that probe or discover this defect before the author reported it. The updated source was then inspected with public `PyObject_GetAttrString` retrieval, strong owned references, explicit NULL checks and matching cleanup.

Updated source snapshot inspected:

- C: `63be5a788cf1450f15ca164e98651c95a9de7351340a49636e7cd50289da90c0`
- adapter: `b2d9feb14b34004808c140a8318f7dfbdf2f1105bbb685f53e0ef0d966977a05`
- build script: `bd8c90beeb28202bd78d5e733a805c98bdfd7e80c5d87b1732c1bc807111dc9c`

No obvious double-free was found in the updated result/seen/iterator cleanup: memo hits are INCREFed, new child results are cleared after insertion, tuple conversion transfers its new owned reference with `Py_SETREF`, and its temporary is cleared without a second DECREF. Errors are fetched before cleanup and restored; active/seen are per invocation and cycle checks precede completed memo. Dict/list iterators preserve original iterative shape rather than shallow-copying values. The model metadata reads and subsequent short-circuit checks appear in the original order. These observations are static and do not prove memory safety under allocation failure or all descriptor behavior.

The reviewer identified a concrete omission-predicate risk in the first draft: a foreign key inserted after the original key gate must receive original Python equality semantics, not be blindly passed to a Unicode-only API or a new late rejection gate. The author added an exact-str fast path and `PyObject_RichCompareBool` fallback, which closes that dispatch issue.

One narrow remaining semantic point was sent to the author: the fallback currently constructs a new `'value'` / `'when'` string, whereas original code compares against its compiled identifier literal. A foreign equality method can distinguish the identity of that right operand. Interning those fixed identifier strings (or supplying the actual original literal constants) would avoid this discrepancy. No arbitrary process-wide code-integrity mechanism is requested; this belongs to the fallback's stated callback-equivalence goal.

The public raw C entry checks type tuples/callability before unchecked tuple access, and a require callback that returns instead of raising creates RuntimeError rather than continuing after a failed predicate. The adapter checks original helpers before native work and does not retry after native failure. It remains explicit offline selection, with no automatic backend discovery or product routing.

Recursion threshold equivalence, all raw ABI misuse, descriptor/iterator mutation, error-identity and allocation-failure behavior remain test/qualification matters. CPython C recursion checks and signal polling are present but do not establish the same Python recursion threshold or production eligibility. Author compile success alone is insufficient. Final frozen source and actual no-Mock evidence should be reviewed separately after the remaining narrow fix.

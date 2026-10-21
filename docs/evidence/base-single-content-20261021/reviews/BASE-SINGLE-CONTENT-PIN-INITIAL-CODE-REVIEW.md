# Native _base single content pin — initial code review

Status: **NOT ACKED — three concrete P2 closure issues identified.** This is an intermediate source review, not an execution/grant decision. Reviewer ran no code, imports, tests, database, Mock or signal and made no repository edits. Findings were promptly sent to the sole writer. Source was undergoing authorized corrective edits after the first read; this is not a final frozen-hash signoff.

Intermediate source read: `_cold_base_segment.py` SHA256 `71ae05582348b5fd7d7322ef83bbd13da85b9c9c126dd970732a30b24ba52ac2`; runtime `2aa6ae8bff793f53f728aaf124847ee401a8efd3ea330dcf8002c30159fa125e`. The later partial correction read of cold_accounted had SHA256 `7b5d0e53d338acc52e2ac3b492eda74915b6dd9a344b24220efcddb51f0a259b`; its new exact storage gates close some, but not all, examples below. Earlier readiness gates were narrower.

## P2: class code identity does not qualify actual instance dispatch

`_cold_base_segment.eligible:30–38` checks class functions. Runtime `_base:2509–2527` invokes instance methods: `_native_base_mode`, `_typed_parameter_models`, `_typed_values_from_models`; mode methods are also called on mutable instances. An exact-class instance can shadow those names in its own dictionary while every class witness passes. A callable shadow can therefore execute before the delayed full content boundary. Require static resolution on the actual mutable instance or fixed-class invocation plus a shadow exclusion before eligibility; class-only witnesses are insufficient.

Public `_ColdGraphRead.check` additionally changed its original inline dynamic predicates into `self._check_dynamic(store,c)`. An instance shadow now suppresses the original lifecycle checks in a public guard that previously had no such dispatch point. Use the fixed class implementation, keeping public-check behavior intact. This issue is separate from whether the native candidate is selected.

## P2: control-table representation gate must cover the actual pure reads

The initial `_base_pure_ready` omitted several fields subsequently read by `_base_parameters_current`, `__assert_links`, `_Family._root` and stage joins. Foreign colliding keys in private inputs can trigger equality on lookup; an issued-table role value can trigger equality; scope active can trigger truth conversion; binding-header/current-header comparison can trigger equality. With simultaneous unused graph-root drift, the old entry codec rejects first with zero such callbacks, whereas the new path may execute them first. The partial correction gates exact table keys, issued tuple/role/packet, active booleans, binding strings and frame scalar types, addressing those examples.

The partial correction still accepts `type(complete) is MappingProxyType` and iterates/gets its contents to qualify it. That exact type can wrap a custom Mapping, so iteration/get can dispatch callbacks during eligibility itself. Nested generation proxies have the same issue. Fixed native stage predicates actually access complete.source/generated/generation/extraction. Eligibility needs original owned native-storage provenance for these proxy objects, or an equivalent callback-free representation check; merely checking proxy type is insufficient. Retaining original private allocation/origin identity is control provenance, not permission or cached mutable-content validation. Unknown representations must select legacy before dispatch, rather than execute the unknown iterator to decide.

## P2: initial native dynamic error bypasses entry-content error priority

Runtime `_base:2510` calls `mode._base_parameters_current` outside the collector's failure-content-check try block. For a changed unused raw graph root plus an already-set original worker.stop event: old entry full CGR rejects `Native mutable frontier changed`; new CGR dynamic header passes (it does not check stop), then mode dynamic rejects `Prewrite dynamic frontier changed`, and outer invalidation occurs without an entry content check. This counterexample requires no foreign callback or class mutation.

The proposed failure-only full check must be placed before any relevant close/invalidation if it is to restore the original mixed-error priority. A new full check after nested mode cleanup merely observes closed state and must not replace the original error with that artifact. Preserve dynamic gates and do not add a finally guard that overwrites arbitrary exceptions.

## Retained positives and next review boundary

The candidate keeps default/non-ready dual pins, retains complete actual/raw/fixed-dump checks, performs reached-class schema qualification using the earlier fresh code witness, and does not change SQL/clock/authority/transactions. The extracted collector retains the original family/stage/model inventory and normal exit full check. Those are the appropriate limited boundaries; no additional root migration, global cache, new component or G0 window is required to address these findings.

Necessary targeted source/test counterexamples are the instance shadow, proxy-underlying callback, control table foreign role/key, and raw-drift-plus-stop examples above. After closure, a newly frozen source review and the authorized complete configured semantic A/B should bind the final bytes. This intermediate report does not assert author tests passed, nor that an optimization is already safe or faster.

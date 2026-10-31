# Minimum next product change: per-use AppManifest ownership

This change is **not implemented by 4546ba43595eb1542d2f8fa209a146663875542c**. The disabled borrowed-cohort backend has zero ordinary-GC coverage and must not be used to claim this ownership transfer already exists.

The smallest next scope is one complete per-use AppManifest chain. Keep original-origin/extraction manifests, FrozenRunContract and every other cohort member on their current full validation path. A one-family migration must not remove checks for any still-mutable family.

## First producer and retained semantics

The per-use producer is `pb_natural_uses._bound_review_from_facts`, before its compiled manifest escapes through the bound result. It must run the original full typed/raw/schema validation before handing the actual storage semantics to a native read-only owner. Own all fields, exact numeric/container types, field order, selected-field metadata, extra/private state, both None-omission rules, serializer/schema identity and complete aliases/anchors outside the transferred root. A frozen `model_dump` alone is not this transfer.

No mutable Pydantic model from this family may escape alongside the owner. A known read-only owner/view is a new explicit schema representation; it must never masquerade as `AppManifest` or pass an old exact-class gate by weakening that gate. Unknown schema, capacity, hooks or outstanding external mutable aliases choose the entire existing family before publication. Late unknown changes reject/roll back rather than replay the producer or SQL.

## Consumers that must close together

- Per-use bound/review results, including the manifest-bearing element later exposed as `_ColdBindingGraph.use_value[1]`.
- All per-use compilation-result field access and serialization, preserving exact limits/actions/schema semantics; produce temporary plain JSON only at a real serialization boundary.
- `_ColdTrialGraph._typed_parameter_models`, which currently places this manifest and its saved raw in the repeated cohort; introduce an explicit owned-schema branch for this one family, while other manifest origins remain original triples.
- The matching `_ColdTrialGraph._fields`, source-manifest/link validation and raw publication. The new owner must be scope/nonce/epoch/phase-bound and rechecked at original boundaries, with the full untransferred graph still checked.
- Any original-origin/release consumer reached by that same per-use value, including origin tuple/lifecycle completion. If such an edge still consumes the mutable model, the family is not closed and cannot leave old whole-graph validation.

The other two AppManifest producer paths are `pa_spec_apps._cold_original_origin_prefix` and `pb_natural_specs._cold_verify_from_review`. They should initially remain original. A later whole-AppManifest-family rollout additionally connects their original-origin/generation/lifecycle/release consumers. Do not declare all three migrated after only wiring the per-use endpoint.

## Why this addresses the actual blocker

The present backend borrows externally mutable model/raw roots. Its extra allocation/snapshot timing can expose GC/signal callbacks between gates, so generic snapshot equality is insufficient. A fully owned data family retires those mutable aliases before any consumer sees the value. Complete native scans can then traverse the immutable owned representation without creating new Python data snapshots; fresh scope/root/config and outside mutable anchors still apply. This is a data-contract change, not a cached validation result, Graph, permission or PASS.

Fresh Run/version/fence/owner/epoch, authority/revocation/stop/both clocks and protected-read gates remain original. Five writes and final postconditions/commit remain atomic. No change to the 30-second or 120-second policies is part of this plan.

First prove value/type/order/alias/serializer equivalence and rejection of changed config, malformed storage, outside alias mutation, competing writes, revocation and cancellation for this **complete producer-to-consumer chain**. Count the actual retired mutable cohort volume and remaining scans, without summing overlapping graph sizes. Only then freeze bytes and perform the same two large real-clock Cold saves, first new-process reopen and actual writer-lock cancellation. There is no promised duration: the previously measured 5.346-second typed region and 12.7-second structural region are separate observations, not additive guaranteed savings for this one manifest.

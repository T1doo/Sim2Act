# Final frozen JS/API author review

Frozen commit: `805afe60cdd94d6d4679e0da9c1f7fde752f67d2`.

Qualification: this agent authored the UI patch. This is a read-only author recheck of the committed UI/API alignment, **not independent code review of that UI**. The separately recorded existing same-Goal old-column runtime test is an independent committed-snapshot execution.

No blocking mismatch found in this bounded static recheck:

- `csv-goal-revision.js` material mode reads `/csv-material-revisions/context` as `{context,materials}`. `csv_material_revisions.mount` returns that exact envelope. The material list stays out of `entry.ctx`; context checks instance, principal, project, app, runtime, current Release fingerprint/revision and data version before enabling review.
- Material preview POST uses only the existing Preview fields plus `expected_data_version`, `resource_id` and `source_hash`. `csv_material_revisions.Preview` declares those exact extra fields. The UI keeps both column controls equal to the adopted parent column; the backend independently requires the same equality and current authorized target bytes.
- Only the initial preview POST uses the material adapter path. Preview recovery, CHECK, version approval and adoption approval retain the original common journal routes and their existing strict contracts. Material response verification checks its namespace, exact context, material resource/hash/format/revision and both column fields.
- Separate CHECK/Release/adoption acknowledgments remain mandatory. Navigation restore reads current authorized context and exact original journal keys, then resets acknowledgments. `here()` and `current()` fence async continuations by account, workspace, instance and generation; unknown/accepted-read-error work recovers with GET and the original key.
- The back button permits only an unsubmitted/proven-rejected material cycle; it rejects unknown/sending/accepted-read-error and any accepted business preview/CHECK/approval/Release/adoption state. It records `abandoned`, preserves original key/context/ledger in audit history and performs local rendering only. It never claims adoption or replaces an unknown durable intent.
- `use.js` adds frozen-preview GET only for material v1 or a validated parent `material_revision` lineage. It checks the exact USE Reference, preview and effective fingerprints, immutable Goal/input/parent, parent Release, spec and instance revision and single effective CSV binding before showing actual B/hash with original Goal sources. The old v1/v2 A branch adds no GET and retains its display shape. The added await uses the existing current-generation fence.
- The material lineage's use-column options come from its frozen single-column definition rather than original A guidance, so the displayed action remains aligned with the effective approved binding.

Retained existing behavior: a context 403/409 clears private UI state; a user reopens/refreshes the authorized instance before returning from a failed unsubmitted material cycle. No permission-clearing boundary was weakened.

This static check does not claim browser runtime, real model, semantic/scenario validity, Windows, PostgreSQL, remote CI or deployment verification. The root agent separately runs the new HTTP/JSDOM material tests.

# Author source review — not independent acceptance

Reviewed the actual source diff against the writer handoff, plus the delivered DOM/controller checks and targeted HTTP regressions.

- No new endpoint, authority, model call, database setting, trusted-code execution or payload expansion is introduced. New read-only inspector/lookup content uses existing authenticated page/receipt state.
- Transient same-Run read errors preserve a clearly identified previously read answer; 401/403 clear it. Identity/project changes and pagehide clear transient private UI. Preference storage contains only bounded appearance values, never tokens, material or results.
- Table/Markdown rendering uses `textContent`/DOM creation, retains full source and does not interpret HTML, load assets or derive fake chart data. Original chart Run/Release checks and permission revocation behavior remain and pass the actual HTTP fixture.
- Shared inspector ownership follows exact current Run/instance generation. Its application observer removes stale content; historical draft viewing does not mutate the persisted version or dispatch a Run.
- Explicit Run commands carry the original version, suppress duplicate local gestures and do not retry uncertain mutations. Existing Source/Cold version, original-key, storage, consent and revocation assertions remain intact.
- Cosmetic changes use original node identities. There are no duplicate IDs in the exercised template; material commands and selection forms have different semantics.

Remaining review risks: broad CSS/layout changes have **no actual product pixel review** in this environment; real zoom/focus/overflow, disclosure height, WebView2 host behavior and performance require a working protected browser/native environment. The historical recovery implementation is deliberately an unsaved editor-draft operation, not a new persisted restoration API. The complete 42-point acceptance matrix remains open where identified in the coverage file.

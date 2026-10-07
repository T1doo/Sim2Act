# Two-case PG OFF→ON classification

Exact source `1c45795a06bc4f2e2d2210540520470582f64c72`; all 257 tracked src/tests/scripts/.github bytes verified against Git. The two original CSV nodes in collection.json ran once per mode: OFF 2 PASS / ON 2 PASS, zero failures/skips, natural exit 0. Opt-in metrics COMPLETE, pending SQL 0.

ON env fixture setup: 665.858 ms. Two Store.initialize calls: 224.882 ms (33.77% of env setup). Eighty has_table calls: 59.573 ms (26.49% of initialization). Eighty existence SQL cursor spans: 43.395 ms; eighty DDL spans: 115.889 ms. Method and cursor families overlap; do not sum them. Full fixed-label metrics and explicit denominators are in on-metrics.json / measurement-summary.json.

This is one Linux process-pair classification, not proof of stable plugin overhead, Windows savings, or budget readiness. It measures fresh PG initialization (40 tables per fixture), with existing checkfirst and every original assertion unchanged. No provider/LIVE/full/CI or optimization was run. A checkfirst-removal proposal remains unqualified and was not implemented.

The actual source-first child origins, collection, original per-mode JUnit and controller timings are preserved. Log/XML exports are marked sanitized; each controller records raw SHA before deletion plus sanitized SHA. In this run sanitization changed neither log nor XML bytes (hashes equal). Private URL and original private copies were removed after verification. Owned schemas, extra roles, public tables, controllers and labelled container are zero; exact temporary worktree and fixture directories removed (cleanup.json).

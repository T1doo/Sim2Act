# Independent read-only preflight

Reviewer /root/next_ui_slice_review gave a limited source ACK before launch. No remaining deterministic blocker identified after these corrections:

- Navigate through the real projects/apps controls before interacting with each directory.
- Await the exact material read-failure text, not the transient unconfirmed placeholder.
- Synthetic app metadata explicitly has csv_instance_candidate=false; no detail/instance lookup is needed.
- Bind the actual held request, require HTTP200 and requestfinished with no failure, then await two page frames before checking that B remains displayed. Original polling is not changed.

Original GET/POST, work/cleanup, sandbox/CSP gates remain. Product assets match c797. Reviewer performed no test, network call or window execution. Actual pixels and exit/cleanup remain pending. Empty task state/Map equality does not prove persisted UNKNOWN or actual authorization recovery.

# Explicit Mock wiring — classification closure review

2026-10-21. Independent read-only review. Result: **LIMITED_STATIC_CLOSURE_ACK_DEFAULT_OFF_NO_START_ACK**. No new P1/P2 found in this increment. Earlier `WIRING-CODE-REVIEW` is retained as an intermediate-hash review; its guard/test hashes are not the final closure hashes.

## Final exact SHA256

Current files were independently hashed and match `/tmp/sim2act-explicit-mock-wiring-20261021/closure-hashes.json`:

| File | SHA256 |
|---|---|
| `src/sim2act/natural_spec_runtime.py` | `eb6010151979b5c6e085559f45e4a4fb430db3790393d44162a8e3e4d924c459` |
| `scripts/diagnostics/g0_guard.py` | `812a01a06ebb2694d68d50c3a02fd08c8266772cf036a54b0e364e0f9bfe5812` |
| `scripts/diagnostics/g0_prefix.py` | `c67132016a0c782d148aeae8ca6ab2c164ba78182d984d46dde99682e116596b` |
| `tests/test_cold_accounted_mock_wiring.py` | `7e834a927f87e4036d985529e3e4ae0e7a90500b0e23b8bb0e574e5c90c83af2` |

Runtime/prefix bytes are unchanged from the previous static review. The target-only dispatch and original graph/candidate nesting conclusions therefore remain applicable. The selected path remains internal, explicitly configured, synthetic SQLite-only, absent from ordinary runtime and bounded-launcher calls, and does not supply account or production qualification.

## Classification P2 closure

In `g0_guard.py:460–474`, a DomainError from the selected target context now yields `classification=UNKNOWN` and `error_origin=UNDETERMINED_ORIGINAL_OR_CANDIDATE`. This covers both a candidate-specific `_Capacity` and a body/guard DomainError when causal origin cannot be established. The same error object is retained in the owned signal and as `raise ... from error`; it is not replaced by an inferred original business refusal.

`diagnostic()` uses `selected_context_error` and `selected_context_diagnostic` for that marked result. It does not emit top-level `original_error` or `original_diagnostic` for the selected rejection. The generic exception-chain serializer remains unchanged; an exception object's actual `_cold_admission_diagnostic`, when present, is still preserved in its existing chain-record field, without establishing the exception's origin. Missing diagnostic remains NOT_REACHED and is not fabricated.

With `_target_context is None`, rejection classification remains `G0_ORIGINAL_REJECTION_NO_W5`, no error_origin is added, and the prior original_error/original_diagnostic fields remain. Healthy completed-context classification and protection-denial / unhealthy Mock handling are unchanged. Unbound/non-target routing remains on original without config. UNKNOWN is outside the bounded launcher's accepted classifications (`g0_bounded.py:338`), so selected errors cannot become launcher success through this change. No new invocation or grant is added.

## Tests and evidence boundary

The target-routing test is now parameterized with ordinary DomainError and `_Capacity`, increasing this local file from 11 to 12 expanded cases. It checks UNKNOWN/error_origin, retained exception identity, selected_context_error and absence of original_error. The test still uses synthetic budget state, a local arm callback and context stand-ins; it does not perform a Mock exchange, production prefix or G0.

The author reports an earlier 192-pass batch before this classification increment. This report does not treat that batch as validation of the final hashes. The requested final 12 local cases and guard pure-unit results were pending at report time and have not been attested here. Reviewer executed no code, imports, tests, database access, Worker, Mock, G0, prefix, prepare or commit; only source/hash reads and /tmp report writes.

This is a frozen static classification/wiring closure ACK only. It is not a full-prepare/G0 integration, timing, deadline-success, production-permission or new-window ACK.

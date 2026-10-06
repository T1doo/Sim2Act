# Spec synthetic_release_boundaries v2

- [retain_history] MUST Keep prior instance records when creating a release.

- [preview_scope] MUST_NOT Send preview writes to a production target.
- [permission_check] MUST Check the current owner and runtime grants before each action.

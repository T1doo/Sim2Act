class DomainError(Exception):
    submission_rejection: dict | None = None
    # Private receive evidence exists only when an adapter captured it. Keep
    # these annotation-only: hasattr(_received_body) controls prefix capture.
    _received_body: bytes
    _received_body_complete: bool
    _received_response: object

    def __init__(self, code: str, message: str = "", *, retryable: bool = False):
        self.code = code
        self.message = message or code
        self.retryable = retryable
        super().__init__(self.message)

    def public(self):
        value = {
            "code": self.code,
            "message": self.message,
            "safe_retry": self.retryable,
            "effect_known": self.code != "OUTCOME_UNKNOWN",
            "user_action": "Check status, configuration and permissions",
        }

        if self.submission_rejection is not None:
            value["submission_rejection"] = self.submission_rejection
        return value

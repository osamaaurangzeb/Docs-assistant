"""Domain errors.

Services raise these; the HTTP layer (see `app/factory.py`) converts them to a
consistent JSON body: {"error": {"code": "...", "message": "..."}}.
Services therefore never import anything HTTP-related.
"""


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationFailed(AppError):
    status_code = 400
    code = "invalid_request"


class PayloadTooLarge(AppError):
    status_code = 413
    code = "payload_too_large"


class SessionNotFound(AppError):
    status_code = 404
    code = "session_not_found"


class ProviderRateLimited(AppError):
    status_code = 429
    code = "provider_rate_limited"


class ProviderUnavailable(AppError):
    status_code = 502
    code = "provider_error"

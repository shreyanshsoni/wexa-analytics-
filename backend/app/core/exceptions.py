class WexaError(Exception):
    def __init__(self, message: str, code: str) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class AuthenticationError(WexaError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthorizationError(WexaError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, code="AUTHORIZATION_ERROR")


class NotFoundError(WexaError):
    def __init__(self, resource: str, resource_id: str | int) -> None:
        super().__init__(
            message=f"{resource} with id '{resource_id}' not found",
            code="NOT_FOUND",
        )


class ConflictError(WexaError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="CONFLICT")


class ValidationError(WexaError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR")


class RateLimitError(WexaError):
    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED")


class ExternalServiceError(WexaError):
    def __init__(self, service: str, message: str) -> None:
        super().__init__(
            message=f"{service} error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
        )

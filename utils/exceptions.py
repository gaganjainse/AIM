"""Custom exception hierarchy for AIM application."""

class AIMException(Exception):
    def __init__(self, message, code="INTERNAL_ERROR", status_code=400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(AIMException):
    def __init__(self, message, field=None):
        self.field = field
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)

class AuthenticationError(AIMException):
    def __init__(self, message="Authentication failed"):
        super().__init__(message, code="AUTH_ERROR", status_code=401)

class AuthorizationError(AIMException):
    def __init__(self, message="Insufficient permissions"):
        super().__init__(message, code="FORBIDDEN", status_code=403)

class ResourceNotFoundError(AIMException):
    def __init__(self, message="Resource not found"):
        super().__init__(message, code="NOT_FOUND", status_code=404)

class DatabaseError(AIMException):
    def __init__(self, message="Database error"):
        super().__init__(message, code="DB_ERROR", status_code=500)

class RateLimitError(AIMException):
    def __init__(self, message="Rate limit exceeded"):
        super().__init__(message, code="RATE_LIMITED", status_code=429)

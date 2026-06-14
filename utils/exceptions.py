"""Custom exception hierarchy for AIM application."""
from typing import Any, Optional, Dict, List, Tuple, Union

class AIMException(Exception):
    def __init__(self, message, code="INTERNAL_ERROR", status_code=400) -> Any:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(AIMException):
    def __init__(self, message, field=None) -> Any:
        self.field = field
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)

class AuthenticationError(AIMException):
    def __init__(self, message="Authentication failed") -> Any:
        super().__init__(message, code="AUTH_ERROR", status_code=401)

class AuthorizationError(AIMException):
    def __init__(self, message="Insufficient permissions") -> Any:
        super().__init__(message, code="FORBIDDEN", status_code=403)

class ResourceNotFoundError(AIMException):
    def __init__(self, message="Resource not found") -> Any:
        super().__init__(message, code="NOT_FOUND", status_code=404)

class DatabaseError(AIMException):
    def __init__(self, message="Database error") -> Any:
        super().__init__(message, code="DB_ERROR", status_code=500)

class RateLimitError(AIMException):
    def __init__(self, message="Rate limit exceeded") -> Any:
        super().__init__(message, code="RATE_LIMITED", status_code=429)

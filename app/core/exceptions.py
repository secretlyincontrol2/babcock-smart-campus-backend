from typing import Any, Dict, Optional
from http import HTTPStatus

class CustomHTTPException(Exception):
    """Custom HTTP exception with additional error information (Flask-compatible)"""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_type: str = "general_error",
        extra_data: Optional[Dict[str, Any]] = None
    ):
        self.status_code = int(status_code)
        self.detail = detail
        self.error_type = error_type
        self.extra_data = extra_data or {}

class ValidationError(CustomHTTPException):
    """Validation error exception"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        extra_data = {}
        if field:
            extra_data["field"] = field
        if value is not None:
            extra_data["value"] = str(value)
        
        super().__init__(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=message,
            error_type="validation_error",
            extra_data=extra_data
        )

class DatabaseError(CustomHTTPException):
    """Database operation error exception"""
    def __init__(self, message: str, operation: str = None):
        extra_data = {}
        if operation:
            extra_data["operation"] = operation
        
        super().__init__(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=message,
            error_type="database_error",
            extra_data=extra_data
        )

class ResourceNotFoundError(CustomHTTPException):
    """Resource not found exception"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"{resource_type} with ID {resource_id} not found",
            error_type="resource_not_found",
            extra_data={"resource_type": resource_type, "resource_id": resource_id}
        )

class AuthorizationError(CustomHTTPException):
    """Authorization error exception"""
    def __init__(self, message: str = "Insufficient privileges"):
        super().__init__(
            status_code=HTTPStatus.FORBIDDEN,
            detail=message,
            error_type="authorization_error"
        )

class ConflictError(CustomHTTPException):
    """Conflict error exception"""
    def __init__(self, message: str, field: str = None):
        extra_data = {}
        if field:
            extra_data["field"] = field
        
        super().__init__(
            status_code=HTTPStatus.CONFLICT,
            detail=message,
            error_type="conflict_error",
            extra_data=extra_data
        )

class RateLimitError(CustomHTTPException):
    """Rate limit exceeded exception"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            detail=message,
            error_type="rate_limit_error"
        )

class ServiceUnavailableError(CustomHTTPException):
    """Service unavailable exception"""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=message,
            error_type="service_unavailable"
        )

class InvalidLocationError(CustomHTTPException):
    """Invalid location exception"""
    def __init__(self, message: str = "Invalid location data"):
        super().__init__(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=message,
            error_type="invalid_location"
        )

class FileUploadError(CustomHTTPException):
    """File upload error exception"""
    def __init__(self, message: str = "File upload failed"):
        super().__init__(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=message,
            error_type="file_upload_error"
        )

class ExternalServiceError(CustomHTTPException):
    """External service error exception"""
    def __init__(self, message: str = "External service error"):
        super().__init__(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=message,
            error_type="external_service_error"
        )

class QRCodeExpiredError(CustomHTTPException):
    """QR code expired exception"""
    def __init__(self, message: str = "QR code has expired"):
        super().__init__(
            status_code=HTTPStatus.GONE,
            detail=message,
            error_type="qr_code_expired"
        )

class DuplicateAttendanceError(CustomHTTPException):
    """Duplicate attendance exception"""
    def __init__(self, message: str = "Attendance already marked"):
        super().__init__(
            status_code=HTTPStatus.CONFLICT,
            detail=message,
            error_type="duplicate_attendance"
        )

# Utility functions for raising exceptions
def raise_validation_error(message: str, field: str = None, value: Any = None):
    """Raise a validation error"""
    raise ValidationError(message, field, value)

def raise_resource_not_found(resource_type: str, resource_id: str):
    """Raise a resource not found error"""
    raise ResourceNotFoundError(resource_type, resource_id)

def raise_authorization_error(message: str = "Insufficient privileges"):
    """Raise an authorization error"""
    raise AuthorizationError(message)

def raise_conflict_error(message: str, field: str = None):
    """Raise a conflict error"""
    raise ConflictError(message, field)

def raise_database_error(message: str, operation: str = None):
    """Raise a database error"""
    raise DatabaseError(message, operation)

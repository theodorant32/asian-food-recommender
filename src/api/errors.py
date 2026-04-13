"""
Custom error handlers and exception classes.

Provides consistent error responses across the API.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger


class APIError(HTTPException):
    """Base API error with consistent response format."""

    def __init__(
        self,
        status_code: int,
        message: str,
        detail: str | None = None,
        error_code: str | None = None,
    ):
        self.message = message
        self.detail = detail or message
        self.error_code = error_code or f"ERR_{status_code}"

        super().__init__(
            status_code=status_code,
            detail={
                "error": self.error_code,
                "message": self.message,
                "detail": self.detail,
            },
        )


class NotFoundError(APIError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"{resource} not found",
            detail=f"No {resource.lower()} with identifier '{identifier}' exists",
            error_code=f"NOT_FOUND_{resource.upper()}",
        )


class ValidationError(APIError):
    """Request validation failed."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Validation error",
            detail=f"{field}: {message}" if field else message,
            error_code="VALIDATION_ERROR",
        )


class ServiceUnavailableError(APIError):
    """Backend service unavailable."""

    def __init__(self, service: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Service unavailable",
            detail=f"{service} is not initialized or unavailable",
            error_code="SERVICE_UNAVAILABLE",
        )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Global handler for HTTP exceptions."""
    logger.error(
        f"HTTP Error: {exc.status_code} - {exc.detail} - Path: {request.url.path}"
    )

    # Format error response
    if isinstance(exc.detail, dict):
        detail = exc.detail
    else:
        detail = {"error": f"ERR_{exc.status_code}", "message": str(exc.detail)}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            **detail,
            "path": request.url.path,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global handler for unhandled exceptions."""
    logger.exception(f"Unhandled error: {exc} - Path: {request.url.path}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "path": request.url.path,
        },
    )

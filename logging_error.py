#!/usr/bin/env python3
"""
Comprehensive Error Handler & Exception Manager
Enhanced error handling with user-friendly messages and detailed logging
"""

import sys
import traceback
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Union
from functools import wraps
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError as PydanticValidationError
import json

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """Standardized error response model"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None
    user_message: Optional[str] = None


class PlatformException(Exception):
    """Base exception for platform-specific errors"""

    def __init__(self,
                 message: str,
                 error_code: str = None,
                 status_code: int = 500,
                 user_message: str = None,
                 details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        self.user_message = user_message or self._get_user_friendly_message()
        self.details = details or {}
        super().__init__(message)

    def _get_user_friendly_message(self) -> str:
        """Get user-friendly error message"""
        return "An error occurred. Please try again or contact support if the issue persists."


class ValidationException(PlatformException):
    """Data validation errors"""

    def __init__(self, message: str, field: str = None, **kwargs):
        self.field = field
        super().__init__(message, status_code=400, **kwargs)

    def _get_user_friendly_message(self) -> str:
        return "Please check your input and try again."


class AuthenticationException(PlatformException):
    """Authentication related errors"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, status_code=401, **kwargs)

    def _get_user_friendly_message(self) -> str:
        return "Please check your credentials and try again."


class AuthorizationException(PlatformException):
    """Authorization/permission errors"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, status_code=403, **kwargs)

    def _get_user_friendly_message(self) -> str:
        return "You don't have permission to access this resource."


class ResourceNotFoundException(PlatformException):
    """Resource not found errors"""

    def __init__(self, resource: str = "Resource", **kwargs):
        message = f"{resource} not found"
        super().__init__(message, status_code=404, **kwargs)

    def _get_user_friendly_message(self) -> str:
        return "The requested information could not be found."


class ExternalServiceException(PlatformException):
    """External service/API errors"""

    def __init__(self, service: str, message: str = None, **kwargs):
        self.service = service
        message = message or f"{service} service unavailable"
        super().__init__(message, status_code=503, **kwargs)

    def _get_user_friendly_message(self) -> str:
        return "An external service is temporarily unavailable. Please try again later."


class RateLimitException(PlatformException):
    """Rate limiting errors"""

    def __init__(self,
                 limit: int = None,
                 reset_time: datetime = None,
                 **kwargs):
        self.limit = limit
        self.reset_time = reset_time
        message = f"Rate limit exceeded"
        if limit:
            message += f" ({limit} requests)"
        super().__init__(message, status_code=429, **kwargs)

    def _get_user_friendly_message(self) -> str:
        if self.reset_time:
            return f"Too many requests. Please try again after {self.reset_time.strftime('%H:%M:%S')}."
        return "Too many requests. Please try again in a few minutes."


class DatabaseException(PlatformException):
    """Database related errors"""

    def __init__(self, operation: str = "database operation", **kwargs):
        message = f"Database error during {operation}"
        super().__init__(message, status_code=500, **kwargs)

    def _get_user_friendly_message(self) -> str:
        return "A temporary database issue occurred. Please try again."


class GST_APIException(ExternalServiceException):
    """GST API specific errors"""

    def __init__(self, gstin: str = None, **kwargs):
        self.gstin = gstin
        super().__init__("GST API", **kwargs)

    def _get_user_friendly_message(self) -> str:
        if self.gstin:
            return f"Unable to fetch GST information for {self.gstin}. Please verify the GSTIN and try again."
        return "GST service is temporarily unavailable. Please try again later."


class LoanServiceException(PlatformException):
    """Loan service specific errors"""

    def __init__(self, loan_operation: str = "loan operation", **kwargs):
        self.loan_operation = loan_operation
        super().__init__(f"Loan service error during {loan_operation}",
                         **kwargs)

    def _get_user_friendly_message(self) -> str:
        return "Loan service is temporarily unavailable. Please try again later."


class EnhancedErrorHandler:
    """Comprehensive error handling system"""

    def __init__(self, templates: Jinja2Templates = None, debug: bool = False):
        self.templates = templates
        self.debug = debug
        self.error_counts = {}
        self.error_handlers = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default error handlers for common exceptions"""

        self.error_handlers.update({
            ValidationException: self._handle_validation_error,
            AuthenticationException: self._handle_auth_error,
            AuthorizationException: self._handle_auth_error,
            ResourceNotFoundException: self._handle_not_found_error,
            ExternalServiceException: self._handle_service_error,
            RateLimitException: self._handle_rate_limit_error,
            DatabaseException: self._handle_database_error,
            GST_APIException: self._handle_gst_api_error,
            LoanServiceException: self._handle_loan_service_error,
            HTTPException: self._handle_http_exception,
            PydanticValidationError: self._handle_pydantic_validation_error,
            ValueError: self._handle_value_error,
            KeyError: self._handle_key_error,
            ConnectionError: self._handle_connection_error,
            TimeoutError: self._handle_timeout_error,
            Exception: self._handle_generic_exception
        })

    def register_handler(self, exception_type: type, handler: Callable):
        """Register custom error handler"""
        self.error_handlers[exception_type] = handler

    async def handle_error(
            self, request: Request,
            exc: Exception) -> Union[JSONResponse, HTMLResponse]:
        """Main error handling method"""

        # Log the error
        await self._log_error(request, exc)

        # Track error frequency
        self._track_error(exc)

        # Find appropriate handler
        handler = self._find_handler(type(exc))

        # Call handler
        if handler:
            return await handler(request, exc)
        else:
            return await self._handle_generic_exception(request, exc)

    def _find_handler(self, exc_type: type) -> Optional[Callable]:
        """Find appropriate error handler"""
        # Try exact match first
        if exc_type in self.error_handlers:
            return self.error_handlers[exc_type]

        # Try parent classes
        for registered_type, handler in self.error_handlers.items():
            if issubclass(exc_type, registered_type):
                return handler

        return None

    async def _log_error(self, request: Request, exc: Exception):
        """Log error with context"""
        try:
            error_context = {
                "url":
                str(request.url),
                "method":
                request.method,
                "headers":
                dict(request.headers),
                "client":
                getattr(request.client, 'host', 'unknown')
                if request.client else 'unknown'
            }

            # Get user info if available
            user_mobile = getattr(request.state, 'user_mobile', None)
            if user_mobile:
                error_context["user_mobile"] = user_mobile

            # Log to application logger
            logger.error(
                f"Error in {request.method} {request.url.path}: {str(exc)}",
                extra={
                    "exception_type": type(exc).__name__,
                    "request_context": error_context,
                    "stack_trace": traceback.format_exc()
                })

            # Log to database if database manager is available
            try:
                from database import get_database
                db = await get_database()
                await db.log_error(error_type=type(exc).__name__,
                                   message=str(exc),
                                   stack_trace=traceback.format_exc(),
                                   user_mobile=user_mobile,
                                   additional_data=error_context)
            except Exception as db_error:
                logger.error(f"Failed to log error to database: {db_error}")

        except Exception as log_error:
            logger.error(f"Failed to log error: {log_error}")

    def _track_error(self, exc: Exception):
        """Track error frequency for monitoring"""
        error_type = type(exc).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type,
                                                              0) + 1

    def _create_error_response(self,
                               exc: Exception,
                               request: Request,
                               status_code: int = 500) -> ErrorResponse:
        """Create standardized error response"""

        # Get request ID if available
        request_id = getattr(request.state, 'request_id', None)

        if isinstance(exc, PlatformException):
            return ErrorResponse(error=exc.message,
                                 error_code=exc.error_code,
                                 user_message=exc.user_message,
                                 details=exc.details,
                                 timestamp=datetime.now(),
                                 request_id=request_id)
        else:
            # Generic error
            user_message = "An unexpected error occurred. Please try again."
            if self.debug:
                user_message = str(exc)

            return ErrorResponse(error=str(exc),
                                 error_code=type(exc).__name__,
                                 user_message=user_message,
                                 timestamp=datetime.now(),
                                 request_id=request_id)

    def _is_api_request(self, request: Request) -> bool:
        """Check if request is for API endpoint"""
        return (request.url.path.startswith("/api/")
                or "application/json" in request.headers.get("accept", "")
                or "XMLHttpRequest" in request.headers.get(
                    "X-Requested-With", ""))

    # Specific error handlers
    async def _handle_validation_error(
            self, request: Request, exc: ValidationException) -> JSONResponse:
        """Handle validation errors"""
        error_response = self._create_error_response(exc, request,
                                                     exc.status_code)
        if hasattr(exc, 'field') and exc.field:
            error_response.field = exc.field

        return JSONResponse(status_code=exc.status_code,
                            content=error_response.dict())

    async def _handle_auth_error(
            self, request: Request,
            exc: PlatformException) -> Union[JSONResponse, HTMLResponse]:
        """Handle authentication/authorization errors"""
        if self._is_api_request(request):
            error_response = self._create_error_response(
                exc, request, exc.status_code)
            return JSONResponse(status_code=exc.status_code,
                                content=error_response.dict())
        else:
            # Redirect to login page
            return HTMLResponse(content=f"""
                <script>
                    window.notificationManager?.show('{exc.user_message}', 'error');
                    setTimeout(() => window.location.href = '/login', 2000);
                </script>
                """,
                                status_code=exc.status_code)

    async def _handle_not_found_error(
            self, request: Request, exc: ResourceNotFoundException
    ) -> Union[JSONResponse, HTMLResponse]:
        """Handle 404 errors"""
        if self._is_api_request(request):
            error_response = self._create_error_response(exc, request, 404)
            return JSONResponse(status_code=404, content=error_response.dict())
        else:
            # Return 404 page
            if self.templates:
                try:
                    return self.templates.TemplateResponse(
                        "errors/404.html", {
                            "request": request,
                            "error": exc.user_message
                        },
                        status_code=404)
                except:
                    pass

            # Fallback 404 page
            return HTMLResponse(content=self._create_error_html(
                "404 - Not Found", exc.user_message),
                                status_code=404)

    async def _handle_service_error(
            self, request: Request,
            exc: ExternalServiceException) -> JSONResponse:
        """Handle external service errors"""
        error_response = self._create_error_response(exc, request,
                                                     exc.status_code)
        error_response.details = {"service": exc.service}

        return JSONResponse(status_code=exc.status_code,
                            content=error_response.dict())

    async def _handle_rate_limit_error(
            self, request: Request, exc: RateLimitException) -> JSONResponse:
        """Handle rate limiting errors"""
        error_response = self._create_error_response(exc, request, 429)

        headers = {"Retry-After": "60"}
        if exc.reset_time:
            retry_after = max(
                1, int((exc.reset_time - datetime.now()).total_seconds()))
            headers["Retry-After"] = str(retry_after)

        return JSONResponse(status_code=429,
                            content=error_response.dict(),
                            headers=headers)

    async def _handle_database_error(self, request: Request,
                                     exc: DatabaseException) -> JSONResponse:
        """Handle database errors"""
        error_response = self._create_error_response(exc, request, 500)

        return JSONResponse(status_code=500, content=error_response.dict())

    async def _handle_gst_api_error(self, request: Request,
                                    exc: GST_APIException) -> JSONResponse:
        """Handle GST API specific errors"""
        error_response = self._create_error_response(exc, request,
                                                     exc.status_code)
        if exc.gstin:
            error_response.details = {"gstin": exc.gstin}

        return JSONResponse(status_code=exc.status_code,
                            content=error_response.dict())

    async def _handle_loan_service_error(
            self, request: Request, exc: LoanServiceException) -> JSONResponse:
        """Handle loan service errors"""
        error_response = self._create_error_response(exc, request,
                                                     exc.status_code)
        error_response.details = {"operation": exc.loan_operation}

        return JSONResponse(status_code=exc.status_code,
                            content=error_response.dict())

    async def _handle_http_exception(self, request: Request,
                                     exc: HTTPException) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        error_response = ErrorResponse(
            error=exc.detail,
            error_code="HTTP_EXCEPTION",
            user_message=exc.detail
            if exc.status_code < 500 else "An error occurred",
            timestamp=datetime.now(),
            request_id=getattr(request.state, 'request_id', None))

        return JSONResponse(status_code=exc.status_code,
                            content=error_response.dict())

    async def _handle_pydantic_validation_error(
            self, request: Request,
            exc: PydanticValidationError) -> JSONResponse:
        """Handle Pydantic validation errors"""
        errors = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors[field] = error["msg"]

        error_response = ErrorResponse(
            error="Validation failed",
            error_code="VALIDATION_ERROR",
            user_message="Please check your input and try again",
            details={"validation_errors": errors},
            timestamp=datetime.now(),
            request_id=getattr(request.state, 'request_id', None))

        return JSONResponse(status_code=422, content=error_response.dict())

    async def _handle_value_error(self, request: Request,
                                  exc: ValueError) -> JSONResponse:
        """Handle value errors"""
        error_response = self._create_error_response(exc, request, 400)
        error_response.user_message = "Invalid input provided"

        return JSONResponse(status_code=400, content=error_response.dict())

    async def _handle_key_error(self, request: Request,
                                exc: KeyError) -> JSONResponse:
        """Handle key errors"""
        error_response = self._create_error_response(exc, request, 400)
        error_response.user_message = "Required field missing"
        error_response.field = str(exc).strip("'\"")

        return JSONResponse(status_code=400, content=error_response.dict())

    async def _handle_connection_error(self, request: Request,
                                       exc: ConnectionError) -> JSONResponse:
        """Handle connection errors"""
        error_response = self._create_error_response(exc, request, 503)
        error_response.user_message = "Service temporarily unavailable"

        return JSONResponse(status_code=503, content=error_response.dict())

    async def _handle_timeout_error(self, request: Request,
                                    exc: TimeoutError) -> JSONResponse:
        """Handle timeout errors"""
        error_response = self._create_error_response(exc, request, 408)
        error_response.user_message = "Request timed out. Please try again."

        return JSONResponse(status_code=408, content=error_response.dict())

    async def _handle_generic_exception(self, request: Request,
                                        exc: Exception) -> JSONResponse:
        """Handle all other exceptions"""
        error_response = self._create_error_response(exc, request, 500)

        # Don't expose internal details in production
        if not self.debug:
            error_response.error = "Internal server error"
            error_response.user_message = "An unexpected error occurred. Please try again."

        return JSONResponse(status_code=500, content=error_response.dict())

    def _create_error_html(self, title: str, message: str) -> str:
        """Create simple HTML error page"""
        return f"""
        <!DOCTYPE html>
        <html lang="en" data-theme="dark">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - GST Intelligence Platform</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                    color: #f8fafc;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 2rem;
                }}
                .error-container {{
                    text-align: center;
                    max-width: 500px;
                    background: rgba(30, 41, 59, 0.8);
                    padding: 3rem 2rem;
                    border-radius: 16px;
                    border: 1px solid #334155;
                }}
                h1 {{ color: #ef4444; margin-bottom: 1rem; }}
                p {{ color: #cbd5e1; margin-bottom: 2rem; line-height: 1.6; }}
                .btn {{
                    background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
                    color: white;
                    border: none;
                    padding: 0.75rem 2rem;
                    border-radius: 8px;
                    text-decoration: none;
                    display: inline-block;
                    font-weight: 600;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>{title}</h1>
                <p>{message}</p>
                <a href="/" class="btn">Go Home</a>
            </div>
        </body>
        </html>
        """

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return self.error_counts.copy()


# Decorator for automatic error handling
def handle_errors(error_handler: EnhancedErrorHandler):
    """Decorator to automatically handle errors in route functions"""

    def decorator(func):

        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                return await func(request, *args, **kwargs)
            except Exception as e:
                return await error_handler.handle_error(request, e)

        return wrapper

    return decorator


# Global error handler instance
error_handler = None


def get_error_handler(templates: Jinja2Templates = None,
                      debug: bool = False) -> EnhancedErrorHandler:
    """Get global error handler instance"""
    global error_handler
    if error_handler is None:
        error_handler = EnhancedErrorHandler(templates, debug)
    return error_handler


# Example usage
if __name__ == "__main__":
    # Test error handling
    from fastapi import FastAPI, Request
    from fastapi.templating import Jinja2Templates

    app = FastAPI()
    templates = Jinja2Templates(directory="templates")
    error_handler = EnhancedErrorHandler(templates, debug=True)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return await error_handler.handle_error(request, exc)

    @app.get("/test-error")
    async def test_error():
        raise ValidationException("Test validation error", field="test_field")

    @app.get("/test-gst-error")
    async def test_gst_error():
        raise GST_APIException(gstin="29AAAPL2356Q1ZS")

    print("✅ Error handler configured successfully")

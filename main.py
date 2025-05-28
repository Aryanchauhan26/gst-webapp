from fastapi import FastAPI, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import requests
import json
from datetime import datetime, date
import pandas as pd
from io import BytesIO
import urllib.parse
import calendar
import logging
import sys
import time
import traceback
from typing import Dict, List, Optional, Any
from functools import wraps
import asyncio
from collections import defaultdict, deque
import hashlib
import os
from pathlib import Path

# Enhanced logging configuration
def setup_logging():
    """Configure comprehensive logging"""
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # File handler for general logs
    file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)
    
    # API calls logger
    api_logger = logging.getLogger('api_calls')
    api_handler = logging.FileHandler('logs/api_calls.log', encoding='utf-8')
    api_handler.setFormatter(log_format)
    api_logger.addHandler(api_handler)
    
    return root_logger

# Initialize logging
logger = setup_logging()

# Error tracking and monitoring
class ErrorTracker:
    """Track and monitor application errors"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=100)
        self.start_time = time.time()
        
    def log_error(self, error_type: str, error_message: str, additional_info: Dict = None):
        """Log and track errors"""
        self.error_counts[error_type] += 1
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_message,
            'additional_info': additional_info or {}
        }
        self.recent_errors.append(error_entry)
        logger.error(f"Error tracked: {error_type} - {error_message}", extra=additional_info or {})
    
    def get_error_stats(self):
        """Get error statistics"""
        uptime = time.time() - self.start_time
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_types': dict(self.error_counts),
            'recent_errors': list(self.recent_errors)[-10:],  # Last 10 errors
            'uptime_hours': round(uptime / 3600, 2)
        }

# Performance monitoring
class PerformanceMonitor:
    """Monitor application performance metrics"""
    
    def __init__(self):
        self.request_times = deque(maxlen=1000)
        self.request_counts = defaultdict(int)
        self.slow_requests = deque(maxlen=50)
        
    def log_request(self, endpoint: str, duration: float, status_code: int):
        """Log request performance"""
        self.request_times.append(duration)
        self.request_counts[endpoint] += 1
        
        # Track slow requests (>5 seconds)
        if duration > 5.0:
            self.slow_requests.append({
                'endpoint': endpoint,
                'duration': duration,
                'status_code': status_code,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_performance_stats(self):
        """Get performance statistics"""
        if not self.request_times:
            return {'message': 'No requests yet'}
            
        return {
            'total_requests': len(self.request_times),
            'avg_response_time': round(sum(self.request_times) / len(self.request_times), 3),
            'max_response_time': max(self.request_times),
            'min_response_time': min(self.request_times),
            'slow_requests_count': len(self.slow_requests),
            'endpoint_counts': dict(self.request_counts),
            'recent_slow_requests': list(self.slow_requests)[-5:]
        }

# Rate limiting
class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self):
        self.request_history = defaultdict(lambda: deque(maxlen=100))
        self.blocked_ips = {}
        
    def is_rate_limited(self, identifier: str, max_requests: int = 10, window_seconds: int = 60) -> tuple[bool, Dict]:
        """Check if request should be rate limited"""
        current_time = time.time()
        requests = self.request_history[identifier]
        
        # Clean old requests
        while requests and current_time - requests[0] > window_seconds:
            requests.popleft()
        
        # Check if blocked
        if identifier in self.blocked_ips:
            if current_time - self.blocked_ips[identifier] < 300:  # 5 min block
                return True, {"reason": "IP temporarily blocked", "retry_after": 300}
            else:
                del self.blocked_ips[identifier]
        
        # Check rate limit
        if len(requests) >= max_requests:
            self.blocked_ips[identifier] = current_time
            return True, {"reason": "Rate limit exceeded", "retry_after": window_seconds}
        
        # Add current request
        requests.append(current_time)
        return False, {"requests_remaining": max_requests - len(requests)}

# Initialize monitoring
error_tracker = ErrorTracker()
performance_monitor = PerformanceMonitor()
rate_limiter = RateLimiter()

# Custom exception classes
class GSTPlatformError(Exception):
    """Base exception for GST platform errors"""
    pass

class GSTINValidationError(GSTPlatformError):
    """GSTIN validation error"""
    pass

class APIConnectionError(GSTPlatformError):
    """API connection error"""
    pass

class DataProcessingError(GSTPlatformError):
    """Data processing error"""
    pass

class ReportGenerationError(GSTPlatformError):
    """Report generation error"""
    pass

# Enhanced GSTIN validation
def validate_gstin(gstin: str) -> tuple[bool, str]:
    """Enhanced GSTIN validation with detailed error messages"""
    try:
        if not gstin:
            return False, "GSTIN cannot be empty"
        
        gstin = gstin.strip().upper()
        
        if len(gstin) != 15:
            return False, f"GSTIN must be 15 characters long, got {len(gstin)}"
        
        # Detailed format validation
        import re
        if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$', gstin):
            return False, "Invalid GSTIN format. Format should be: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric"
        
        # State code validation (basic check)
        state_code = int(gstin[:2])
        if state_code < 1 or state_code > 37:
            return False, f"Invalid state code: {state_code}"
        
        return True, "Valid GSTIN"
        
    except Exception as e:
        error_tracker.log_error("GSTIN_VALIDATION", str(e), {"gstin": gstin})
        return False, f"GSTIN validation error: {str(e)}"

# Enhanced API client with retry logic
class GSAPIClient:
    """Enhanced GST API client with retry logic and error handling"""
    
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.session = requests.Session()
        self.session.headers.update({
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
            "User-Agent": "GST-Compliance-Platform/1.0"
        })
        
    async def fetch_gstin_data(self, gstin: str, max_retries: int = 3) -> Dict:
        """Fetch GSTIN data with retry logic"""
        url = f"https://{self.host}/free/gstin/{gstin}"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching GST data for {gstin}, attempt {attempt + 1}")
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                if not data.get("success", False):
                    raise APIConnectionError(f"API returned unsuccessful response: {data.get('message', 'Unknown error')}")
                
                logger.info(f"Successfully fetched GST data for {gstin}")
                return data.get("data", {})
                
            except requests.exceptions.Timeout:
                error_msg = f"API timeout on attempt {attempt + 1}"
                error_tracker.log_error("API_TIMEOUT", error_msg, {"gstin": gstin, "attempt": attempt + 1})
                if attempt == max_retries - 1:
                    raise APIConnectionError(f"API timeout after {max_retries} attempts")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.ConnectionError:
                error_msg = f"API connection error on attempt {attempt + 1}"
                error_tracker.log_error("API_CONNECTION", error_msg, {"gstin": gstin, "attempt": attempt + 1})
                if attempt == max_retries - 1:
                    raise APIConnectionError(f"Unable to connect to API after {max_retries} attempts")
                await asyncio.sleep(2 ** attempt)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    error_tracker.log_error("API_RATE_LIMIT", "API rate limit exceeded", {"gstin": gstin})
                    raise APIConnectionError("API rate limit exceeded. Please try again later.")
                elif e.response.status_code in [500, 502, 503, 504]:  # Server errors
                    error_msg = f"API server error: {e.response.status_code}"
                    error_tracker.log_error("API_SERVER_ERROR", error_msg, {"gstin": gstin, "status_code": e.response.status_code})
                    if attempt == max_retries - 1:
                        raise APIConnectionError(f"API server error: {e.response.status_code}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise APIConnectionError(f"API HTTP error: {e.response.status_code}")
                    
            except Exception as e:
                error_msg = f"Unexpected API error: {str(e)}"
                error_tracker.log_error("API_UNEXPECTED", error_msg, {"gstin": gstin})
                if attempt == max_retries - 1:
                    raise APIConnectionError(f"Unexpected API error: {str(e)}")
                await asyncio.sleep(2 ** attempt)

# Try to import ReportLab with fallback
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
    logger.info("ReportLab is available for PDF generation")
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available - PDF generation will be limited")

# Initialize FastAPI app with enhanced configuration
app = FastAPI(
    title="GST Compliance Platform",
    description="Advanced GST compliance monitoring and reporting platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize API client
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "08cbf9855dmsh5c8d8660645305cp1a8713jsn17eca3b207a5")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST)

# Performance monitoring middleware
@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """Monitor request performance and add security headers"""
    start_time = time.time()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limiting check
    is_limited, limit_info = rate_limiter.is_rate_limited(client_ip)
    if is_limited:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "details": limit_info}
        )
    
    try:
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log performance
        performance_monitor.log_request(
            endpoint=str(request.url.path),
            duration=process_time,
            status_code=response.status_code
        )
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log request
        logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        error_tracker.log_error("REQUEST_PROCESSING", str(e), {
            "method": request.method,
            "path": str(request.url.path),
            "client_ip": client_ip,
            "process_time": process_time
        })
        
        logger.error(f"Request processing error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "message": "An unexpected error occurred"}
        )

# Enhanced error handler
@app.exception_handler(GSTPlatformError)
async def gst_platform_error_handler(request: Request, exc: GSTPlatformError):
    """Handle GST platform specific errors"""
    error_tracker.log_error(type(exc).__name__, str(exc), {
        "path": str(request.url.path),
        "method": request.method
    })
    
    return JSONResponse(
        status_code=400,
        content={"error": type(exc).__name__, "message": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    error_id = hashlib.md5(f"{time.time()}{str(exc)}".encode()).hexdigest()[:8]
    
    error_tracker.log_error("UNEXPECTED_ERROR", str(exc), {
        "path": str(request.url.path),
        "method": request.method,
        "error_id": error_id,
        "traceback": traceback.format_exc()
    })
    
    logger.error(f"Unexpected error (ID: {error_id}): {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "error_id": error_id
        }
    )

# Health check and monitoring endpoints
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    try:
        # Check API connectivity
        test_response = api_client.session.get(f"https://{RAPIDAPI_HOST}", timeout=5)
        api_healthy = test_response.status_code < 500
    except:
        api_healthy = False
    
    return {
        "status": "healthy" if api_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "api_connectivity": api_healthy,
        "reportlab_available": REPORTLAB_AVAILABLE,
        "uptime_hours": round((time.time() - error_tracker.start_time) / 3600, 2)
    }

@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    return {
        "timestamp": datetime.now().isoformat(),
        "errors": error_tracker.get_error_stats(),
        "performance": performance_monitor.get_performance_stats(),
        "system": {
            "reportlab_available": REPORTLAB_AVAILABLE,
            "python_version": sys.version,
            "platform": sys.platform
        }
    }

# Your existing route handlers would go here with enhanced error handling
# I'll show a few examples:

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Enhanced index page with error handling"""
    try:
        return templates.TemplateResponse("index.html", {"request": request, "data": None})
    except Exception as e:
        error_tracker.log_error("TEMPLATE_RENDER", str(e), {"template": "index.html"})
        raise HTTPException(status_code=500, detail="Error loading page")

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request, gstin: str = Form(...)):
    """Enhanced GST data fetching with comprehensive error handling"""
    try:
        # Validate GSTIN
        is_valid, validation_message = validate_gstin(gstin)
        if not is_valid:
            raise GSTINValidationError(validation_message)
        
        gstin = gstin.strip().upper()
        
        # Fetch data with enhanced error handling
        data = await api_client.fetch_gstin_data(gstin)
        
        # Process data (your existing logic here)
        # compliance = calculate_enhanced_compliance_score(data)
        # returns_by_year = organize_returns_by_year(data.get('returns', []))
        
        logger.info(f"Successfully processed GST data for {gstin}")
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": data,
            "gstin": gstin
        })
        
    except GSTINValidationError as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": str(e),
            "error_type": "validation"
        })
        
    except APIConnectionError as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": str(e),
            "error_type": "api"
        })
        
    except Exception as e:
        error_tracker.log_error("DATA_PROCESSING", str(e), {"gstin": gstin})
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": "An unexpected error occurred while processing your request. Please try again.",
            "error_type": "processing"
        })

# Add all your other existing functions here (calculate_enhanced_compliance_score, etc.)
# They would be enhanced with similar error handling patterns

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting GST Compliance Platform...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )

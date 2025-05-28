from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import httpx
from datetime import datetime
import pandas as pd
from io import BytesIO
import calendar
import logging
import sys
import time
import traceback
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
import hashlib
import os
from pathlib import Path
import re

# Logging setup
def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    try:
        file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)
        error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(log_format)
        root_logger.addHandler(error_handler)
    except Exception as e:
        print(f"Warning: Could not create log files: {e}")
    return root_logger

logger = setup_logging()

class ErrorTracker:
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=100)
        self.start_time = time.time()
    def log_error(self, error_type: str, error_message: str, additional_info: Dict = None):
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
        uptime = time.time() - self.start_time
        return {
            'total_errors': sum(self.error_counts.values()),
            'error_types': dict(self.error_counts),
            'recent_errors': list(self.recent_errors)[-10:],
            'uptime_hours': round(uptime / 3600, 2)
        }

class PerformanceMonitor:
    def __init__(self):
        self.request_times = deque(maxlen=1000)
        self.request_counts = defaultdict(int)
        self.slow_requests = deque(maxlen=50)
    def log_request(self, endpoint: str, duration: float, status_code: int):
        self.request_times.append(duration)
        self.request_counts[endpoint] += 1
        if duration > 5.0:
            self.slow_requests.append({
                'endpoint': endpoint,
                'duration': duration,
                'status_code': status_code,
                'timestamp': datetime.now().isoformat()
            })
    def get_performance_stats(self):
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

class RateLimiter:
    def __init__(self):
        self.request_history = defaultdict(lambda: deque(maxlen=100))
        self.blocked_ips = {}
    def is_rate_limited(self, identifier: str, max_requests: int = 10, window_seconds: int = 60) -> Tuple[bool, Dict]:
        current_time = time.time()
        requests = self.request_history[identifier]
        while requests and current_time - requests[0] > window_seconds:
            requests.popleft()
        if identifier in self.blocked_ips:
            if current_time - self.blocked_ips[identifier] < 300:
                return True, {"reason": "IP temporarily blocked", "retry_after": 300}
            else:
                del self.blocked_ips[identifier]
        if len(requests) >= max_requests:
            self.blocked_ips[identifier] = current_time
            return True, {"reason": "Rate limit exceeded", "retry_after": window_seconds}
        requests.append(current_time)
        return False, {"requests_remaining": max_requests - len(requests)}

error_tracker = ErrorTracker()
performance_monitor = PerformanceMonitor()
rate_limiter = RateLimiter()

class GSTPlatformError(Exception): pass
class GSTINValidationError(GSTPlatformError): pass
class APIConnectionError(GSTPlatformError): pass
class DataProcessingError(GSTPlatformError): pass
class ReportGenerationError(GSTPlatformError): pass

def validate_gstin(gstin: str) -> Tuple[bool, str]:
    try:
        if not gstin:
            return False, "GSTIN cannot be empty"
        gstin = gstin.strip().upper()
        if len(gstin) != 15:
            return False, f"GSTIN must be 15 characters long, got {len(gstin)}"
        if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$', gstin):
            return False, "Invalid GSTIN format. Format should be: 2 digits + 5 letters + 4 digits + 1 letter + 1 alphanumeric + Z + 1 alphanumeric"
        state_code = int(gstin[:2])
        if state_code < 1 or state_code > 37:
            return False, f"Invalid state code: {state_code}"
        return True, "Valid GSTIN"
    except Exception as e:
        error_tracker.log_error("GSTIN_VALIDATION", str(e), {"gstin": gstin})
        return False, f"GSTIN validation error: {str(e)}"

class GSAPIClient:
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
            "User-Agent": "GST-Compliance-Platform/2.0"
        }
    async def fetch_gstin_data(self, gstin: str, max_retries: int = 3) -> Dict:
        url = f"https://{self.host}/free/gstin/{gstin}"
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching GST data for {gstin}, attempt {attempt + 1}")
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                if not data.get("success", False):
                    raise APIConnectionError(f"API returned unsuccessful response: {data.get('message', 'Unknown error')}")
                logger.info(f"Successfully fetched GST data for {gstin}")
                return data.get("data", {})
            except httpx.TimeoutException:
                error_msg = f"API timeout on attempt {attempt + 1}"
                error_tracker.log_error("API_TIMEOUT", error_msg, {"gstin": gstin, "attempt": attempt + 1})
                if attempt == max_retries - 1:
                    raise APIConnectionError(f"API timeout after {max_retries} attempts")
                await asyncio.sleep(2 ** attempt)
            except httpx.RequestError as e:
                error_msg = f"API connection error on attempt {attempt + 1}: {str(e)}"
                error_tracker.log_error("API_CONNECTION", error_msg, {"gstin": gstin, "attempt": attempt + 1})
                if attempt == max_retries - 1:
                    raise APIConnectionError(f"Unable to connect to API after {max_retries} attempts")
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    error_tracker.log_error("API_RATE_LIMIT", "API rate limit exceeded", {"gstin": gstin})
                    raise APIConnectionError("API rate limit exceeded. Please try again later.")
                elif e.response.status_code in [500, 502, 503, 504]:
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

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
    logger.info("ReportLab is available for PDF generation")
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available - PDF generation will be limited")

def calculate_enhanced_compliance_score(data: Dict) -> Dict:
    try:
        returns = data.get('filedreturns', [])
        if not returns:
            return {
                'score': 0,
                'grade': 'N/A',
                'status': 'No Returns Found',
                'total_returns': 0,
                'filed_returns': 0,
                'pending_returns': 0,
                'details': 'No return filing history available'
            }
        filed_count = sum(1 for ret in returns if ret.get('dof'))
        total_count = len(returns)
        score = round((filed_count / total_count) * 100, 1) if total_count else 0
        if score >= 95:
            grade = 'A+'
        elif score >= 85:
            grade = 'A'
        elif score >= 75:
            grade = 'B'
        elif score >= 60:
            grade = 'C'
        else:
            grade = 'D'
        if score >= 90:
            status = 'Excellent Compliance'
        elif score >= 75:
            status = 'Good Compliance'
        elif score >= 60:
            status = 'Fair Compliance'
        else:
            status = 'Poor Compliance'
        return {
            'score': score,
            'grade': grade,
            'status': status,
            'total_returns': total_count,
            'filed_returns': filed_count,
            'pending_returns': total_count - filed_count,
            'details': f'Filed {filed_count} out of {total_count} returns'
        }
    except Exception as e:
        error_tracker.log_error("COMPLIANCE_CALCULATION", str(e), {"data_keys": list(data.keys())})
        return {
            'score': 0,
            'grade': 'Error',
            'status': 'Calculation Error',
            'total_returns': 0,
            'filed_returns': 0,
            'pending_returns': 0,
            'details': 'Error calculating compliance score'
        }

def organize_returns_by_year(returns: List[Dict]) -> Dict:
    try:
        returns_by_year = defaultdict(list)
        for ret in returns:
            if ret.get('taxp'):
                try:
                    tax_period = ret['taxp']
                    if len(tax_period) >= 6:
                        month = int(tax_period[:2])
                        year = int(tax_period[2:6])
                        if month >= 4:
                            fy = f"{year}-{year+1}"
                        else:
                            fy = f"{year-1}-{year}"
                        returns_by_year[fy].append(ret)
                except (ValueError, IndexError):
                    current_year = datetime.now().year
                    fy = f"{current_year-1}-{current_year}"
                    returns_by_year[fy].append(ret)
        sorted_years = dict(sorted(returns_by_year.items(), reverse=True))
        return sorted_years
    except Exception as e:
        error_tracker.log_error("RETURNS_ORGANIZATION", str(e), {"returns_count": len(returns)})
        return {}

app = FastAPI(
    title="GST Compliance Platform",
    description="Advanced GST compliance monitoring and reporting platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
trusted_host = os.getenv("TRUSTED_HOST", "localhost")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[trusted_host]
)

static_dir = Path("static")
if not static_dir.exists():
    static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates_dir = Path("templates")
if not templates_dir.exists():
    templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory="templates")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    logger.critical("RAPIDAPI_KEY environment variable is required")
    raise RuntimeError("RAPIDAPI_KEY environment variable is required")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    is_limited, limit_info = rate_limiter.is_rate_limited(client_ip)
    if is_limited:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "details": limit_info}
        )
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        performance_monitor.log_request(
            endpoint=str(request.url.path),
            duration=process_time,
            status_code=response.status_code
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Process-Time"] = str(process_time)
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

@app.exception_handler(GSTPlatformError)
async def gst_platform_error_handler(request: Request, exc: GSTPlatformError):
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

@app.get("/health")
async def health_check():
    try:
        async with httpx.AsyncClient() as client:
            test_response = await client.get(f"https://{RAPIDAPI_HOST}", timeout=5)
        api_healthy = test_response.status_code < 500
    except Exception:
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

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request, "data": None})
    except Exception as e:
        error_tracker.log_error("TEMPLATE_RENDER", str(e), {"template": "index.html"})
        return HTMLResponse("""
        <html>
            <head><title>GST Compliance Platform</title></head>
            <body>
                <h1>GST Compliance Platform</h1>
                <p>Service temporarily unavailable. Please try again later.</p>
            </body>
        </html>
        """, status_code=500)

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request, gstin: str = Form(...)):
    try:
        is_valid, validation_message = validate_gstin(gstin)
        if not is_valid:
            raise GSTINValidationError(validation_message)
        gstin = gstin.strip().upper()
        raw_data = await api_client.fetch_gstin_data(gstin)
        compliance = calculate_enhanced_compliance_score(raw_data)
        returns_by_year = organize_returns_by_year(raw_data.get('filedreturns', []))
        enhanced_data = {
            **raw_data,
            'compliance': compliance,
            'returns_by_year': returns_by_year,
            'returns': raw_data.get('filedreturns', [])
        }
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": enhanced_data,
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

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting GST Compliance Platform...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
        access_log=True
    )

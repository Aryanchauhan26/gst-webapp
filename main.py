#!/usr/bin/env python3
"""
GST Intelligence Platform - Main Application
Enhanced with PostgreSQL database, security improvements, and better error handling
"""

import os
import re
import asyncio
import asyncpg
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, List
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from weasyprint import HTML
from dotenv import load_dotenv
from anthro_ai import get_anthropic_synopsis
from fastapi import Response

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variable validation
def validate_environment():
    """Validate required environment variables"""
    required_vars = {
        'RAPIDAPI_KEY': 'RapidAPI key for GST data',
        'ANTHROPIC_API_KEY': 'Anthropic API key for AI features (optional)'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            # Make ANTHROPIC_API_KEY optional
            if var == 'ANTHROPIC_API_KEY':
                logger.warning(f"Optional {var} not set - AI features will be disabled")
            else:
                missing_vars.append(f"{var} - {description}")
    
    if missing_vars:
        error_msg = "Missing required environment variables:\n" + "\n".join(f"   • {var}" for var in missing_vars)
        logger.error(error_msg)
        raise ValueError(error_msg)

# Validate environment on startup
try:
    validate_environment()
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
except ValueError as e:
    logger.error(f"Configuration Error: {e}")
    # Allow app to start but with limited functionality
    RAPIDAPI_KEY = None
    ANTHROPIC_API_KEY = None

# API Configuration
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")

# Initialize FastAPI app
app = FastAPI(title="GST Intelligence Platform", version="2.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Rate Limiter Implementation
class RateLimiter:
    def __init__(self, max_attempts=5, window_minutes=15):
        self.attempts = defaultdict(list)
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
    
    def is_allowed(self, identifier: str) -> bool:
        now = datetime.now()
        # Clean old attempts
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier]
            if now - attempt < self.window
        ]
        
        if len(self.attempts[identifier]) >= self.max_attempts:
            return False
        
        self.attempts[identifier].append(now)
        return True
    
    def get_retry_after(self, identifier: str) -> int:
        """Get seconds until retry is allowed"""
        if not self.attempts[identifier]:
            return 0
        
        oldest_attempt = min(self.attempts[identifier])
        retry_time = oldest_attempt + self.window
        seconds_left = (retry_time - datetime.now()).total_seconds()
        return max(0, int(seconds_left))

# Initialize rate limiter
login_limiter = RateLimiter()
api_limiter = RateLimiter(max_attempts=60, window_minutes=1)  # API rate limiting

# PostgreSQL Database Manager
POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

class PostgresDB:
    def __init__(self, dsn=POSTGRES_DSN):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)

    async def create_user(self, mobile: str, password_hash: str, salt: str):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (mobile, password_hash, salt) VALUES ($1, $2, $3) ON CONFLICT (mobile) DO NOTHING",
                mobile, password_hash, salt
            )

    async def verify_user(self, mobile: str, password: str) -> bool:
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT password_hash, salt FROM users WHERE mobile=$1", mobile)
            if not row:
                return False
            return check_password(password, row['password_hash'], row['salt'])

    async def create_session(self, mobile: str) -> Optional[str]:
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)
        await self.connect()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO sessions (session_token, mobile, expires_at) VALUES ($1, $2, $3)",
                    session_token, mobile, expires_at
                )
            return session_token
        except Exception as e:
            print(f"Session creation failed: {e}")  # Add this line for debugging
            return None

    async def get_session(self, session_token: str) -> Optional[str]:
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mobile, expires_at FROM sessions WHERE session_token=$1",
                session_token
            )
            if row and row['expires_at'] > datetime.now():
                return row['mobile']
        return None

    async def delete_session(self, session_token: str) -> bool:
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM sessions WHERE session_token=$1",
                session_token
            )
        return True

    async def update_last_login(self, mobile: str):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login=$1 WHERE mobile=$2",
                datetime.now(), mobile
            )

    async def add_search_history(self, mobile: str, gstin: str, company_name: str, compliance_score: float = None):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO search_history (mobile, gstin, company_name, compliance_score) VALUES ($1, $2, $3, $4)",
                mobile, gstin, company_name, compliance_score
            )

    async def get_search_history(self, mobile: str, limit: int = 10) -> List[Dict]:
        await self.connect()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=$1 ORDER BY searched_at DESC LIMIT $2",
                mobile, limit
            )
            return [dict(row) for row in rows]

    async def get_all_searches(self, mobile: str) -> List[Dict]:
        await self.connect()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=$1 ORDER BY searched_at DESC",
                mobile
            )
            return [dict(row) for row in rows]

db = PostgresDB()

# GST API Client with Error Handling
class GSAPIClient:
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": host,
            "User-Agent": "GST-Compliance-Platform/2.0"
        }
    
    async def fetch_gstin_data(self, gstin: str) -> Dict:
        import httpx
        url = f"https://{self.host}/free/gstin/{gstin}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 200:
                json_data = resp.json()
                # Handle new API response structure
                if json_data.get("success") and "data" in json_data:
                    return json_data["data"]
                elif "data" in json_data:
                    return json_data["data"]
                else:
                    # Fallback for old API structure
                    return json_data
            raise HTTPException(status_code=404, detail="GSTIN not found or API error")

api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST) if RAPIDAPI_KEY else None

# Dependency to get current user
async def get_current_user(request: Request) -> Optional[str]:
    """Get current user from session"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    return await db.get_session(session_token)

# Dependency to require authentication
async def require_auth(request: Request) -> str:
    """Require authenticated user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    return user

# Validation functions
def validate_mobile(mobile: str) -> tuple[bool, str]:
    """Validate Indian mobile number"""
    mobile = mobile.strip()
    if not mobile.isdigit() or len(mobile) != 10 or mobile[0] not in "6789":
        return False, "Invalid mobile number"
    return True, ""

def validate_gstin(gstin: str) -> bool:
    """Validate GSTIN format"""
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    return bool(re.match(pattern, gstin.upper()))

def calculate_return_due_date(return_type: str, tax_period: str, fy: str) -> datetime:
    """Calculate the due date for a GST return"""
    try:
        # Parse tax period
        months = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        if tax_period in months:
            month = months[tax_period]
            # Extract year from FY (e.g., "2024-2025" -> 2024 or 2025)
            fy_parts = fy.split('-')
            if month >= 4:  # April to December
                year = int(fy_parts[0])
            else:  # January to March
                year = int(fy_parts[1])
            
            # Due dates
            if return_type == "GSTR1":
                # GSTR-1 due on 11th of next month
                if month == 12:
                    due_date = datetime(year + 1, 1, 11)
                else:
                    due_date = datetime(year, month + 1, 11)
            elif return_type == "GSTR3B":
                # GSTR-3B due on 20th of next month
                if month == 12:
                    due_date = datetime(year + 1, 1, 20)
                else:
                    due_date = datetime(year, month + 1, 20)
            elif return_type == "GSTR9":
                # Annual return due on December 31st of next year
                year = int(fy_parts[1])
                due_date = datetime(year, 12, 31)
            else:
                return None
                
            return due_date
    except:
        return None
    
    return None

def analyze_late_filings(returns: List[Dict]) -> Dict:
    """Analyze returns for late filing"""
    late_returns = []
    on_time_returns = []
    total_delay_days = 0
    
    for return_item in returns:
        return_type = return_item.get("rtntype")
        tax_period = return_item.get("taxp")
        fy = return_item.get("fy")
        dof = return_item.get("dof")
        
        if all([return_type, tax_period, fy, dof]):
            # Calculate due date
            due_date = calculate_return_due_date(return_type, tax_period, fy)
            
            if due_date:
                # Parse filing date
                try:
                    filing_date = datetime.strptime(dof, "%d/%m/%Y")
                    
                    # Check if late
                    if filing_date > due_date:
                        delay_days = (filing_date - due_date).days
                        late_returns.append({
                            'return': return_item,
                            'due_date': due_date,
                            'filing_date': filing_date,
                            'delay_days': delay_days
                        })
                        total_delay_days += delay_days
                    else:
                        on_time_returns.append(return_item)
                except:
                    pass
    
    return {
        'late_count': len(late_returns),
        'on_time_count': len(on_time_returns),
        'late_returns': late_returns,
        'total_delay_days': total_delay_days,
        'average_delay': total_delay_days / len(late_returns) if late_returns else 0
    }

def calculate_compliance_score(company_data: dict) -> float:
    """Calculate comprehensive compliance score based on multiple factors including late filings"""
    score = 100.0
    factors = []
    
    # 1. Registration Status (25 points)
    if company_data.get("sts") == "Active":
        factors.append(("Registration Status", 25, 25, "Active"))
    else:
        factors.append(("Registration Status", 0, 25, company_data.get("sts", "Inactive")))
        score -= 25
    
    # 2. Filing Compliance (20 points)
    returns = company_data.get("returns", [])
    if returns:
        # Calculate filing regularity
        current_date = datetime.now()
        gstr1_returns = [r for r in returns if r.get("rtntype") == "GSTR1"]
        gstr3b_returns = [r for r in returns if r.get("rtntype") == "GSTR3B"]
        
        # Check if filing regularly (expected ~12 per year for monthly filers)
        months_since_reg = 12  # Default to 1 year
        if company_data.get("rgdt"):
            try:
                reg_date = datetime.strptime(company_data["rgdt"], "%d/%m/%Y")
                months_since_reg = max(1, (current_date - reg_date).days // 30)
            except:
                pass
        
        expected_returns = min(months_since_reg, 12)
        filing_ratio = min(len(gstr1_returns) / expected_returns, 1.0) if expected_returns > 0 else 0
        filing_points = int(filing_ratio * 20)
        factors.append(("Return Filing Compliance", filing_points, 20, f"{len(returns)} returns filed"))
        score = score - 20 + filing_points
    else:
        factors.append(("Return Filing Compliance", 0, 20, "No returns filed"))
        score -= 20
    
    # 3. Late Filing Penalty (25 points) - NEW!
    if returns:
        late_filing_analysis = analyze_late_filings(returns)
        late_count = late_filing_analysis['late_count']
        total_returns = late_count + late_filing_analysis['on_time_count']
        
        if total_returns > 0:
            on_time_ratio = late_filing_analysis['on_time_count'] / total_returns
            late_filing_points = int(on_time_ratio * 25)
            
            # Additional penalty for chronic late filing
            avg_delay = late_filing_analysis['average_delay']
            if avg_delay > 30:
                late_filing_points = max(0, late_filing_points - 5)
            
            factors.append(("On-Time Filing", late_filing_points, 25, 
                          f"{late_filing_analysis['on_time_count']} on-time, {late_count} late"))
            score = score - 25 + late_filing_points
        else:
            factors.append(("On-Time Filing", 12, 25, "No filing data"))
            score -= 13
        
        # Store late filing analysis for display
        company_data['_late_filing_analysis'] = late_filing_analysis
    else:
        factors.append(("On-Time Filing", 0, 25, "No returns to analyze"))
        score -= 25
    
    # 4. Filing Recency (15 points)
    if returns:
        latest_return_date = None
        for return_item in returns:
            if return_item.get("dof"):
                try:
                    dof = datetime.strptime(return_item["dof"], "%d/%m/%Y")
                    if not latest_return_date or dof > latest_return_date:
                        latest_return_date = dof
                except:
                    pass
        
        if latest_return_date:
            days_since_filing = (current_date - latest_return_date).days
            if days_since_filing <= 30:
                recency_points = 15
                recency_desc = "Filed within last 30 days"
            elif days_since_filing <= 60:
                recency_points = 10
                recency_desc = "Filed within last 60 days"
            elif days_since_filing <= 90:
                recency_points = 5
                recency_desc = "Filed within last 90 days"
            else:
                recency_points = 0
                recency_desc = f"Last filed {days_since_filing} days ago"
            
            factors.append(("Filing Recency", recency_points, 15, recency_desc))
            score = score - 15 + recency_points
    else:
        factors.append(("Filing Recency", 0, 15, "No filing history"))
        score -= 15
    
    # 5. Filing Frequency Consistency (5 points)
    filing_freq = company_data.get("fillingFreq", {})
    if filing_freq:
        monthly_count = sum(1 for freq in filing_freq.values() if freq == "M")
        quarterly_count = sum(1 for freq in filing_freq.values() if freq == "Q")
        
        if monthly_count >= 6:  # Mostly monthly filer
            freq_points = 5
            freq_desc = "Consistent monthly filer"
        elif quarterly_count >= 6:  # Mostly quarterly filer
            freq_points = 4
            freq_desc = "Consistent quarterly filer"
        else:
            freq_points = 2
            freq_desc = "Mixed filing frequency"
        
        factors.append(("Filing Frequency", freq_points, 5, freq_desc))
        score = score - 5 + freq_points
    else:
        factors.append(("Filing Frequency", 2, 5, "No frequency data"))
        score -= 3
    
    # 6. E-Invoice Compliance (5 points)
    einvoice = company_data.get("einvoiceStatus", "No")
    if einvoice == "Yes":
        factors.append(("E-Invoice Adoption", 5, 5, "E-Invoice enabled"))
    else:
        factors.append(("E-Invoice Adoption", 2, 5, "E-Invoice not enabled"))
        score -= 3
    
    # 7. Annual Return Filing (5 points)
    annual_returns = [r for r in returns if r.get("rtntype") == "GSTR9"]
    if annual_returns:
        factors.append(("Annual Return Filing", 5, 5, f"{len(annual_returns)} annual returns filed"))
    else:
        factors.append(("Annual Return Filing", 0, 5, "No annual returns filed"))
        score -= 5
    
    # Store detailed factors for potential use
    company_data['_compliance_factors'] = factors
    
    return max(0, min(100, score))

# Routes

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database
        db_status = "healthy"
        try:
            await db.connect()
            async with db.pool.acquire() as conn:
                await conn.execute("SELECT 1")
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check API configuration
        api_status = "configured" if RAPIDAPI_KEY else "missing"
        ai_status = "configured" if ANTHROPIC_API_KEY else "disabled"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": datetime.now(),
            "version": "2.0.0",
            "checks": {
                "database": db_status,
                "gst_api": api_status,
                "ai_features": ai_status
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now()
            }
        )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: str = Depends(require_auth)):
    """Home page with search functionality"""
    history = await db.get_search_history(current_user)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "mobile": current_user,
        "history": history
    })

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

# Remove RateLimiter usage from login
@app.post("/login")
async def post_login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    """Process login without rate limiting"""
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": message
        })
    
    if not await db.verify_user(mobile, password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })
    
    # Create session
    session_token = await db.create_session(mobile)
    
    if not session_token:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Failed to create session. Please try again."
        })
    
    await db.update_last_login(mobile)
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )
    return response

@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    """Registration page"""
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def post_signup(request: Request, mobile: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    """Process registration"""
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": message
        })
    
    # Validate password strength
    if len(password) < 6:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Password must be at least 6 characters"
        })
    
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match"
        })
    
    # Hash password with salt
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000, dklen=64).hex()
    
    await db.create_user(mobile, password_hash, salt)
    
    return RedirectResponse(url="/login?registered=true", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.delete_session(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

# Add this route to your main.py file, or replace the existing @app.post("/search") with both routes:

@app.get("/search")
async def search_gstin_get(request: Request, gstin: str = None, current_user: str = Depends(require_auth)):
    """Handle GET requests for search (from View button)"""
    if not gstin:
        return RedirectResponse(url="/", status_code=302)
    
    # Validate GSTIN format
    gstin = gstin.strip().upper()
    if not validate_gstin(gstin):
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": "Invalid GSTIN format",
            "history": history
        })
    
    # Check API rate limit
    if not api_limiter.is_allowed(current_user):
        retry_after = api_limiter.get_retry_after(current_user)
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": f"API rate limit exceeded. Please try again in {retry_after} seconds.",
            "history": history
        })
    
    try:
        # Fetch data from API
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await api_client.fetch_gstin_data(gstin)
        
        # Calculate compliance score
        compliance_score = calculate_compliance_score(company_data)
        
        # Get AI synopsis if available
        synopsis = None
        if ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except Exception as e:
                logger.error(f"Failed to get AI synopsis: {e}")
                synopsis = None
        
        # Add to search history
        await db.add_search_history(
            current_user,
            gstin,
            company_data.get("lgnm", "Unknown"),
            compliance_score
        )
        
        # Get late filing analysis
        late_filing_analysis = company_data.get('_late_filing_analysis', {})
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "mobile": current_user,
            "company_data": company_data,
            "compliance_score": int(compliance_score),
            "synopsis": synopsis,
            "late_filing_analysis": late_filing_analysis
        })
        
    except HTTPException as e:
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": e.detail,
            "history": history
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": "An error occurred while searching. Please try again.",
            "history": history
        })

@app.post("/search")
async def search_gstin(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    """Search for GSTIN with enhanced features"""
    # Validate GSTIN format
    gstin = gstin.strip().upper()
    if not validate_gstin(gstin):
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": "Invalid GSTIN format",
            "history": await db.get_search_history(current_user)
        })
    
    # Check API rate limit
    if not api_limiter.is_allowed(current_user):
        retry_after = api_limiter.get_retry_after(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": f"API rate limit exceeded. Please try again in {retry_after} seconds.",
            "history": await db.get_search_history(current_user)
        })
    
    try:
        # Fetch data from API
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await api_client.fetch_gstin_data(gstin)
        
        # Calculate compliance score
        compliance_score = calculate_compliance_score(company_data)
        
        # Get AI synopsis if available
        synopsis = None
        if ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except Exception as e:
                logger.error(f"Failed to get AI synopsis: {e}")
                synopsis = None
        
        # Add to search history
        await db.add_search_history(
            current_user,
            gstin,
            company_data.get("lgnm", "Unknown"),
            compliance_score
        )
        
        # Get late filing analysis
        late_filing_analysis = company_data.get('_late_filing_analysis', {})
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "mobile": current_user,
            "company_data": company_data,
            "compliance_score": int(compliance_score),
            "synopsis": synopsis,
            "late_filing_analysis": late_filing_analysis
        })
        
    except HTTPException as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": e.detail,
            "history": await db.get_search_history(current_user)
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": "An error occurred while searching. Please try again.",
            "history": await db.get_search_history(current_user)
        })

@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request, current_user: str = Depends(require_auth)):
    """View complete search history"""
    history = await db.get_all_searches(current_user)
    # Calculate searches in the last 30 days
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days
    )
    return templates.TemplateResponse("history.html", {
        "request": request,
        "mobile": current_user,
        "history": history,
        "searches_this_month": searches_this_month
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, current_user: str = Depends(require_auth)):
    """Live Analytics Dashboard"""
    # Get analytics data
    await db.connect()
    async with db.pool.acquire() as conn:
        # Get search trends (last 7 days)
        daily_searches = await conn.fetch("""
            SELECT 
                DATE(searched_at) as date,
                COUNT(*) as search_count,
                AVG(compliance_score) as avg_score
            FROM search_history 
            WHERE mobile = $1 
            AND searched_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(searched_at)
            ORDER BY date
        """, current_user)
        
        # Get compliance score distribution
        score_distribution = await conn.fetch("""
            SELECT 
                CASE 
                    WHEN compliance_score >= 90 THEN 'Excellent (90-100)'
                    WHEN compliance_score >= 80 THEN 'Very Good (80-89)'
                    WHEN compliance_score >= 70 THEN 'Good (70-79)'
                    WHEN compliance_score >= 60 THEN 'Average (60-69)'
                    ELSE 'Poor (<60)'
                END as range,
                COUNT(*) as count
            FROM search_history 
            WHERE mobile = $1
            GROUP BY range
            ORDER BY range DESC
        """, current_user)
        
        # Get top searched companies
        top_companies = await conn.fetch("""
            SELECT 
                company_name,
                gstin,
                COUNT(*) as search_count,
                MAX(compliance_score) as latest_score
            FROM search_history 
            WHERE mobile = $1
            GROUP BY company_name, gstin
            ORDER BY search_count DESC
            LIMIT 10
        """, current_user)
        
        # Get search statistics
        total_searches = await conn.fetchval(
            "SELECT COUNT(*) FROM search_history WHERE mobile = $1", 
            current_user
        )
        
        unique_companies = await conn.fetchval(
            "SELECT COUNT(DISTINCT gstin) FROM search_history WHERE mobile = $1", 
            current_user
        )
        
        avg_compliance = await conn.fetchval(
            "SELECT AVG(compliance_score) FROM search_history WHERE mobile = $1", 
            current_user
        )
    
    # Convert date objects to strings for JSON serialization
    daily_searches = [
        {**dict(row), "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else row["date"]}
        for row in daily_searches
    ]
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "mobile": current_user,
        "daily_searches": daily_searches,
        "score_distribution": [dict(row) for row in score_distribution],
        "top_companies": [dict(row) for row in top_companies],
        "total_searches": total_searches or 0,
        "unique_companies": unique_companies or 0,
        "avg_compliance": round(avg_compliance or 0, 1)
    })

@app.get("/export/history")
async def export_history(current_user: str = Depends(require_auth)):
    """Export search history to CSV"""
    from io import StringIO
    import csv
    history = await db.get_all_searches(current_user)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['searched_at', 'gstin', 'company_name', 'compliance_score'])
    writer.writeheader()
    writer.writerows(history)
    content = output.getvalue()
    output.close()
    
    return StreamingResponse(
        BytesIO(content.encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=gst_search_history_{datetime.now().strftime('%Y%m%d')}.csv"
        }
    )

@app.post("/generate-pdf")
async def generate_pdf(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    """Generate PDF report with fixed implementation"""
    try:
        # Fetch company data
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await api_client.fetch_gstin_data(gstin)
        
        # Calculate compliance score
        compliance_score = calculate_compliance_score(company_data)
        
        # Get AI synopsis if available
        synopsis = None
        if ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except:
                synopsis = "AI synopsis not available"
        
        # Get late filing analysis
        late_filing_analysis = company_data.get('_late_filing_analysis', None)
        
        # Generate PDF
        pdf_content = generate_pdf_report(company_data, compliance_score, synopsis, late_filing_analysis)
        
        return StreamingResponse(
            pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=GST_Report_{gstin}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

# Replace the generate_pdf_report function in main.py with this fixed version

def generate_pdf_report(company_data: dict, compliance_score: float, synopsis: str = None, late_filing_analysis: dict = None) -> BytesIO:
    """Generate comprehensive PDF report with enhanced dashboard-like styling"""
    # Extract data
    company_name = company_data.get("lgnm", "Unknown Company")
    gstin = company_data.get("gstin", "N/A")
    status = company_data.get("sts", "N/A")
    company_type = company_data.get("ctb", "N/A")
    reg_date = company_data.get("rgdt", "N/A")
    pan = company_data.get("pan", "N/A")
    category = company_data.get("compCategory", "N/A")
    trade_name = company_data.get("tradeName", company_name)
    
    # Address details
    address = company_data.get('adr', 'N/A')
    pincode = company_data.get('pincode', 'N/A')
    state = "N/A"
    if company_data.get('stj') and 'State - ' in company_data.get('stj'):
        state = company_data.get('stj').split('State - ')[1].split(',')[0]
    
    # Business details
    nba = company_data.get('nba', [])
    nba_str = ', '.join(nba) if nba else 'N/A'
    einvoice = company_data.get('einvoiceStatus', 'N/A')
    duty_type = company_data.get('dty', 'N/A')
    
    # Returns data
    returns = company_data.get('returns', [])
    gstr1_returns = [r for r in returns if r.get('rtntype') == 'GSTR1']
    gstr3b_returns = [r for r in returns if r.get('rtntype') == 'GSTR3B']
    gstr9_returns = [r for r in returns if r.get('rtntype') == 'GSTR9']
    
    # Get compliance grade
    if compliance_score >= 90:
        grade = "A+"
        grade_text = "Excellent"
        grade_color = "#10b981"
    elif compliance_score >= 80:
        grade = "A"
        grade_text = "Very Good"
        grade_color = "#34d399"
    elif compliance_score >= 70:
        grade = "B"
        grade_text = "Good"
        grade_color = "#f59e0b"
    elif compliance_score >= 60:
        grade = "C"
        grade_text = "Average"
        grade_color = "#f97316"
    else:
        grade = "D"
        grade_text = "Needs Improvement"
        grade_color = "#ef4444"
    
    # HTML content with enhanced dashboard-like styling
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 15mm;
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, Arial, sans-serif;
                color: #1f2937;
                line-height: 1.6;
                background: #ffffff;
            }}
            
            /* Header Section */
            .header {{
                background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
                color: white;
                padding: 30px;
                margin: -15mm -15mm 20px -15mm;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .header-left {{
                flex: 1;
            }}
            
            .header-title {{
                font-size: 28px;
                font-weight: 800;
                margin-bottom: 5px;
                letter-spacing: -0.5px;
            }}
            
            .header-subtitle {{
                font-size: 14px;
                opacity: 0.9;
            }}
            
            .header-date {{
                font-size: 12px;
                opacity: 0.8;
                text-align: right;
            }}
            
            /* Company Info Section */
            .company-section {{
                background: #f8f9fa;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                border-left: 4px solid #7c3aed;
            }}
            
            .company-name {{
                font-size: 24px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 5px;
            }}
            
            .company-gstin {{
                font-size: 14px;
                color: #6b7280;
                font-family: monospace;
            }}
            
            /* Compliance Score Section */
            .compliance-section {{
                background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
                color: white;
                border-radius: 12px;
                padding: 25px;
                text-align: center;
                margin-bottom: 20px;
            }}
            
            .score-container {{
                display: inline-block;
                position: relative;
            }}
            
            .score-circle {{
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 15px;
                border: 3px solid rgba(255, 255, 255, 0.4);
            }}
            
            .score-value {{
                font-size: 36px;
                font-weight: 800;
            }}
            
            .score-grade {{
                font-size: 20px;
                font-weight: 600;
                padding: 5px 20px;
                background-color: {grade_color};
                border-radius: 20px;
                display: inline-block;
            }}
            
            /* Synopsis Section */
            .synopsis-section {{
                background: #e0e7ff;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                border-left: 4px solid #7c3aed;
            }}
            
            .synopsis-title {{
                font-size: 18px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .synopsis-content {{
                color: #374151;
                line-height: 1.8;
                font-size: 14px;
                text-align: justify;
            }}
            
            /* Stats Grid */
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin-bottom: 20px;
            }}
            
            .stat-card {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 15px;
                text-align: center;
                border: 1px solid #e5e7eb;
            }}
            
            .stat-value {{
                font-size: 24px;
                font-weight: 700;
                color: #7c3aed;
                margin-bottom: 5px;
            }}
            
            .stat-label {{
                font-size: 12px;
                color: #6b7280;
            }}
            
            /* Info Grid */
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin-bottom: 20px;
            }}
            
            .info-card {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 20px;
                page-break-inside: avoid;
            }}
            
            .info-card-title {{
                font-size: 16px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #7c3aed;
            }}
            
            .info-item {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #f3f4f6;
            }}
            
            .info-item:last-child {{
                border-bottom: none;
            }}
            
            .info-label {{
                font-size: 13px;
                color: #6b7280;
                font-weight: 500;
            }}
            
            .info-value {{
                font-size: 13px;
                color: #1f2937;
                font-weight: 600;
                text-align: right;
                max-width: 60%;
                word-wrap: break-word;
            }}
            
            /* Returns Section */
            .returns-section {{
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            
            .returns-title {{
                font-size: 18px;
                font-weight: 700;
                color: #1f2937;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #7c3aed;
            }}
            
            /* Alert Box */
            .alert {{
                background: #fef3c7;
                border: 1px solid #fbbf24;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .alert-icon {{
                font-size: 20px;
            }}
            
            .alert-content {{
                flex: 1;
            }}
            
            .alert-title {{
                font-weight: 600;
                color: #92400e;
                margin-bottom: 3px;
                font-size: 14px;
            }}
            
            .alert-text {{
                color: #78350f;
                font-size: 12px;
            }}
            
            /* Table Styles */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 12px;
            }}
            
            th {{
                background: #f8f9fa;
                padding: 10px;
                text-align: left;
                font-weight: 600;
                border: 1px solid #e5e7eb;
                color: #1f2937;
            }}
            
            td {{
                padding: 8px;
                border: 1px solid #e5e7eb;
            }}
            
            tr:nth-child(even) {{
                background: #f9fafb;
            }}
            
            /* Status Badges */
            .status-badge {{
                display: inline-block;
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            
            .status-active {{
                background: #d1fae5;
                color: #065f46;
            }}
            
            .status-inactive {{
                background: #fee2e2;
                color: #991b1b;
            }}
            
            .status-late {{
                background: #fee2e2;
                color: #991b1b;
            }}
            
            .status-on-time {{
                background: #d1fae5;
                color: #065f46;
            }}
            
            /* Footer */
            .footer {{
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                text-align: center;
                border-top: 2px solid #e5e7eb;
            }}
            
            .footer p {{
                color: #6b7280;
                font-size: 11px;
                margin: 3px 0;
            }}
            
            /* Utilities */
            .text-center {{ text-align: center; }}
            .mb-10 {{ margin-bottom: 10px; }}
            .mb-20 {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <div class="header">
            <div class="header-left">
                <div class="header-title">GST Compliance Report</div>
                <div class="header-subtitle">Advanced Business Analytics Platform</div>
            </div>
            <div class="header-date">Generated on {datetime.now().strftime("%d %B %Y")}</div>
        </div>
        
        <!-- Company Section -->
        <div class="company-section">
            <div class="company-name">{company_name}</div>
            <div class="company-gstin">GSTIN: {gstin}</div>
        </div>
        
        <!-- Compliance Score -->
        <div class="compliance-section">
            <h2 style="margin-bottom: 15px; font-size: 16px; font-weight: 500;">Overall Compliance Score</h2>
            <div class="score-container">
                <div class="score-circle">
                    <div class="score-value">{int(compliance_score)}%</div>
                </div>
            </div>
            <div class="score-grade">{grade} ({grade_text})</div>
            <p style="margin-top: 10px; font-size: 12px; opacity: 0.9;">Based on registration status, filing history, and compliance factors</p>
        </div>
        
        {f'''<!-- AI Synopsis -->
        <div class="synopsis-section">
            <h3 class="synopsis-title">
                <span>🔍</span>
                Company Overview
            </h3>
            <div class="synopsis-content">{synopsis}</div>
            <p style="font-size: 11px; color: #6b7280; margin-top: 10px; font-style: italic;">
                This overview is generated using AI analysis and web research.
            </p>
        </div>''' if synopsis else ''}
        
        <!-- Stats Overview -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(returns)}</div>
                <div class="stat-label">Total Returns</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(gstr1_returns)}</div>
                <div class="stat-label">GSTR-1 Filed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(gstr3b_returns)}</div>
                <div class="stat-label">GSTR-3B Filed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(gstr9_returns)}</div>
                <div class="stat-label">Annual Returns</div>
            </div>
        </div>
        
        <!-- Company Information Grid -->
        <div class="info-grid">
            <div class="info-card">
                <h3 class="info-card-title">Company Information</h3>
                <div class="info-item">
                    <span class="info-label">Legal Name</span>
                    <span class="info-value">{company_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Trade Name</span>
                    <span class="info-value">{trade_name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Business Type</span>
                    <span class="info-value">{company_type}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Registration Date</span>
                    <span class="info-value">{reg_date}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Status</span>
                    <span class="info-value">
                        <span class="status-badge {'status-active' if status == 'Active' else 'status-inactive'}">{status}</span>
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">PAN</span>
                    <span class="info-value">{pan}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Company Category</span>
                    <span class="info-value">{category}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">E-Invoice Status</span>
                    <span class="info-value">{einvoice}</span>
                </div>
            </div>
            
            <div class="info-card">
                <h3 class="info-card-title">Business Details</h3>
                <div class="info-item">
                    <span class="info-label">Address</span>
                    <span class="info-value" style="text-align: left; font-size: 11px;">{address}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Pincode</span>
                    <span class="info-value">{pincode}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">State</span>
                    <span class="info-value">{state}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Nature of Business</span>
                    <span class="info-value" style="text-align: left; font-size: 11px;">{nba_str}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Duty Type</span>
                    <span class="info-value">{duty_type}</span>
                </div>
            </div>
        </div>
        
        <!-- GST Returns Section -->
        <div class="returns-section">
            <h3 class="returns-title">GST Returns Summary</h3>
            
            {f'''<div class="alert">
                <div class="alert-icon">⚠️</div>
                <div class="alert-content">
                    <div class="alert-title">Late Filing Alert</div>
                    <div class="alert-text">{late_filing_analysis['late_count']} returns filed late out of {late_filing_analysis['late_count'] + late_filing_analysis['on_time_count']} total returns. Average delay: {late_filing_analysis['average_delay']:.1f} days.</div>
                </div>
            </div>''' if late_filing_analysis and late_filing_analysis.get('late_count', 0) > 0 else ''}
            
            <h4 style="margin-top: 15px; margin-bottom: 10px; font-size: 14px; color: #1f2937;">Recent Filing History (Latest 10)</h4>
            <table>
                <thead>
                    <tr>
                        <th>Return Type</th>
                        <th>Tax Period</th>
                        <th>Financial Year</th>
                        <th>Filing Date</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {_generate_returns_rows(returns[:10], late_filing_analysis)}
                </tbody>
            </table>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p><strong>GST Intelligence Platform</strong></p>
            <p>This report is generated based on available GST data and AI analysis.</p>
            <p>For the most current information, please verify with the official GST portal.</p>
            <p style="margin-top: 10px;">© {datetime.now().year} GST Intelligence Platform. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(target=pdf_file)
    pdf_file.seek(0)
    
    return pdf_file

def _generate_returns_rows(returns, late_filing_analysis):
    """Helper method to generate table rows for returns"""
    rows_html = ""
    for r in returns:
        return_type = r.get('rtntype', 'N/A')
        tax_period = r.get('taxp', 'N/A')
        fy = r.get('fy', 'N/A')
        dof = r.get('dof', 'N/A')
        
        # Check if late
        status_html = '<span class="status-badge status-on-time">On Time</span>'
        if late_filing_analysis and late_filing_analysis.get('late_returns'):
            for lr in late_filing_analysis['late_returns']:
                if (lr['return'].get('dof') == dof and 
                    lr['return'].get('rtntype') == return_type):
                    status_html = f'<span class="status-badge status-late">Late by {lr["delay_days"]} days</span>'
                    break
        
        rows_html += f"""
            <tr>
                <td>{return_type}</td>
                <td>{tax_period}</td>
                <td>{fy}</td>
                <td>{dof}</td>
                <td>{status_html}</td>
            </tr>
        """
    
    return rows_html

@app.post("/refresh-session")
async def refresh_session(current_user: str = Depends(require_auth)):
    """Refresh session to prevent timeout"""
    return {"status": "success", "message": "Session refreshed"}

@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon to prevent 404 errors"""
    # Return a 1x1 transparent PNG
    favicon_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x01\x8d\xc8\x02\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=favicon_bytes, media_type="image/png")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        # Properly handle redirect
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"error": "An internal error occurred. Please try again later."}
    )

# Cleanup tasks
@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    logger.info("GST Intelligence Platform starting up...")
    # Clean up old sessions in Postgres
    await db.connect()
    async with db.pool.acquire() as conn:
        await conn.execute('DELETE FROM sessions WHERE expires_at < $1', datetime.now())
    logger.info("Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown tasks"""
    logger.info("GST Intelligence Platform shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

def check_password(password: str, stored_hash: str, salt: str) -> bool:
    hash_attempt = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000, dklen=64).hex()
    return hash_attempt == stored_hash
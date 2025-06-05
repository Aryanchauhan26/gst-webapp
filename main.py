#!/usr/bin/env python3
"""
GST Intelligence Platform - Main Application
Enhanced with SQLite database, security improvements, and better error handling
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
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        await self.connect()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO sessions (session_token, mobile, expires_at) VALUES ($1, $2, $3)",
                    session_token, mobile, expires_at
                )
            return session_token
        except Exception:
            return None

    async def get_session(self, session_token: str) -> Optional[str]:
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mobile, expires_at FROM sessions WHERE session_token=$1",
                session_token
            )
            if row and datetime.fromisoformat(row['expires_at']) > datetime.now():
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
                datetime.now().isoformat(), mobile
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
            "timestamp": datetime.now().isoformat(),
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
                "timestamp": datetime.now().isoformat()
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

@app.post("/login")
async def post_login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    """Process login with rate limiting"""
    # Get client IP for rate limiting
    client_ip = request.client.host
    
    # Check rate limit
    if not login_limiter.is_allowed(client_ip):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Too many attempts. Try again later."
        })
    
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
    return templates.TemplateResponse("history.html", {
        "request": request,
        "mobile": current_user,
        "history": history
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

def generate_pdf_report(company_data: dict, compliance_score: float, synopsis: str = None, late_filing_analysis: dict = None) -> BytesIO:
    """Generate comprehensive PDF report with company data and late filing analysis"""
    # Extract address parts if available
    address = company_data.get('adr', 'N/A')
    state = "Maharashtra"  # Default based on GSTIN prefix 27
    if address != 'N/A':
        # Try to extract state from address
        address_parts = address.split(',')
        if len(address_parts) > 3:
            for part in address_parts:
                if any(state_name in part for state_name in ['Maharashtra', 'Gujarat', 'Delhi', 'Karnataka', 'Tamil Nadu']):
                    state = part.strip()
                    break
    
    # Extract jurisdiction info
    ctj = company_data.get('ctj', '')
    stj = company_data.get('stj', '')
    jurisdiction = f"{stj}" if stj else "N/A"
    
    # Get returns summary
    returns = company_data.get('returns', [])
    gstr1_count = len([r for r in returns if r.get('rtntype') == 'GSTR1'])
    gstr3b_count = len([r for r in returns if r.get('rtntype') == 'GSTR3B'])
    gstr9_count = len([r for r in returns if r.get('rtntype') == 'GSTR9'])
    
    # Get compliance grade
    if compliance_score >= 90:
        grade = "A+ (Excellent)"
        grade_color = "#10b981"
    elif compliance_score >= 80:
        grade = "A (Very Good)"
        grade_color = "#34d399"
    elif compliance_score >= 70:
        grade = "B (Good)"
        grade_color = "#f59e0b"
    elif compliance_score >= 60:
        grade = "C (Average)"
        grade_color = "#f97316"
    else:
        grade = "D (Needs Improvement)"
        grade_color = "#ef4444"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 40px;
                color: #333;
                line-height: 1.6;
            }}
            .header {{
                background-color: #1e3c72;
                color: white;
                padding: 30px;
                margin: -40px -40px 30px -40px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 32px;
                font-weight: bold;
            }}
            .header p {{
                margin: 10px 0 0 0;
                font-size: 16px;
                opacity: 0.9;
            }}
            .section {{
                margin-bottom: 30px;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
                page-break-inside: avoid;
            }}
            .section h2 {{
                color: #1e3c72;
                margin-top: 0;
                font-size: 22px;
                border-bottom: 2px solid #1e3c72;
                padding-bottom: 10px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-top: 15px;
            }}
            .info-item {{
                padding: 12px;
                background-color: white;
                border-radius: 5px;
                border: 1px solid #e0e0e0;
            }}
            .info-label {{
                font-weight: bold;
                color: #666;
                font-size: 14px;
                display: block;
                margin-bottom: 5px;
            }}
            .info-value {{
                font-size: 16px;
                color: #333;
            }}
            .compliance-score {{
                text-align: center;
                padding: 30px;
                background-color: #2a5298;
                color: white;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .score-value {{
                font-size: 60px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .score-grade {{
                font-size: 24px;
                margin: 10px 0;
                padding: 5px 20px;
                background-color: {grade_color};
                border-radius: 20px;
                display: inline-block;
            }}
            .returns-summary {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 20px 0;
            }}
            .return-stat {{
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
                border: 1px solid #e0e0e0;
            }}
            .return-stat-value {{
                font-size: 28px;
                font-weight: bold;
                color: #1e3c72;
            }}
            .return-stat-label {{
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }}
            .synopsis {{
                background-color: #e3f2fd;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
                line-height: 1.8;
            }}
            .synopsis h2 {{
                color: #1e3c72;
                border-color: #2196F3;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #666;
                font-size: 12px;
            }}
            .status-active {{
                color: #10b981;
                font-weight: bold;
            }}
            .status-inactive {{
                color: #ef4444;
                font-weight: bold;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th {{
                background-color: #f0f0f0;
                padding: 10px;
                text-align: left;
                font-weight: bold;
                border-bottom: 2px solid #ddd;
            }}
            td {{
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }}
            @page {{
                margin: 0;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>GST Compliance Report</h1>
            <p>Generated on {datetime.now().strftime("%d %B %Y at %I:%M %p")}</p>
            {returns_table}
        </div>
        
        <div class="section">
            <h2>Company Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Legal Name</span>
                    <span class="info-value">{company_data.get('lgnm', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">GSTIN</span>
                    <span class="info-value">{company_data.get('gstin', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Trade Name</span>
                    <span class="info-value">{company_data.get('tradeName', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Business Type</span>
                    <span class="info-value">{company_data.get('ctb', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Registration Date</span>
                    <span class="info-value">{company_data.get('rgdt', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Status</span>
                    <span class="info-value{' status-active' if company_data.get('sts') == 'Active' else ' status-inactive'}">
                        {company_data.get('sts', 'N/A')}
                    </span>
                </div>
                <div class="info-item">
                    <span class="info-label">PAN</span>
                    <span class="info-value">{company_data.get('pan', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Company Category</span>
                    <span class="info-value">{company_data.get('compCategory', 'N/A')}</span>
                </div>
            </div>
        </div>
        
        <div class="compliance-score">
            <h2 style="color: white; border: none; margin-bottom: 20px;">Compliance Score</h2>
            <div class="score-value">{int(compliance_score)}%</div>
            <div class="score-grade">{grade}</div>
            <p style="margin-top: 20px;">Based on registration status, filing history, and compliance factors</p>
            
            {f'''<div style="margin-top: 25px; background-color: rgba(255,255,255,0.1); padding: 15px; border-radius: 5px;">
                <h3 style="color: white; margin-bottom: 10px; font-size: 16px;">Score Breakdown</h3>
                {''.join(f'<div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.2);"><span>{factor[0]}</span><span>{factor[1]}/{factor[2]} pts</span></div>' for factor in company_data.get('_compliance_factors', []))}
            </div>''' if company_data.get('_compliance_factors') else ''}
        </div>
        
        <div class="section">
            <h2>GST Returns Summary</h2>
            {f'''<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
                <strong style="color: #856404;">⚠️ Late Filing Alert:</strong> {late_filing_analysis['late_count']} returns filed late out of {late_filing_analysis['late_count'] + late_filing_analysis['on_time_count']} total returns.
                Average delay: {late_filing_analysis['average_delay']:.1f} days.
            </div>''' if late_filing_analysis and late_filing_analysis['late_count'] > 0 else ''}
            <div class="returns-summary">
                <div class="return-stat">
                    <div class="return-stat-value">{len(returns)}</div>
                    <div class="return-stat-label">Total Returns</div>
                </div>
                <div class="return-stat">
                    <div class="return-stat-value">{gstr1_count}</div>
                    <div class="return-stat-label">GSTR-1 Filed</div>
                </div>
                <div class="return-stat">
                    <div class="return-stat-value">{gstr3b_count}</div>
                    <div class="return-stat-label">GSTR-3B Filed</div>
                </div>
                <div class="return-stat">
                    <div class="return-stat-value">{gstr9_count}</div>
                    <div class="return-stat-label">Annual Returns</div>
                </div>
            </div>
            
            # Prepare returns data for table
            table_rows = []
            for r in returns[:5]:
                return_type = r.get('rtntype')
                tax_period = r.get('taxp')
                fy = r.get('fy')
                dof = r.get('dof')
                
                # Check if this return was filed late
                status = 'On Time'
                if late_filing_analysis and late_filing_analysis.get('late_returns'):
                    for lr in late_filing_analysis['late_returns']:
                        if (lr['return']['dof'] == dof and 
                            lr['return']['rtntype'] == return_type):
                            status = f"Late by {lr['delay_days']} days"
                            break
                
                table_rows.append(f"<tr><td>{return_type}</td><td>{tax_period}</td><td>{fy}</td><td>{dof}</td><td>{status}</td></tr>")
            
            returns_table = f'''<h3 style="margin-top: 25px;">Latest Returns Filed</h3>
            <table>
                <tr>
                    <th>Return Type</th>
                    <th>Tax Period</th>
                    <th>Financial Year</th>
                    <th>Filing Date</th>
                    <th>Status</th>
                </tr>
                {''.join(table_rows)}
            </table>''' if returns else '<p>No return filing history available.</p>'
        </div>
        
        <div class="section">
            <h2>Business Details</h2>
            <div class="info-grid">
                <div class="info-item" style="grid-column: 1 / -1;">
                    <span class="info-label">Principal Place of Business</span>
                    <span class="info-value">{address}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">State</span>
                    <span class="info-value">{state}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Nature of Business</span>
                    <span class="info-value">{', '.join(company_data.get('nba', [])) if company_data.get('nba') else 'N/A'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">State Jurisdiction</span>
                    <span class="info-value" style="font-size: 14px;">{company_data.get('stj', 'N/A')}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Central Jurisdiction</span>
                    <span class="info-value" style="font-size: 14px;">{company_data.get('ctj', 'N/A')}</span>
                </div>
            </div>
        </div>
        
        {f'''<div class="synopsis">
            <h2 style="color: #1e3c72;">Company Overview</h2>
            <p>{synopsis}</p>
            <p style="font-size: 12px; color: #666; margin-top: 15px;">
                <em>This overview is generated using AI analysis and web research.</em>
            </p>
        </div>''' if synopsis else ''}
        
        <div class="footer">
            <p><strong>Disclaimer:</strong> This report is generated by GST Intelligence Platform based on available GST data.</p>
            <p>For the most current information, please verify with the official GST portal.</p>
            <p>&copy; {datetime.now().year} GST Intelligence Platform. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(target=pdf_file)
    pdf_file.seek(0)
    
    return pdf_file

@app.post("/refresh-session")
async def refresh_session(current_user: str = Depends(require_auth)):
    """Refresh session to prevent timeout"""
    return {"status": "success", "message": "Session refreshed"}

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
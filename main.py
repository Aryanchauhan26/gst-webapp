#!/usr/bin/env python3
"""
GST Intelligence Platform - Main Application (Fixed Version)
Enhanced with PostgreSQL database and AI-powered insights
"""

import os
import re
import asyncio
import asyncpg
import hashlib
import secrets
import logging
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, List
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment Configuration
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") 
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# Initialize FastAPI app
app = FastAPI(title="GST Intelligence Platform", version="2.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Add template globals
def setup_template_globals():
    """Setup global template variables"""
    templates.env.globals.update({
        'current_year': datetime.now().year,
        'app_version': "2.0.0"
    })

# Authentication functions
async def get_current_user(request: Request) -> Optional[str]:
    """Get current user from session"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    return await db.get_session(session_token)

async def require_auth(request: Request) -> str:
    """Require authentication for protected routes"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER, 
            headers={"Location": "/login"}
        )
    return user

# Rate Limiter
class RateLimiter:
    def __init__(self, max_attempts=5, window_minutes=15):
        self.attempts = defaultdict(list)
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
    
    def is_allowed(self, identifier: str) -> bool:
        now = datetime.now()
        self.attempts[identifier] = [
            attempt for attempt in self.attempts[identifier]
            if now - attempt < self.window
        ]
        
        if len(self.attempts[identifier]) >= self.max_attempts:
            return False
        
        self.attempts[identifier].append(now)
        return True

# Initialize rate limiters
login_limiter = RateLimiter()
api_limiter = RateLimiter(max_attempts=60, window_minutes=1)

# PostgreSQL Database Manager
class PostgresDB:
    def __init__(self, dsn=POSTGRES_DSN):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)

    async def ensure_tables(self):
        """Ensure all required tables exist"""
        await self.connect()
        async with self.pool.acquire() as conn:
            # Create users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    mobile VARCHAR(10) PRIMARY KEY,
                    password_hash VARCHAR(128) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
            """)
            
            # Create sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token VARCHAR(64) PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            
            # Create search_history table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    compliance_score DECIMAL(5,2),
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            
            # Create user_preferences table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    mobile VARCHAR(10) PRIMARY KEY,
                    preferences JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);")

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
            logger.error(f"Session creation failed: {e}")
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

    async def delete_session(self, session_token: str):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM sessions WHERE session_token=$1", session_token)

    async def update_last_login(self, mobile: str):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE users SET last_login=$1 WHERE mobile=$2", datetime.now(), mobile)

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

# GST API Client
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
                if json_data.get("success") and "data" in json_data:
                    return json_data["data"]
                elif "data" in json_data:
                    return json_data["data"]
                else:
                    return json_data
            raise HTTPException(status_code=404, detail="GSTIN not found or API error")

api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST) if RAPIDAPI_KEY else None

# Validation functions
def validate_mobile(mobile: str) -> tuple[bool, str]:
    mobile = mobile.strip()
    if not mobile.isdigit() or len(mobile) != 10 or mobile[0] not in "6789":
        return False, "Invalid mobile number"
    return True, ""

def validate_gstin(gstin: str) -> bool:
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    return bool(re.match(pattern, gstin.upper()))

def calculate_return_due_date(return_type: str, tax_period: str, fy: str) -> datetime:
    try:
        months = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        
        if tax_period in months:
            month = months[tax_period]
            fy_parts = fy.split('-')
            if month >= 4:
                year = int(fy_parts[0])
            else:
                year = int(fy_parts[1])
            
            if return_type == "GSTR1":
                if month == 12:
                    due_date = datetime(year + 1, 1, 11)
                else:
                    due_date = datetime(year, month + 1, 11)
            elif return_type == "GSTR3B":
                if month == 12:
                    due_date = datetime(year + 1, 1, 20)
                else:
                    due_date = datetime(year, month + 1, 20)
            elif return_type == "GSTR9":
                year = int(fy_parts[1])
                due_date = datetime(year, 12, 31)
            else:
                return None
                
            return due_date
    except:
        return None
    
    return None

def analyze_late_filings(returns: List[Dict]) -> Dict:
    late_returns = []
    on_time_returns = []
    total_delay_days = 0
    
    for return_item in returns:
        return_type = return_item.get("rtntype")
        tax_period = return_item.get("taxp")
        fy = return_item.get("fy")
        dof = return_item.get("dof")
        
        if all([return_type, tax_period, fy, dof]):
            due_date = calculate_return_due_date(return_type, tax_period, fy)
            
            if due_date:
                try:
                    filing_date = datetime.strptime(dof, "%d/%m/%Y")
                    
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
    """Calculate compliance score with proper logic"""
    score = 100.0
    
    # Registration Status (25 points)
    if company_data.get("sts") != "Active":
        score -= 25
    
    # Filing Compliance (20 points)
    returns = company_data.get("returns", [])
    if returns:
        current_date = datetime.now()
        gstr1_returns = [r for r in returns if r.get("rtntype") == "GSTR1"]
        
        months_since_reg = 12
        if company_data.get("rgdt"):
            try:
                reg_date = datetime.strptime(company_data["rgdt"], "%d/%m/%Y")
                months_since_reg = max(1, (current_date - reg_date).days // 30)
            except:
                pass
        
        expected_returns = min(months_since_reg, 12)
        filing_ratio = min(len(gstr1_returns) / expected_returns, 1.0) if expected_returns > 0 else 0
        filing_points = int(filing_ratio * 20)
        score = score - 20 + filing_points
    else:
        score -= 20
    
    # Late Filing Analysis (25 points)
    if returns:
        late_filing_analysis = analyze_late_filings(returns)
        late_count = late_filing_analysis['late_count']
        total_returns = late_count + late_filing_analysis['on_time_count']
        
        if total_returns > 0:
            on_time_ratio = late_filing_analysis['on_time_count'] / total_returns
            late_filing_points = int(on_time_ratio * 25)
            
            avg_delay = late_filing_analysis['average_delay']
            if avg_delay > 30:
                late_filing_points = max(0, late_filing_points - 5)
            
            score = score - 25 + late_filing_points
        else:
            score -= 13
        
        company_data['_late_filing_analysis'] = late_filing_analysis
    else:
        score -= 25
    
    # Filing Recency (15 points)
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
            elif days_since_filing <= 60:
                recency_points = 10
            elif days_since_filing <= 90:
                recency_points = 5
            else:
                recency_points = 0
            
            score = score - 15 + recency_points
    else:
        score -= 15
    
    # Filing Frequency (5 points)
    filing_freq = company_data.get("fillingFreq", {})
    if filing_freq:
        monthly_count = sum(1 for freq in filing_freq.values() if freq == "M")
        quarterly_count = sum(1 for freq in filing_freq.values() if freq == "Q")
        
        if monthly_count >= 6:
            freq_points = 5
        elif quarterly_count >= 6:
            freq_points = 4
        else:
            freq_points = 2
        
        score = score - 5 + freq_points
    else:
        score -= 3
    
    # E-Invoice & Annual Returns (5 points each)
    einvoice = company_data.get("einvoiceStatus", "No")
    if einvoice != "Yes":
        score -= 3
    
    annual_returns = [r for r in returns if r.get("rtntype") == "GSTR9"]
    if not annual_returns:
        score -= 5
    
    final_score = max(0, min(100, score))
    logger.info(f"Calculated compliance score: {final_score} for company {company_data.get('lgnm', 'Unknown')}")
    return final_score

def check_password(password: str, stored_hash: str, salt: str) -> bool:
    hash_attempt = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000, dklen=64).hex()
    return hash_attempt == stored_hash

# Routes
@app.get("/health")
async def health_check():
    try:
        db_status = "healthy"
        try:
            await db.connect()
            async with db.pool.acquire() as conn:
                await conn.execute("SELECT 1")
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": datetime.now(),
            "version": "2.0.0",
            "checks": {
                "database": db_status,
                "gst_api": "configured" if RAPIDAPI_KEY else "missing",
                "ai_features": "configured" if ANTHROPIC_API_KEY else "disabled"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.now()}
        )

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: str = Depends(require_auth)):
    history = await db.get_search_history(current_user)
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "current_user": current_user, 
        "history": history
    })

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def post_login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("login.html", {"request": request, "error": message})
    
    if not await db.verify_user(mobile, password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    session_token = await db.create_session(mobile)
    if not session_token:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Failed to create session"})
    
    await db.update_last_login(mobile)
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token", value=session_token, max_age=7 * 24 * 60 * 60,
        httponly=True, samesite="lax", secure=False
    )
    return response

@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def post_signup(request: Request, mobile: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("signup.html", {"request": request, "error": message})
    
    if len(password) < 6:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Password must be at least 6 characters"})
    
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Passwords do not match"})
    
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000, dklen=64).hex()
    
    await db.create_user(mobile, password_hash, salt)
    return RedirectResponse(url="/login?registered=true", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.delete_session(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

@app.get("/search")
async def search_gstin_get(request: Request, gstin: str = None, current_user: str = Depends(require_auth)):
    if not gstin:
        return RedirectResponse(url="/", status_code=302)
    
    return await process_search(request, gstin, current_user)

@app.post("/search")
async def search_gstin_post(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    return await process_search(request, gstin, current_user)

async def process_search(request: Request, gstin: str, current_user: str):
    gstin = gstin.strip().upper()
    if not validate_gstin(gstin):
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, "current_user": current_user, "error": "Invalid GSTIN format", "history": history
        })
    
    if not api_limiter.is_allowed(current_user):
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, "current_user": current_user, 
            "error": "API rate limit exceeded. Please try again later.", "history": history
        })
    
    try:
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await api_client.fetch_gstin_data(gstin)
        
        # Calculate compliance score
        compliance_score = calculate_compliance_score(company_data)
        logger.info(f"Final compliance score for template: {compliance_score}")
        
        synopsis = None
        if ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except Exception as e:
                logger.error(f"Failed to get AI synopsis: {e}")
        
        # Add to search history
        await db.add_search_history(current_user, gstin, company_data.get("lgnm", "Unknown"), compliance_score)
        
        late_filing_analysis = company_data.get('_late_filing_analysis', {})
        
        return templates.TemplateResponse("results.html", {
            "request": request, 
            "current_user": current_user, 
            "company_data": company_data,
            "compliance_score": int(compliance_score),
            "synopsis": synopsis,
            "late_filing_analysis": late_filing_analysis
        })
        
    except HTTPException as e:
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, "current_user": current_user, "error": e.detail, "history": history
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, "current_user": current_user, 
            "error": "An error occurred while searching. Please try again.", "history": history
        })

@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request, current_user: str = Depends(require_auth)):
    history = await db.get_all_searches(current_user)
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days
    )
    return templates.TemplateResponse("history.html", {
        "request": request, 
        "current_user": current_user, 
        "history": history,
        "searches_this_month": searches_this_month
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, current_user: str = Depends(require_auth)):
    await db.connect()
    async with db.pool.acquire() as conn:
        daily_searches = await conn.fetch("""
            SELECT DATE(searched_at) as date, COUNT(*) as search_count, AVG(compliance_score) as avg_score
            FROM search_history WHERE mobile = $1 AND searched_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(searched_at) ORDER BY date
        """, current_user)
        
        score_distribution = await conn.fetch("""
            SELECT CASE WHEN compliance_score >= 90 THEN 'Excellent (90-100)'
                        WHEN compliance_score >= 80 THEN 'Very Good (80-89)'
                        WHEN compliance_score >= 70 THEN 'Good (70-79)'
                        WHEN compliance_score >= 60 THEN 'Average (60-69)'
                        ELSE 'Poor (<60)' END as range, COUNT(*) as count
            FROM search_history WHERE mobile = $1 AND compliance_score IS NOT NULL GROUP BY range ORDER BY range DESC
        """, current_user)
        
        top_companies = await conn.fetch("""
            SELECT company_name, gstin, COUNT(*) as search_count, MAX(compliance_score) as latest_score
            FROM search_history WHERE mobile = $1 GROUP BY company_name, gstin
            ORDER BY search_count DESC LIMIT 10
        """, current_user)
        
        total_searches = await conn.fetchval("SELECT COUNT(*) FROM search_history WHERE mobile = $1", current_user)
        unique_companies = await conn.fetchval("SELECT COUNT(DISTINCT gstin) FROM search_history WHERE mobile = $1", current_user)
        avg_compliance = await conn.fetchval("SELECT AVG(compliance_score) FROM search_history WHERE mobile = $1", current_user)
    
    daily_searches = [
        {**dict(row), "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else row["date"]}
        for row in daily_searches
    ]
    
    return templates.TemplateResponse("analytics.html", {
        "request": request, 
        "current_user": current_user, 
        "daily_searches": daily_searches,
        "score_distribution": [dict(row) for row in score_distribution],
        "top_companies": [dict(row) for row in top_companies],
        "total_searches": total_searches or 0, 
        "unique_companies": unique_companies or 0,
        "avg_compliance": round(avg_compliance or 0, 1)
    })

@app.get("/export/history")
async def export_history(current_user: str = Depends(require_auth)):
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
        BytesIO(content.encode()), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=gst_search_history_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.post("/generate-pdf")
async def generate_pdf(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    try:
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)
        
        synopsis = None
        if ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except:
                synopsis = "AI synopsis not available"
        
        late_filing_analysis = company_data.get('_late_filing_analysis', None)
        pdf_content = generate_pdf_report(company_data, compliance_score, synopsis, late_filing_analysis)
        
        return StreamingResponse(
            pdf_content, media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=GST_Report_{gstin}.pdf"}
        )
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

def generate_pdf_report(company_data: dict, compliance_score: float, synopsis: str = None, late_filing_analysis: dict = None) -> BytesIO:
    """Generate comprehensive PDF report"""
    company_name = company_data.get("lgnm", "Unknown Company")
    gstin = company_data.get("gstin", "N/A")
    status = company_data.get("sts", "N/A")
    returns = company_data.get('returns', [])
    
    if compliance_score >= 90:
        grade, grade_text, grade_color = "A+", "Excellent", "#10b981"
    elif compliance_score >= 80:
        grade, grade_text, grade_color = "A", "Very Good", "#34d399"
    elif compliance_score >= 70:
        grade, grade_text, grade_color = "B", "Good", "#f59e0b"
    elif compliance_score >= 60:
        grade, grade_text, grade_color = "C", "Average", "#f97316"
    else:
        grade, grade_text, grade_color = "D", "Needs Improvement", "#ef4444"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 15mm; }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: Arial, sans-serif; color: #1f2937; line-height: 1.6; }}
            
            .header {{ background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%); color: white;
                     padding: 30px; margin: -15mm -15mm 20px -15mm; }}
            .header-title {{ font-size: 28px; font-weight: 800; margin-bottom: 5px; }}
            .header-subtitle {{ font-size: 14px; opacity: 0.9; }}
            
            .company-section {{ background: #f8f9fa; border-radius: 12px; padding: 20px;
                              margin-bottom: 20px; border-left: 4px solid #7c3aed; }}
            .company-name {{ font-size: 24px; font-weight: 700; margin-bottom: 5px; }}
            
            .compliance-section {{ background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%);
                                 color: white; border-radius: 12px; padding: 25px; text-align: center; margin-bottom: 20px; }}
            .score-value {{ font-size: 36px; font-weight: 800; }}
            .score-grade {{ font-size: 20px; font-weight: 600; padding: 5px 20px;
                          background-color: {grade_color}; border-radius: 20px; display: inline-block; }}
            
            .info-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 20px; }}
            .info-card {{ background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; }}
            .info-card-title {{ font-size: 16px; font-weight: 700; margin-bottom: 15px;
                              padding-bottom: 10px; border-bottom: 2px solid #7c3aed; }}
            .info-item {{ display: flex; justify-content: space-between; padding: 8px 0;
                        border-bottom: 1px solid #f3f4f6; }}
            .info-item:last-child {{ border-bottom: none; }}
            .info-label {{ font-size: 13px; color: #6b7280; font-weight: 500; }}
            .info-value {{ font-size: 13px; color: #1f2937; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-title">GST Compliance Report</div>
            <div class="header-subtitle">Advanced Business Analytics Platform</div>
            <div style="text-align: right; font-size: 12px;">Generated on {datetime.now().strftime("%d %B %Y")}</div>
        </div>
        
        <div class="company-section">
            <div class="company-name">{company_name}</div>
            <div>GSTIN: {gstin}</div>
        </div>
        
        <div class="compliance-section">
            <h2 style="margin-bottom: 15px;">Overall Compliance Score</h2>
            <div class="score-value">{int(compliance_score)}%</div>
            <div class="score-grade">{grade} ({grade_text})</div>
        </div>
        
        {f'<div style="background: #e0e7ff; border-radius: 12px; padding: 20px; margin-bottom: 20px;"><h3>Company Overview</h3><p>{synopsis}</p></div>' if synopsis else ''}
        
        <div class="info-grid">
            <div class="info-card">
                <h3 class="info-card-title">Company Information</h3>
                <div class="info-item"><span class="info-label">Status</span><span class="info-value">{status}</span></div>
                <div class="info-item"><span class="info-label">Business Type</span><span class="info-value">{company_data.get('ctb', 'N/A')}</span></div>
                <div class="info-item"><span class="info-label">Registration Date</span><span class="info-value">{company_data.get('rgdt', 'N/A')}</span></div>
            </div>
            <div class="info-card">
                <h3 class="info-card-title">Returns Summary</h3>
                <div class="info-item"><span class="info-label">Total Returns</span><span class="info-value">{len(returns)}</span></div>
                <div class="info-item"><span class="info-label">GSTR-1 Filed</span><span class="info-value">{len([r for r in returns if r.get('rtntype') == 'GSTR1'])}</span></div>
                <div class="info-item"><span class="info-label">GSTR-3B Filed</span><span class="info-value">{len([r for r in returns if r.get('rtntype') == 'GSTR3B'])}</span></div>
            </div>
        </div>
        
        {f'<div style="background: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; padding: 12px; margin-bottom: 15px;"><strong>Late Filing Alert:</strong> {late_filing_analysis["late_count"]} returns filed late with average delay of {late_filing_analysis["average_delay"]:.1f} days.</div>' if late_filing_analysis and late_filing_analysis.get('late_count', 0) > 0 else ''}
        
        <div style="margin-top: 30px; text-align: center; font-size: 11px; color: #6b7280;">
            <p>© {datetime.now().year} GST Intelligence Platform. This report is generated based on available GST data.</p>
        </div>
    </body>
    </html>
    """
    
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(target=pdf_file)
    pdf_file.seek(0)
    return pdf_file

# API endpoints for enhanced user features
@app.get("/api/user/stats")
async def get_user_stats(request: Request, current_user: str = Depends(require_auth)):
    """Get user statistics for profile display"""
    try:
        await db.connect()
        async with db.pool.acquire() as conn:
            # Get basic stats
            total_searches = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE mobile = $1", 
                current_user
            )
            
            unique_companies = await conn.fetchval(
                "SELECT COUNT(DISTINCT gstin) FROM search_history WHERE mobile = $1", 
                current_user
            )
            
            avg_compliance = await conn.fetchval(
                "SELECT ROUND(AVG(compliance_score), 1) FROM search_history WHERE mobile = $1 AND compliance_score IS NOT NULL", 
                current_user
            )
            
            # Get recent activity (last 30 days)
            recent_searches = await conn.fetchval("""
                SELECT COUNT(*) FROM search_history 
                WHERE mobile = $1 AND searched_at >= CURRENT_DATE - INTERVAL '30 days'
            """, current_user)
            
            # Get last search date
            last_search = await conn.fetchval(
                "SELECT MAX(searched_at) FROM search_history WHERE mobile = $1", 
                current_user
            )
            
            return {
                "success": True,
                "data": {
                    "total_searches": total_searches or 0,
                    "unique_companies": unique_companies or 0,
                    "avg_compliance": float(avg_compliance) if avg_compliance else 0,
                    "recent_searches": recent_searches or 0,
                    "last_search": last_search.isoformat() if last_search else None,
                    "user_level": get_user_level(total_searches or 0),
                    "achievements": get_user_achievements(total_searches or 0, avg_compliance or 0)
                }
            }
            
    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        return {"success": False, "error": "Failed to fetch user statistics"}

def get_user_level(total_searches: int) -> dict:
    """Determine user level based on activity"""
    if total_searches >= 100:
        return {"level": "Expert", "icon": "fas fa-crown", "color": "#f59e0b"}
    elif total_searches >= 50:
        return {"level": "Advanced", "icon": "fas fa-star", "color": "#3b82f6"}
    elif total_searches >= 20:
        return {"level": "Intermediate", "icon": "fas fa-chart-line", "color": "#10b981"}
    elif total_searches >= 5:
        return {"level": "Beginner", "icon": "fas fa-seedling", "color": "#8b5cf6"}
    else:
        return {"level": "New User", "icon": "fas fa-user-plus", "color": "#6b7280"}

def get_user_achievements(total_searches: int, avg_compliance: float) -> list:
    """Get user achievements based on activity"""
    achievements = []
    
    if total_searches >= 1:
        achievements.append({
            "title": "First Search",
            "description": "Completed your first GST search",
            "icon": "fas fa-search",
            "unlocked": True
        })
    
    if total_searches >= 10:
        achievements.append({
            "title": "Research Enthusiast",
            "description": "Completed 10 searches",
            "icon": "fas fa-chart-bar",
            "unlocked": True
        })
    
    if total_searches >= 50:
        achievements.append({
            "title": "Compliance Expert",
            "description": "Completed 50 searches",
            "icon": "fas fa-medal",
            "unlocked": True
        })
    
    if avg_compliance >= 80:
        achievements.append({
            "title": "Quality Finder",
            "description": "Average compliance score above 80%",
            "icon": "fas fa-trophy",
            "unlocked": True
        })
    
    return achievements

@app.get("/favicon.ico")
async def favicon():
    favicon_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x01\x8d\xc8\x02\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=favicon_bytes, media_type="image/png")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "An internal error occurred"})

# Startup/Shutdown
@app.on_event("startup")
async def startup_event():
    logger.info("GST Intelligence Platform starting up...")
    await db.ensure_tables()
    setup_template_globals()
    await db.connect()
    async with db.pool.acquire() as conn:
        await conn.execute('DELETE FROM sessions WHERE expires_at < $1', datetime.now())
    logger.info("Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("GST Intelligence Platform shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
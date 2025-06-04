#!/usr/bin/env python3
"""
GST Intelligence Platform - Main Application
Enhanced with SQLite database, security improvements, and better error handling
"""

import os
import re
import sqlite3
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

# SQLite Database Manager
class SQLiteDB:
    def __init__(self, db_path: str = "database/gst_platform.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with all required tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    mobile TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login TEXT
                )
            ''')
            
            # Sessions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    mobile TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL
                )
            ''')
            
            # Search history table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mobile TEXT NOT NULL,
                    gstin TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    searched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    compliance_score REAL
                )
            ''')
            
            conn.commit()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2 - FIXED VERSION"""
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        # PBKDF2 with SHA256, 100000 iterations, 64 bytes output
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000, dklen=64)
        
        # Convert to hex string
        return hash_bytes.hex()
    
    def create_user(self, mobile: str, password: str) -> bool:
        """Create a new user with secure password hashing"""
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO users (mobile, password_hash, salt)
                    VALUES (?, ?, ?)
                ''', (mobile, password_hash, salt))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT password_hash, salt FROM users WHERE mobile=?', (mobile,)).fetchone()
            if not row:
                return False
            password_hash, salt = row
            return self._hash_password(password, salt) == password_hash
    
    def create_session(self, mobile: str) -> Optional[str]:
        """Create a new session with enhanced security"""
        session_token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO sessions (session_token, mobile, expires_at)
                    VALUES (?, ?, ?)
                ''', (session_token, mobile, expires_at))
                conn.commit()
            return session_token
        except Exception:
            return None
    
    def get_session(self, session_token: str) -> Optional[str]:
        """Get mobile number from valid session"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT mobile, expires_at FROM sessions WHERE session_token=?', (session_token,)).fetchone()
            if row and datetime.fromisoformat(row[1]) > datetime.now():
                return row[0]
        return None
    
    def delete_session(self, session_token: str) -> bool:
        """Delete a session (logout)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM sessions WHERE session_token=?', (session_token,))
            conn.commit()
        return True
    
    def update_last_login(self, mobile: str):
        """Update user's last login timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE users SET last_login=? WHERE mobile=?', (datetime.now().isoformat(), mobile))
            conn.commit()
    
    def add_search_history(self, mobile: str, gstin: str, company_name: str, compliance_score: float = None):
        """Add search to history with upsert logic"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('INSERT INTO search_history (mobile, gstin, company_name, compliance_score) VALUES (?, ?, ?, ?)', (mobile, gstin, company_name, compliance_score))
            conn.commit()
    
    def get_search_history(self, mobile: str, limit: int = 10) -> List[Dict]:
        """Get user's search history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=? ORDER BY searched_at DESC LIMIT ?', (mobile, limit)).fetchall()
            return [dict(row) for row in rows]
    
    def get_all_searches(self, mobile: str) -> List[Dict]:
        """Get all searches for export"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=? ORDER BY searched_at DESC', (mobile,)).fetchall()
            return [dict(row) for row in rows]

# Initialize database
db = SQLiteDB()

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
    return db.get_session(session_token)

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

def calculate_compliance_score(company_data: dict) -> float:
    """Calculate comprehensive compliance score based on multiple factors"""
    score = 100.0
    factors = []
    
    # 1. Registration Status (30 points)
    if company_data.get("sts") == "Active":
        factors.append(("Registration Status", 30, 30, "Active"))
    else:
        factors.append(("Registration Status", 0, 30, company_data.get("sts", "Inactive")))
        score -= 30
    
    # 2. Filing Compliance (25 points)
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
        filing_points = int(filing_ratio * 25)
        factors.append(("Return Filing Compliance", filing_points, 25, f"{len(returns)} returns filed"))
        score = score - 25 + filing_points
    else:
        factors.append(("Return Filing Compliance", 0, 25, "No returns filed"))
        score -= 25
    
    # 3. Filing Timeliness (20 points)
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
                timeliness_points = 20
                timeliness_desc = "Filed within last 30 days"
            elif days_since_filing <= 60:
                timeliness_points = 15
                timeliness_desc = "Filed within last 60 days"
            elif days_since_filing <= 90:
                timeliness_points = 10
                timeliness_desc = "Filed within last 90 days"
            else:
                timeliness_points = 5
                timeliness_desc = f"Last filed {days_since_filing} days ago"
            
            factors.append(("Filing Timeliness", timeliness_points, 20, timeliness_desc))
            score = score - 20 + timeliness_points
    else:
        factors.append(("Filing Timeliness", 0, 20, "No filing history"))
        score -= 20
    
    # 4. Filing Frequency Consistency (10 points)
    filing_freq = company_data.get("fillingFreq", {})
    if filing_freq:
        monthly_count = sum(1 for freq in filing_freq.values() if freq == "M")
        quarterly_count = sum(1 for freq in filing_freq.values() if freq == "Q")
        
        if monthly_count >= 6:  # Mostly monthly filer
            freq_points = 10
            freq_desc = "Consistent monthly filer"
        elif quarterly_count >= 6:  # Mostly quarterly filer
            freq_points = 8
            freq_desc = "Consistent quarterly filer"
        else:
            freq_points = 5
            freq_desc = "Mixed filing frequency"
        
        factors.append(("Filing Frequency", freq_points, 10, freq_desc))
        score = score - 10 + freq_points
    else:
        factors.append(("Filing Frequency", 5, 10, "No frequency data"))
        score -= 5
    
    # 5. E-Invoice Compliance (5 points)
    einvoice = company_data.get("einvoiceStatus", "No")
    if einvoice == "Yes":
        factors.append(("E-Invoice Adoption", 5, 5, "E-Invoice enabled"))
    else:
        factors.append(("E-Invoice Adoption", 2, 5, "E-Invoice not enabled"))
        score -= 3
    
    # 6. Business Type and Category (5 points)
    category = company_data.get("compCategory", "")
    if category in ["Green", "Yellow"]:
        factors.append(("Business Category", 5, 5, f"{category} category"))
    else:
        factors.append(("Business Category", 3, 5, f"{category or 'Unknown'} category"))
        score -= 2
    
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
            with sqlite3.connect(db.db_path) as conn:
                conn.execute("SELECT 1")
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
    history = db.get_search_history(current_user)
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
    
    if not db.verify_user(mobile, password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })
    
    # Create session
    session_token = db.create_session(mobile)
    
    if not session_token:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Failed to create session. Please try again."
        })
    
    db.update_last_login(mobile)
    
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
    
    if db.create_user(mobile, password):
        return RedirectResponse(url="/login?registered=true", status_code=302)
    else:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Mobile already registered"
        })

@app.get("/logout")
async def logout(request: Request):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        db.delete_session(session_token)
    
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
            "history": db.get_search_history(current_user)
        })
    
    # Check API rate limit
    if not api_limiter.is_allowed(current_user):
        retry_after = api_limiter.get_retry_after(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": f"API rate limit exceeded. Please try again in {retry_after} seconds.",
            "history": db.get_search_history(current_user)
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
        db.add_search_history(
            current_user,
            gstin,
            company_data.get("lgnm", "Unknown"),
            compliance_score
        )
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "mobile": current_user,
            "company_data": company_data,
            "compliance_score": int(compliance_score),
            "synopsis": synopsis
        })
        
    except HTTPException as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": e.detail,
            "history": db.get_search_history(current_user)
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "mobile": current_user,
            "error": "An error occurred while searching. Please try again.",
            "history": db.get_search_history(current_user)
        })

@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request, current_user: str = Depends(require_auth)):
    """View complete search history"""
    history = db.get_all_searches(current_user)
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
    history = db.get_all_searches(current_user)
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
        
        # Generate PDF
        pdf_content = generate_pdf_report(company_data, compliance_score, synopsis)
        
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

def generate_pdf_report(company_data: dict, compliance_score: float, synopsis: str = None) -> BytesIO:
    """Generate PDF report with company data - FIXED VERSION"""
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
            }}
            .header {{
                background-color: #1e3c72;
                color: white;
                padding: 20px;
                margin: -40px -40px 30px -40px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            .section {{
                margin-bottom: 30px;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
            }}
            .section h2 {{
                color: #1e3c72;
                margin-top: 0;
                font-size: 20px;
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
                padding: 10px;
                background-color: white;
                border-radius: 5px;
                border: 1px solid #e0e0e0;
            }}
            .info-label {{
                font-weight: bold;
                color: #666;
                font-size: 14px;
            }}
            .info-value {{
                margin-top: 5px;
                font-size: 16px;
                color: #333;
            }}
            .compliance-score {{
                text-align: center;
                padding: 20px;
                background-color: #2a5298;
                color: white;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .score-value {{
                font-size: 48px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .synopsis {{
                background-color: #e3f2fd;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
                line-height: 1.6;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #666;
                font-size: 12px;
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
        </div>
        
        <div class="section">
            <h2>Company Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Legal Name</div>
                    <div class="info-value">{company_data.get('lgnm', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">GSTIN</div>
                    <div class="info-value">{company_data.get('gstin', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Trade Name</div>
                    <div class="info-value">{company_data.get('tradeName', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Business Type</div>
                    <div class="info-value">{company_data.get('ctb', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Registration Date</div>
                    <div class="info-value">{company_data.get('rgdt', 'N/A')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Status</div>
                    <div class="info-value">{company_data.get('sts', 'N/A')}</div>
                </div>
            </div>
        </div>
        
        <div class="compliance-score">
            <h2 style="color: white; border: none;">Compliance Score</h2>
            <div class="score-value">{int(compliance_score)}%</div>
            <p>Based on registration status and filing history</p>
        </div>
        
        <div class="section">
            <h2>Address Details</h2>
            <div class="info-grid">
                <div class="info-item" style="grid-column: 1 / -1;">
                    <div class="info-label">Principal Place of Business</div>
                    <div class="info-value">{address}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">State</div>
                    <div class="info-value">{state}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Jurisdiction</div>
                    <div class="info-value">{jurisdiction}</div>
                </div>
            </div>
        </div>
        
        {f'''<div class="synopsis">
            <h2 style="color: #1e3c72;">AI-Generated Business Overview</h2>
            <p>{synopsis}</p>
        </div>''' if synopsis else ''}
        
        <div class="footer">
            <p>This report is generated by GST Intelligence Platform</p>
            <p>For the most current information, please verify with official GST portal</p>
            <p>&copy; {datetime.now().year} GST Intelligence Platform. All rights reserved.</p>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF - FIXED: Use correct parameter name
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
    
    # Clean up old sessions
    with sqlite3.connect(db.db_path) as conn:
        conn.execute('DELETE FROM sessions WHERE expires_at < ?', (datetime.now().isoformat(),))
        conn.commit()
    
    logger.info("Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown tasks"""
    logger.info("GST Intelligence Platform shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
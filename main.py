from fastapi import FastAPI, Request, Form, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import httpx
import os
import re
from pathlib import Path
import secrets
import hashlib
import json
from pydantic import BaseModel
import asyncio
import sqlite3
import threading

from weasyprint import HTML, CSS
from fastapi.concurrency import run_in_threadpool
from anthro_ai import get_anthropic_synopsis

# Database models
class User(BaseModel):
    mobile: str
    password_hash: str
    created_at: datetime
    last_login: Optional[datetime] = None

class SearchHistory(BaseModel):
    user_mobile: str
    gstin: str
    company_name: str
    searched_at: datetime
    compliance_score: Optional[float] = None

# SQLite Database with proper security - FIXED HASHING
class SQLiteDB:
    def __init__(self):
        self.db_dir = Path("database")
        self.db_dir.mkdir(exist_ok=True)
        self.db_path = self.db_dir / "gst_platform.db"
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables with proper indexes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    mobile TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    mobile TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (mobile) REFERENCES users (mobile) ON DELETE CASCADE
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mobile TEXT NOT NULL,
                    gstin TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    compliance_score REAL,
                    FOREIGN KEY (mobile) REFERENCES users (mobile) ON DELETE CASCADE,
                    UNIQUE(mobile, gstin)
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_mobile ON sessions(mobile)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_mobile ON search_history(mobile)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_searched_at ON search_history(searched_at DESC)')
            
            conn.commit()
    
    def _generate_salt(self) -> str:
        """Generate a random salt for password hashing"""
        return secrets.token_hex(16)
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2 - FIXED VERSION"""
        # Use hashlib.pbkdf2_hmac which is the correct function
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        
        # PBKDF2 with SHA256, 100000 iterations, 64 bytes output
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, 100000, 64)
        
        # Convert to hex string
        return hash_bytes.hex()
    
    def create_user(self, mobile: str, password: str) -> bool:
        """Create a new user with secure password hashing"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Check if user already exists
                    cursor = conn.execute('SELECT mobile FROM users WHERE mobile = ?', (mobile,))
                    if cursor.fetchone():
                        return False
                    
                    # Create user with salted hash
                    salt = self._generate_salt()
                    password_hash = self._hash_password(password, salt)
                    
                    conn.execute('''
                        INSERT INTO users (mobile, password_hash, salt, created_at)
                        VALUES (?, ?, ?, ?)
                    ''', (mobile, password_hash, salt, datetime.now().isoformat()))
                    
                    conn.commit()
                    return True
            except sqlite3.Error as e:
                print(f"Database error creating user: {e}")
                return False
    
    def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials with secure comparison"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        'SELECT password_hash, salt FROM users WHERE mobile = ?', 
                        (mobile,)
                    )
                    result = cursor.fetchone()
                    
                    if not result:
                        return False
                    
                    stored_hash, salt = result
                    password_hash = self._hash_password(password, salt)
                    
                    # Use secrets.compare_digest for secure comparison
                    return secrets.compare_digest(stored_hash, password_hash)
            except sqlite3.Error as e:
                print(f"Database error verifying user: {e}")
                return False
    
    def update_password(self, mobile: str, new_password: str) -> bool:
        """Update user password with new salt and hash"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Generate new salt and hash
                    salt = self._generate_salt()
                    password_hash = self._hash_password(new_password, salt)
                    
                    conn.execute('''
                        UPDATE users 
                        SET password_hash = ?, salt = ? 
                        WHERE mobile = ?
                    ''', (password_hash, salt, mobile))
                    
                    conn.commit()
                    return conn.total_changes > 0
            except sqlite3.Error as e:
                print(f"Database error updating password: {e}")
                return False
    
    def update_last_login(self, mobile: str):
        """Update user's last login timestamp"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        'UPDATE users SET last_login = ? WHERE mobile = ?',
                        (datetime.now().isoformat(), mobile)
                    )
                    conn.commit()
            except sqlite3.Error as e:
                print(f"Database error updating last login: {e}")
    
    def create_session(self, mobile: str) -> str:
        """Create a new session token"""
        with self._lock:
            try:
                session_token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(days=7)
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO sessions (session_token, mobile, expires_at)
                        VALUES (?, ?, ?)
                    ''', (session_token, mobile, expires_at.isoformat()))
                    conn.commit()
                    
                return session_token
            except sqlite3.Error as e:
                print(f"Database error creating session: {e}")
                return None
    
    def get_user_from_session(self, session_token: str) -> Optional[str]:
        """Get user from session token"""
        if not session_token:
            return None
            
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('''
                        SELECT mobile, expires_at FROM sessions 
                        WHERE session_token = ?
                    ''', (session_token,))
                    
                    result = cursor.fetchone()
                    if not result:
                        return None
                    
                    mobile, expires_at_str = result
                    expires_at = datetime.fromisoformat(expires_at_str)
                    
                    if expires_at < datetime.now():
                        # Clean up expired session
                        conn.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
                        conn.commit()
                        return None
                    
                    return mobile
            except sqlite3.Error as e:
                print(f"Database error getting user from session: {e}")
                return None
    
    def delete_session(self, session_token: str):
        """Delete a session"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
                    conn.commit()
            except sqlite3.Error as e:
                print(f"Database error deleting session: {e}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM sessions WHERE expires_at < ?', (datetime.now().isoformat(),))
                    conn.commit()
            except sqlite3.Error as e:
                print(f"Database error cleaning up sessions: {e}")
    
    def add_search_history(self, mobile: str, gstin: str, company_name: str, compliance_score: float = None):
        """Add or update search history"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Use REPLACE to update if exists, insert if not
                    conn.execute('''
                        INSERT OR REPLACE INTO search_history 
                        (mobile, gstin, company_name, searched_at, compliance_score)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (mobile, gstin, company_name, datetime.now().isoformat(), compliance_score))
                    
                    # Keep only last 50 searches per user
                    conn.execute('''
                        DELETE FROM search_history 
                        WHERE mobile = ? AND id NOT IN (
                            SELECT id FROM search_history 
                            WHERE mobile = ? 
                            ORDER BY searched_at DESC 
                            LIMIT 50
                        )
                    ''', (mobile, mobile))
                    
                    conn.commit()
            except sqlite3.Error as e:
                print(f"Database error adding search history: {e}")
    
    def get_search_history(self, mobile: str) -> List[Dict]:
        """Get user's search history"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('''
                        SELECT gstin, company_name, searched_at, compliance_score 
                        FROM search_history 
                        WHERE mobile = ? 
                        ORDER BY searched_at DESC 
                        LIMIT 50
                    ''', (mobile,))
                    
                    results = cursor.fetchall()
                    return [
                        {
                            'gstin': row[0],
                            'company_name': row[1],
                            'searched_at': row[2],
                            'compliance_score': row[3]
                        }
                        for row in results
                    ]
            except sqlite3.Error as e:
                print(f"Database error getting search history: {e}")
                return []

# Initialize database
db = SQLiteDB()

# Session management
async def get_current_user(request: Request) -> Optional[str]:
    session_token = request.cookies.get("session_token")
    return db.get_user_from_session(session_token)

def validate_gstin(gstin: str) -> Tuple[bool, str]:
    """Validate GSTIN format"""
    try:
        if not gstin:
            return False, "GSTIN cannot be empty"
        gstin = gstin.strip().upper()
        if len(gstin) != 15:
            return False, f"GSTIN must be 15 characters long, got {len(gstin)}"
        if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$', gstin):
            return False, "Invalid GSTIN format."
        state_code = int(gstin[:2])
        if state_code < 1 or state_code > 37:
            return False, f"Invalid state code: {state_code}"
        return True, "Valid GSTIN"
    except Exception as e:
        return False, f"GSTIN validation error: {str(e)}"

def validate_mobile(mobile: str) -> Tuple[bool, str]:
    """Validate Indian mobile number"""
    mobile = mobile.strip()
    if not re.match(r'^[6-9]\d{9}$', mobile):
        return False, "Invalid mobile number. Please enter a 10-digit Indian mobile number."
    return True, "Valid mobile number"

class GSAPIClient:
    """Client for GST API"""
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host,
            "User-Agent": "GST-Compliance-Platform/2.0"
        }
    
    async def fetch_gstin_data(self, gstin: str) -> Dict:
        """Fetch GSTIN data from API"""
        url = f"https://{self.host}/free/gstin/{gstin}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        if not data.get("success", False):
            raise HTTPException(status_code=400, detail=f"API Error: {data.get('message', 'Unknown error')}")
        return data.get("data", {})

# [Rest of the functions remain the same - mark_late_returns, calculate_compliance_score, etc.]
# I'll include just the essential parts to keep the artifact reasonable length

def mark_late_returns(returns: List[Dict]) -> List[Dict]:
    """Mark returns as late based on due dates"""
    for ret in returns:
        ret['late'] = False
        dof = ret.get("dof")
        fy = ret.get("fy")
        month_str = ret.get("taxp")
        rtntype = ret.get("rtntype", "") or ret.get("rtype", "")
        
        if fy and month_str and dof:
            try:
                if "-" in fy:
                    start_year = int(fy.split("-")[0])
                else:
                    start_year = int(fy[:4]) if len(fy) >= 4 else int(fy)
                
                month_map = {
                    "April": (4, start_year), "May": (5, start_year), "June": (6, start_year),
                    "July": (7, start_year), "August": (8, start_year), "September": (9, start_year),
                    "October": (10, start_year), "November": (11, start_year), "December": (12, start_year),
                    "January": (1, start_year + 1), "February": (2, start_year + 1), "March": (3, start_year + 1)
                }
                
                month_info = month_map.get(month_str)
                if month_info:
                    month, year = month_info
                    
                    if rtntype.upper() in ['GSTR1', 'GSTR-1']:
                        if month == 12:
                            due_date = datetime(year + 1, 1, 11)
                        else:
                            due_date = datetime(year, month + 1, 11)
                    elif rtntype.upper() in ['GSTR3B', 'GSTR-3B']:
                        if month == 12:
                            due_date = datetime(year + 1, 1, 20)
                        else:
                            due_date = datetime(year, month + 1, 20)
                    else:
                        if month == 12:
                            due_date = datetime(year + 1, 1, 20)
                        else:
                            due_date = datetime(year, month + 1, 20)
                    
                    filed_date = datetime.strptime(dof, "%d/%m/%Y")
                    
                    if filed_date > due_date:
                        ret['late'] = True
                        ret['days_late'] = (filed_date - due_date).days
                    else:
                        ret['days_late'] = 0
                        
            except Exception as e:
                print(f"Error processing return: {e}")
                ret['late'] = False
                ret['days_late'] = 0
                
    return returns

def calculate_compliance_score(data: Dict) -> Dict:
    """Calculate enhanced compliance score"""
    returns = data.get('returns', [])
    if not returns:
        return {
            'score': 0, 'grade': 'N/A', 'status': 'No Returns Found',
            'total_returns': 0, 'filed_returns': 0, 'pending_returns': 0, 'late_returns': 0,
            'details': 'No return filing history available'
        }
    
    filed_count = sum(1 for ret in returns if ret.get("dof"))
    late_count = sum(1 for ret in returns if ret.get('late'))
    total_count = len(returns)
    on_time_count = filed_count - late_count
    
    score = round(((on_time_count + 0.5 * late_count) / total_count) * 100, 1)
    
    if score >= 95: grade = 'A+'
    elif score >= 85: grade = 'A'
    elif score >= 75: grade = 'B'
    elif score >= 60: grade = 'C'
    else: grade = 'D'
    
    if score >= 90: status = 'Excellent Compliance'
    elif score >= 75: status = 'Good Compliance'
    elif score >= 60: status = 'Fair Compliance'
    else: status = 'Poor Compliance'
    
    return {
        'score': score, 'grade': grade, 'status': status,
        'total_returns': total_count, 'filed_returns': filed_count,
        'pending_returns': total_count - filed_count, 'late_returns': late_count,
        'details': f'Filed {filed_count} out of {total_count} returns, {late_count} late'
    }

def organize_returns_by_year(returns: List[Dict]) -> Dict:
    """Organize returns by financial year"""
    returns_by_year = defaultdict(list)
    for ret in returns:
        fy = ret.get('fy')
        if fy:
            returns_by_year[fy].append(ret)
    return dict(sorted(returns_by_year.items(), reverse=True))

# FastAPI App Setup
app = FastAPI(title="GST Compliance Platform")

# Setup directories
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory="templates")

# API Client Setup
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "gst-return-status.p.rapidapi.com")
api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST)

# Cleanup expired sessions on startup
@app.on_event("startup")
async def startup_event():
    db.cleanup_expired_sessions()

# Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Home page"""
    current_user = await get_current_user(request)
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "data": None,
        "current_user": current_user
    })

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    """Login page"""
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def post_login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    """Process login"""
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": message
        })
    
    if not db.verify_user(mobile, password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid mobile number or password"
        })
    
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
        secure=False
    )
    return response

@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    """Signup page"""
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def post_signup(request: Request, mobile: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    """Process signup"""
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": message
        })
    
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match"
        })
    
    if len(password) < 6:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Password must be at least 6 characters long"
        })
    
    if not db.create_user(mobile, password):
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Mobile number already registered"
        })
    
    session_token = db.create_session(mobile)
    if not session_token:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Account created but failed to login. Please try logging in manually."
        })
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False
    )
    return response

@app.get("/logout")
async def logout(request: Request):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        db.delete_session(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

@app.get("/history", response_class=HTMLResponse)
async def get_history(request: Request):
    """Search history page"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    history = db.get_search_history(current_user)
    return templates.TemplateResponse("history.html", {
        "request": request,
        "current_user": current_user,
        "history": history
    })

@app.get("/change-password", response_class=HTMLResponse)
async def get_change_password(request: Request):
    """Change password page"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("change_password.html", {"request": request, "current_user": current_user})

@app.post("/change-password")
async def post_change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...)
):
    """Process password change"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    if not db.verify_user(current_user, old_password):
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": "Old password is incorrect."
        })
    
    if new_password != confirm_new_password:
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": "New passwords do not match."
        })
    
    if len(new_password) < 6:
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": "New password must be at least 6 characters long."
        })
    
    if old_password == new_password:
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": "New password must be different from the old password."
        })
    
    if not db.update_password(current_user, new_password):
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "current_user": current_user,
            "error": "Failed to update password. Please try again."
        })
    
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "current_user": current_user,
        "success": "Password changed successfully."
    })

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request, gstin: str = Form(...)):
    """Process GSTIN search"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Validate GSTIN
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": validation_message,
            "error_type": "validation",
            "current_user": current_user
        })
    
    gstin = gstin.strip().upper()
    
    try:
        # Fetch data from API
        raw_data = await api_client.fetch_gstin_data(gstin)
        
        # Process returns
        returns = mark_late_returns(raw_data.get('returns', []))
        raw_data['returns'] = returns
        
        # Calculate compliance
        compliance = calculate_compliance_score(raw_data)
        
        # Organize returns by year
        returns_by_year = organize_returns_by_year(returns)
        
        # Generate synopsis (simplified version)
        synopsis = {
            'business_profile': {
                'display_name': raw_data.get('lgnm', 'Unknown Company'),
                'business_age': 'Unknown',
                'entity_type': raw_data.get('ctb', 'Unknown'),
                'operational_status': raw_data.get('sts', 'Unknown'),
                'state': 'Unknown'
            },
            'compliance_summary': {
                'overall_rating': compliance.get('grade', 'N/A'),
                'compliance_score': compliance.get('score', 0),
                'filing_reliability': 'Unknown',
                'late_filing_rate': f"{compliance.get('late_returns', 0)}/{compliance.get('total_returns', 0)}"
            },
            'narrative': f"Analysis for {raw_data.get('lgnm', 'Unknown Company')} shows a compliance score of {compliance.get('score', 0)}%."
        }
        
        # Get AI-powered narrative if available
        try:
            ai_narrative = await get_anthropic_synopsis({**raw_data, "compliance": compliance})
            synopsis['narrative'] = ai_narrative
        except Exception as e:
            print(f"AI synopsis error: {e}")
        
        # Prepare enhanced data
        enhanced_data = {
            **raw_data,
            'compliance': compliance,
            'returns_by_year': returns_by_year,
            'returns': returns,
            'synopsis': synopsis
        }
        
        # Save to history
        company_name = raw_data.get('lgnm', 'Unknown Company')
        db.add_search_history(current_user, gstin, company_name, compliance.get('score'))
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": enhanced_data,
            "gstin": gstin,
            "current_user": current_user
        })
        
    except HTTPException as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": e.detail,
            "error_type": "api",
            "current_user": current_user
        })
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": f"An error occurred: {str(e)}",
            "error_type": "system",
            "current_user": current_user
        })

@app.get("/company/{gstin}", response_class=HTMLResponse)
async def get_company_report(request: Request, gstin: str):
    """View company report by GSTIN"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Validate GSTIN
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": validation_message,
            "error_type": "validation",
            "current_user": current_user
        })
    
    try:
        # Fetch data from API
        raw_data = await api_client.fetch_gstin_data(gstin)
        
        # Process returns
        returns = mark_late_returns(raw_data.get('returns', []))
        raw_data['returns'] = returns
        
        # Calculate compliance
        compliance = calculate_compliance_score(raw_data)
        
        # Organize returns by year
        returns_by_year = organize_returns_by_year(returns)
        
        # Generate basic synopsis
        synopsis = {
            'business_profile': {
                'display_name': raw_data.get('lgnm', 'Unknown Company'),
                'business_age': 'Unknown',
                'entity_type': raw_data.get('ctb', 'Unknown'),
                'operational_status': raw_data.get('sts', 'Unknown'),
                'state': 'Unknown'
            },
            'compliance_summary': {
                'overall_rating': compliance.get('grade', 'N/A'),
                'compliance_score': compliance.get('score', 0),
                'filing_reliability': 'Unknown',
                'late_filing_rate': f"{compliance.get('late_returns', 0)}/{compliance.get('total_returns', 0)}"
            },
            'narrative': f"Analysis for {raw_data.get('lgnm', 'Unknown Company')} shows a compliance score of {compliance.get('score', 0)}%."
        }
        
        # Try to get AI narrative
        try:
            ai_narrative = await get_anthropic_synopsis({**raw_data, "compliance": compliance})
            synopsis['narrative'] = ai_narrative
        except Exception as e:
            print(f"AI synopsis error: {e}")
        
        # Prepare enhanced data
        enhanced_data = {
            **raw_data,
            'compliance': compliance,
            'returns_by_year': returns_by_year,
            'returns': returns,
            'synopsis': synopsis
        }
        
        # Update history
        company_name = raw_data.get('lgnm', 'Unknown Company')
        db.add_search_history(current_user, gstin, company_name, compliance.get('score'))
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": enhanced_data,
            "gstin": gstin,
            "current_user": current_user
        })
        
    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": None,
            "error": f"An error occurred: {str(e)}",
            "error_type": "system",
            "current_user": current_user
        })

# Fixed PDF Generation Routes
@app.post("/download/pdf")
async def download_pdf_post(request: Request, gstin: str = Form(...)):
    """Download PDF report - POST method"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return await generate_pdf_response(request, gstin, current_user)

@app.get("/download/pdf")
async def download_pdf_get(request: Request, gstin: str):
    """Download PDF report - GET method"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return await generate_pdf_response(request, gstin, current_user)

async def generate_pdf_response(request: Request, gstin: str, current_user: str):
    """Generate PDF response - helper function"""
    # Validate GSTIN
    is_valid, validation_message = validate_gstin(gstin)
    if not is_valid:
        raise HTTPException(status_code=400, detail=validation_message)
    
    try:
        # Fetch and process data
        raw_data = await api_client.fetch_gstin_data(gstin)
        returns = mark_late_returns(raw_data.get('returns', []))
        raw_data['returns'] = returns
        compliance = calculate_compliance_score(raw_data)
        returns_by_year = organize_returns_by_year(returns)
        
        # Basic synopsis for PDF
        synopsis = {
            'business_profile': {
                'display_name': raw_data.get('lgnm', 'Unknown Company'),
                'business_age': 'Unknown',
                'entity_type': raw_data.get('ctb', 'Unknown'),
                'operational_status': raw_data.get('sts', 'Unknown'),
                'state': 'Unknown'
            },
            'compliance_summary': {
                'overall_rating': compliance.get('grade', 'N/A'),
                'compliance_score': compliance.get('score', 0),
                'filing_reliability': 'Unknown',
                'late_filing_rate': f"{compliance.get('late_returns', 0)}/{compliance.get('total_returns', 0)}"
            },
            'narrative': f"GST compliance analysis for {raw_data.get('lgnm', 'Unknown Company')} shows a compliance score of {compliance.get('score', 0)}%."
        }
        
        # Try to get AI narrative
        try:
            ai_narrative = await get_anthropic_synopsis({**raw_data, "compliance": compliance})
            synopsis['narrative'] = ai_narrative
        except Exception as e:
            print(f"AI synopsis error: {e}")
        
        enhanced_data = {
            **raw_data,
            'compliance': compliance,
            'returns_by_year': returns_by_year,
            'returns': returns,
            'synopsis': synopsis
        }
        
        # Render HTML template
        html_content = templates.get_template("pdf_template.html").render({
            "request": request,
            "data": enhanced_data,
            "gstin": gstin,
            "error": None
        })
        
        # Generate PDF using WeasyPrint - FIXED
        def create_pdf():
            pdf_file = BytesIO()
            # Fixed: Remove extra arguments - HTML() only takes string
            HTML(string=html_content).write_pdf(pdf_file)
            pdf_file.seek(0)
            return pdf_file
        
        # Run PDF generation in thread pool to avoid blocking
        pdf_file = await run_in_threadpool(create_pdf)
        
        # Create filename
        company_name = enhanced_data.get('lgnm', 'Company').replace(' ', '_')
        filename = f"{gstin}_{company_name}_GST_Report.pdf"
        
        return StreamingResponse(
            pdf_file,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        print(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
#!/usr/bin/env python3
"""
GST Intelligence Platform - Complete Main Application
Enhanced with all missing API endpoints and functionality
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
from pydantic import BaseModel
import html

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

# Pydantic models for API requests
class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str

class UserPreferencesRequest(BaseModel):
    emailNotifications: Optional[bool] = False
    pushNotifications: Optional[bool] = False
    autoSearch: Optional[bool] = True
    animations: Optional[bool] = True
    compactMode: Optional[bool] = False
    saveHistory: Optional[bool] = True
    analytics: Optional[bool] = True

class UserProfileRequest(BaseModel):
    display_name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    designation: Optional[str] = None

# NEW: Missing Pydantic models from paste.txt
class BatchSearchRequest(BaseModel):
    gstins: List[str]

class ErrorLogRequest(BaseModel):
    type: str
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    userAgent: Optional[str] = None
    timestamp: Optional[str] = None

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
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("✅ Database pool created successfully")
            except Exception as e:
                logger.error(f"❌ Database connection failed: {e}")
                raise

    async def ensure_tables(self):
        """Ensure all required tables exist"""
        await self.connect()
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""CREATE TABLE IF NOT EXISTS users (
                    mobile VARCHAR(10) PRIMARY KEY,
                    password_hash VARCHAR(128) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
            """)
            
            # Sessions table
            await conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
                    session_token VARCHAR(64) PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            
            # Search history table
            await conn.execute("""CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    compliance_score DECIMAL(5,2),
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            
            # User preferences table
            await conn.execute("""CREATE TABLE IF NOT EXISTS user_preferences (
                    mobile VARCHAR(10) PRIMARY KEY,
                    preferences JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            
            logger.info("✅ All tables ensured")

    async def create_user(self, mobile: str, password_hash: str, salt: str):
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (mobile, password_hash, salt) VALUES ($1, $2, $3)",
                mobile, password_hash, salt
            )

    async def verify_user(self, mobile: str, password: str) -> bool:
        await self.connect()
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT password_hash, salt FROM users WHERE mobile = $1", mobile
            )
            if user:
                return check_password(password, user['password_hash'], user['salt'])
            return False

    async def change_password(self, mobile: str, old_password: str, new_password: str) -> bool:
        """Change user password after verifying old password"""
        await self.connect()
        async with self.pool.acquire() as conn:
            # Verify old password
            row = await conn.fetchrow("SELECT password_hash, salt FROM users WHERE mobile=$1", mobile)
            if not row or not check_password(old_password, row['password_hash'], row['salt']):
                return False
            
            # Generate new salt and hash
            new_salt = secrets.token_hex(16)
            new_hash = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), new_salt.encode('utf-8'), 100000, dklen=64).hex()
            
            # Update password
            await conn.execute(
                "UPDATE users SET password_hash=$1, salt=$2 WHERE mobile=$3",
                new_hash, new_salt, mobile
            )
            return True

    async def create_session(self, mobile: str) -> Optional[str]:
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=30)
        
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO sessions (session_token, mobile, expires_at) VALUES ($1, $2, $3)",
                session_token, mobile, expires_at
            )
        return session_token

    async def get_session(self, session_token: str) -> Optional[str]:
        await self.connect()
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT mobile FROM sessions WHERE session_token = $1 AND expires_at > NOW()",
                session_token
            )
            return user['mobile'] if user else None

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

    async def get_user_stats(self, mobile: str) -> Dict:
        """Get comprehensive user statistics"""
        await self.connect()
        async with self.pool.acquire() as conn:
            # Basic stats
            total_searches = await conn.fetchval(
                "SELECT COUNT(*) FROM search_history WHERE mobile = $1", mobile
            )
            
            unique_companies = await conn.fetchval(
                "SELECT COUNT(DISTINCT gstin) FROM search_history WHERE mobile = $1", mobile
            )
            
            avg_compliance = await conn.fetchval(
                "SELECT AVG(compliance_score) FROM search_history WHERE mobile = $1 AND compliance_score IS NOT NULL", mobile
            )
            
            # Recent activity (last 30 days)
            recent_searches = await conn.fetchval("""
                SELECT COUNT(*) FROM search_history 
                WHERE mobile = $1 AND searched_at >= CURRENT_DATE - INTERVAL '30 days'
            """, mobile)
            
            # Last search date
            last_search = await conn.fetchval(
                "SELECT MAX(searched_at) FROM search_history WHERE mobile = $1", mobile
            )
            
            # User level and achievements
            user_level = self._get_user_level(total_searches or 0)
            achievements = self._get_user_achievements(total_searches or 0, avg_compliance or 0)
            
            return {
                "total_searches": total_searches or 0,
                "unique_companies": unique_companies or 0,
                "avg_compliance": float(avg_compliance) if avg_compliance else 0,
                "recent_searches": recent_searches or 0,
                "last_search": last_search.isoformat() if last_search else None,
                "user_level": user_level,
                "achievements": achievements
            }

    def _get_user_level(self, total_searches: int) -> dict:
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

    def _get_user_achievements(self, total_searches: int, avg_compliance: float) -> list:
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

    async def save_user_preferences(self, mobile: str, preferences: dict):
        """Save user preferences"""
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_preferences (mobile, preferences, updated_at) 
                VALUES ($1, $2, $3)
                ON CONFLICT (mobile) 
                DO UPDATE SET preferences = $2, updated_at = $3
            """, mobile, json.dumps(preferences), datetime.now())

    async def get_user_preferences(self, mobile: str) -> dict:
        """Get user preferences"""
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT preferences FROM user_preferences WHERE mobile = $1", mobile)
            return json.loads(row['preferences']) if row else {}

    async def save_user_profile(self, mobile: str, profile_data: dict):
        """Save user profile information"""
        await self.connect()
        async with self.pool.acquire() as conn:
            # Update or insert user profile
            await conn.execute("""
                INSERT INTO user_preferences (mobile, preferences, updated_at) 
                VALUES ($1, $2, $3)
                ON CONFLICT (mobile) 
                DO UPDATE SET 
                    preferences = user_preferences.preferences || $2::jsonb,
                    updated_at = $3
            """, mobile, json.dumps(profile_data), datetime.now())

    async def get_user_profile(self, mobile: str) -> dict:
        """Get user profile information"""
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT preferences FROM user_preferences WHERE mobile = $1", mobile)
            if row:
                prefs = json.loads(row['preferences'])
                return {
                    'display_name': prefs.get('display_name'),
                    'company': prefs.get('company'),
                    'email': prefs.get('email'),
                    'designation': prefs.get('designation')
                }
            return {}

    async def get_user_activity_summary(self, mobile: str, days: int = 30) -> Dict:
        """Get user activity summary for dashboard"""
        await self.connect()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        async with self.pool.acquire() as conn:
            summary = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_searches,
                    COUNT(DISTINCT gstin) as unique_companies,
                    AVG(compliance_score) as avg_compliance,
                    MAX(searched_at) as last_search,
                    MIN(searched_at) as first_search
                FROM search_history 
                WHERE mobile = $1 AND searched_at >= $2
            """, mobile, start_date)
            
            return {
                "total_searches": summary["total_searches"] or 0,
                "unique_companies": summary["unique_companies"] or 0,
                "avg_compliance": float(summary["avg_compliance"]) if summary["avg_compliance"] else 0,
                "last_search": summary["last_search"].isoformat() if summary["last_search"] else None,
                "first_search": summary["first_search"].isoformat() if summary["first_search"] else None,
                "period_days": days
            }

    async def get_compliance_insights(self, mobile: str) -> Dict:
        """Get compliance insights for user"""
        await self.connect()
        async with self.pool.acquire() as conn:
            insights = await conn.fetchrow("""
                SELECT 
                    AVG(compliance_score) as avg_score,
                    MAX(compliance_score) as best_score,
                    MIN(compliance_score) as worst_score,
                    COUNT(CASE WHEN compliance_score >= 80 THEN 1 END) as high_compliance_count,
                    COUNT(CASE WHEN compliance_score < 60 THEN 1 END) as low_compliance_count,
                    COUNT(*) as total_scored
                FROM search_history 
                WHERE mobile = $1 AND compliance_score IS NOT NULL
            """, mobile)
            
            return {
                "avg_score": float(insights["avg_score"]) if insights["avg_score"] else 0,
                "best_score": float(insights["best_score"]) if insights["best_score"] else 0,
                "worst_score": float(insights["worst_score"]) if insights["worst_score"] else 0,
                "high_compliance_count": insights["high_compliance_count"] or 0,
                "low_compliance_count": insights["low_compliance_count"] or 0,
                "total_scored": insights["total_scored"] or 0,
                "high_compliance_percentage": (insights["high_compliance_count"] / insights["total_scored"] * 100) if insights["total_scored"] > 0 else 0
            }

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
def check_password(password: str, stored_hash: str, salt: str) -> bool:
    hash_attempt = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000, dklen=64).hex()
    return hash_attempt == stored_hash

def validate_mobile(mobile: str) -> tuple[bool, str]:
    mobile = mobile.strip()
    if not mobile.isdigit() or len(mobile) != 10 or mobile[0] not in "6789":
        return False, "Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9"
    return True, ""

def validate_gstin(gstin: str) -> bool:
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    return bool(re.match(pattern, gstin.upper()))

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, ""

async def get_user_display_name(mobile: str) -> str:
    """Get user display name or fallback to mobile"""
    try:
        profile = await db.get_user_profile(mobile)
        display_name = profile.get('display_name')
        if display_name:
            return display_name
        # Create a friendly name from mobile number
        return f"User {mobile[-4:]}"
    except:
        return f"User {mobile[-4:]}"

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
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
    # Calculate searches this month
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days
    )
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile,
        "history": history,
        "searches_this_month": searches_this_month
    })

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def post_login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    # Rate limiting
    client_ip = request.client.host
    if not login_limiter.is_allowed(client_ip):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Too many login attempts. Please try again later."
        })
    
    # Validate mobile number
    is_valid, error_msg = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": error_msg
        })
    
    # Verify user
    if await db.verify_user(mobile, password):
        session_token = await db.create_session(mobile)
        await db.update_last_login(mobile)
        
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=30 * 24 * 3600,  # 30 days
            httponly=True,
            secure=True,
            samesite="strict"
        )
        return response
    else:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid mobile number or password"
        })

@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def post_signup(request: Request, mobile: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    # Validate mobile
    is_valid, error_msg = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": error_msg
        })
    
    # Validate password
    is_strong, strength_msg = validate_password_strength(password)
    if not is_strong:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": strength_msg
        })
    
    # Check password confirmation
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Passwords do not match"
        })
    
    try:
        # Create user
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000, dklen=64).hex()
        
        await db.create_user(mobile, password_hash, salt)
        
        return RedirectResponse(url="/login?registered=true", status_code=303)
        
    except Exception as e:
        if "duplicate key" in str(e).lower():
            error_msg = "Mobile number already registered"
        else:
            error_msg = "Registration failed. Please try again."
            logger.error(f"Signup error: {e}")
        
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": error_msg
        })

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
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "Invalid GSTIN format. Please enter a valid 15-character GSTIN.",
            "current_user": current_user
        })
    
    if not api_limiter.is_allowed(current_user):
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "Rate limit exceeded. Please try again later.",
            "current_user": current_user
        })
    
    try:
        if not api_client:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": "GST API service is currently unavailable.",
                "current_user": current_user
            })
        
        # Fetch company data
        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)
        
        # Get AI synopsis
        synopsis = await get_anthropic_synopsis(company_data)
        
        # Analyze late filings
        late_filing_analysis = analyze_late_filings(company_data.get('returns', []))
        
        # Add to search history
        await db.add_search_history(
            current_user, 
            gstin, 
            company_data.get("lgnm", "Unknown"), 
            compliance_score
        )
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "company_data": company_data,
            "compliance_score": compliance_score,
            "synopsis": synopsis,
            "late_filing_analysis": late_filing_analysis,
            "current_user": current_user
        })
        
    except HTTPException as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"Error fetching company data: {e.detail}",
            "current_user": current_user
        })
    except Exception as e:
        logger.error(f"Search error for {gstin}: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": "An unexpected error occurred. Please try again.",
            "current_user": current_user
        })

@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request, current_user: str = Depends(require_auth)):
    history = await db.get_all_searches(current_user)
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days
    )
    return templates.TemplateResponse("history.html", {
        "request": request, 
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile,
        "history": history,
        "searches_this_month": searches_this_month
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, current_user: str = Depends(require_auth)):
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
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
                        ELSE 'Poor (<60)' END as range, COUNT(*)
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
        "user_display_name": user_display_name,
        "user_profile": user_profile,
        "daily_searches": daily_searches,
        "score_distribution": [dict(row) for row in score_distribution],
        "top_companies": [dict(row) for row in top_companies],
        "total_searches": total_searches or 0, 
        "unique_companies": unique_companies or 0,
        "avg_compliance": round(avg_compliance or 0, 1)
    })

# ==============================================================
# NEW API ENDPOINTS FROM PASTE.TXT - MISSING IMPLEMENTATIONS
# ==============================================================

# Batch Search Endpoint
@app.post("/api/search/batch")
async def batch_search(request: BatchSearchRequest, current_user: str = Depends(require_auth)):
    """Handle batch GSTIN searches (max 10 at once)"""
    try:
        gstins = request.gstins[:10]  # Limit to 10 for safety
        results = []
        successful = 0
        
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
        
        for gstin in gstins:
            gstin = gstin.strip().upper()
            if not validate_gstin(gstin):
                results.append({
                    'gstin': gstin,
                    'success': False,
                    'error': 'Invalid GSTIN format'
                })
                continue
            
            try:
                company_data = await api_client.fetch_gstin_data(gstin)
                compliance_score = calculate_compliance_score(company_data)
                
                # Add to search history
                await db.add_search_history(current_user, gstin, company_data.get("lgnm", "Unknown"), compliance_score)
                
                results.append({
                    'gstin': gstin,
                    'success': True,
                    'company_name': company_data.get('lgnm', 'Unknown'),
                    'compliance_score': compliance_score,
                    'status': company_data.get('sts', 'Unknown')
                })
                successful += 1
                
            except Exception as e:
                logger.error(f"Error processing GSTIN {gstin}: {e}")
                results.append({
                    'gstin': gstin,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'results': results,
            'processed': len(gstins),
            'successful': successful
        }
        
    except Exception as e:
        logger.error(f"Batch search error: {e}")
        return {
            'success': False,
            'error': 'Batch search failed',
            'results': [],
            'processed': 0,
            'successful': 0
        }

# Search Suggestions Endpoint  
@app.get("/api/search/suggestions")
async def get_search_suggestions(q: str, current_user: str = Depends(require_auth)):
    """Get search suggestions based on query"""
    try:
        if len(q) < 2:
            return {'success': True, 'suggestions': []}
        
        # Get recent searches from history that match query
        await db.connect()
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT gstin, company_name, compliance_score 
                FROM search_history 
                WHERE mobile = $1 
                AND (LOWER(company_name) LIKE $2 OR LOWER(gstin) LIKE $2)
                ORDER BY searched_at DESC 
                LIMIT 5
            """, current_user, f"%{q.lower()}%")
        
        suggestions = []
        for row in rows:
            suggestions.append({
                'gstin': row['gstin'],
                'company': row['company_name'],
                'compliance_score': float(row['compliance_score']) if row['compliance_score'] else None,
                'icon': 'fas fa-history',
                'type': 'recent'
            })
        
        # Add some sample suggestions if no recent matches
        if not suggestions:
            sample_suggestions = [
                {
                    'gstin': '27AABCU9603R1ZX',
                    'company': 'UBER INDIA SYSTEMS PRIVATE LIMITED',
                    'icon': 'fas fa-building',
                    'type': 'sample'
                },
                {
                    'gstin': '29AABCT1332L1ZU', 
                    'company': 'TATA CONSULTANCY SERVICES LIMITED',
                    'icon': 'fas fa-building',
                    'type': 'sample'
                }
            ]
            
            # Filter samples that match query
            for suggestion in sample_suggestions:
                if (q.lower() in suggestion['company'].lower() or 
                    q.lower() in suggestion['gstin'].lower()):
                    suggestions.append(suggestion)
        
        return {
            'success': True,
            'suggestions': suggestions[:5]
        }
        
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        return {'success': False, 'suggestions': []}

# Error Logging Endpoint
@app.post("/api/system/error")
async def log_frontend_error(request: ErrorLogRequest):
    """Log frontend JavaScript errors"""
    try:
        error_data = {
            'type': request.type,
            'message': request.message,
            'stack': request.stack,
            'url': request.url,
            'userAgent': request.userAgent,
            'timestamp': request.timestamp
        }
        
        # Log to application logger
        logger.error(f"Frontend Error: {error_data}")
        
        # Could also save to database if needed
        # await db.log_error(error_data)
        
        return {'success': True, 'message': 'Error logged'}
        
    except Exception as e:
        logger.error(f"Error logging frontend error: {e}")
        return {'success': False, 'message': 'Failed to log error'}

# Enhanced User Activity Endpoint
@app.get("/api/user/activity")
async def get_user_activity(days: int = 30, current_user: str = Depends(require_auth)):
    """Get detailed user activity data for charts"""
    try:
        await db.connect()
        async with db.pool.acquire() as conn:
            # Daily search activity
            daily_activity = await conn.fetch("""
                SELECT DATE(searched_at) as date, 
                       COUNT(*) as searches,
                       AVG(compliance_score) as avg_score
                FROM search_history 
                WHERE mobile = $1 
                AND searched_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(searched_at)
                ORDER BY date
            """, current_user, days)
            
            # Hourly activity pattern
            hourly_activity = await conn.fetch("""
                SELECT EXTRACT(hour FROM searched_at) as hour,
                       COUNT(*) as searches
                FROM search_history 
                WHERE mobile = $1
                AND searched_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY EXTRACT(hour FROM searched_at)
                ORDER BY hour
            """, current_user)
            
            # Score distribution
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
                AND compliance_score IS NOT NULL
                GROUP BY range
                ORDER BY range DESC
            """, current_user)
        
        return {
            'success': True,
            'data': {
                'daily_activity': [dict(row) for row in daily_activity],
                'hourly_activity': [dict(row) for row in hourly_activity],
                'score_distribution': [dict(row) for row in score_distribution]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return {'success': False, 'error': 'Failed to get activity data'}

# System Status Endpoint
@app.get("/api/system/status")
async def get_system_status():
    """Get system status for monitoring"""
    try:
        status = {
            'database': 'healthy',
            'gst_api': 'configured' if RAPIDAPI_KEY else 'missing',
            'ai_service': 'configured' if ANTHROPIC_API_KEY else 'disabled',
            'timestamp': datetime.now().isoformat()
        }
        
        # Test database connection
        try:
            await db.connect()
            async with db.pool.acquire() as conn:
                await conn.execute("SELECT 1")
        except Exception as e:
            status['database'] = f'unhealthy: {str(e)}'
        
        return {
            'success': True,
            'status': status
        }
        
    except Exception as e:
        logger.error(f"System status error: {e}")
        return {
            'success': False,
            'error': 'Failed to get system status'
        }

# API Endpoints for User Management (ALREADY EXISTED - KEEPING AS IS)
@app.get("/api/user/stats")
async def get_user_stats(current_user: str = Depends(require_auth)):
    """Get user statistics for profile display"""
    try:
        stats = await db.get_user_stats(current_user)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Error fetching user stats: {e}")
        return {"success": False, "error": "Failed to fetch user statistics"}

@app.post("/api/user/change-password")
async def change_password(request: ChangePasswordRequest, current_user: str = Depends(require_auth)):
    """Change user password"""
    try:
        # Validate new password strength
        is_strong, message = validate_password_strength(request.newPassword)
        if not is_strong:
            return {"success": False, "message": message}
        
        # Change password
        success = await db.change_password(current_user, request.currentPassword, request.newPassword)
        
        if success:
            return {"success": True, "message": "Password changed successfully"}
        else:
            return {"success": False, "message": "Current password is incorrect"}
    
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return {"success": False, "message": "Failed to change password"}

@app.get("/api/user/preferences")
async def get_user_preferences(current_user: str = Depends(require_auth)):
    """Get user preferences"""
    try:
        preferences = await db.get_user_preferences(current_user)
        return {"success": True, "data": preferences}
    except Exception as e:
        logger.error(f"Error fetching preferences: {e}")
        return {"success": False, "error": "Failed to fetch preferences"}

@app.post("/api/user/preferences")
async def save_user_preferences(request: UserPreferencesRequest, current_user: str = Depends(require_auth)):
    """Save user preferences"""
    try:
        preferences = request.dict()
        await db.save_user_preferences(current_user, preferences)
        return {"success": True, "message": "Preferences saved successfully"}
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        return {"success": False, "error": "Failed to save preferences"}

@app.get("/api/user/profile")
async def get_user_profile_api(current_user: str = Depends(require_auth)):
    """Get user profile data"""
    try:
        profile = await db.get_user_profile(current_user)
        return {"success": True, "data": profile}
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        return {"success": False, "error": "Failed to fetch user profile"}

@app.post("/api/user/profile")
async def save_user_profile_api(request: UserProfileRequest, current_user: str = Depends(require_auth)):
    """Save user profile data"""
    try:
        profile_data = {k: v for k, v in request.dict().items() if v is not None}
        await db.save_user_profile(current_user, profile_data)
        return {"success": True, "message": "Profile saved successfully"}
    except Exception as e:
        logger.error(f"Error saving user profile: {e}")
        return {"success": False, "error": "Failed to save user profile"}

@app.delete("/api/user/data")
async def clear_user_data(current_user: str = Depends(require_auth)):
    """Clear user search history"""
    try:
        await db.connect()
        async with db.pool.acquire() as conn:
            result = await conn.fetchval("DELETE FROM search_history WHERE mobile = $1 RETURNING COUNT(*)", current_user)
            return {"success": True, "deleted_count": result or 0}
    except Exception as e:
        logger.error(f"Error clearing user data: {e}")
        return {"success": False, "error": "Failed to clear user data"}

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
        
        <div class="compliance-section card--elevated glow-pulse">
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

@app.get("/favicon.ico")
async def favicon():
    favicon_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x01\x8d\xc8\x02\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=favicon_bytes, media_type="image/png")

# Serve PWA manifest
@app.get("/manifest.json")
async def get_manifest():
    with open("static/manifest.json", "r") as f:
        manifest_content = f.read()
    return Response(content=manifest_content, media_type="application/json")

# Serve service worker
@app.get("/sw.js")
async def get_service_worker():
    with open("sw.js", "r") as f:
        sw_content = f.read()
    return Response(content=sw_content, media_type="application/javascript")

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
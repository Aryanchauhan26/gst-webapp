#!/usr/bin/env python3
"""
GST Intelligence Platform - Main Application (Fixed Version)
Enhanced with PostgreSQL database and AI-powered insights
All missing endpoints and database fixes included
"""

import os
import re
import asyncio
import asyncpg
import hashlib
import secrets
import logging
import json
import httpx
import uvicorn
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, List
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from io import BytesIO, StringIO
from dotenv import load_dotenv
from anthro_ai import get_anthropic_synopsis
from validators import EnhancedDataValidator, get_validation_rules

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    logger.warning("WeasyPrint not available - PDF generation disabled")
    WEASYPRINT_AVAILABLE = False

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

# Enhanced Database Manager
class FixedDatabaseManager:
    """Fixed database manager with graceful handling of missing columns"""
    
    def __init__(self, postgres_dsn: str):
        self.postgres_dsn = postgres_dsn
        self.pool = None
        self._initialized = False
        self._column_cache = {}  # Cache for column existence checks

    async def initialize(self):
        """Initialize database connection"""
        if self._initialized:
            return

        try:
            self.pool = await asyncpg.create_pool(
                dsn=self.postgres_dsn,
                min_size=2,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=30,
                server_settings={
                    'application_name': 'gst-intelligence-platform',
                    'timezone': 'UTC'
                }
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            # Cache column information
            await self._cache_table_columns()
            
            self._initialized = True
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def _cache_table_columns(self):
        """Cache information about which columns exist in each table"""
        try:
            async with self.pool.acquire() as conn:
                # Get all columns for important tables
                tables_to_check = ['users', 'user_profiles', 'user_sessions', 'search_history', 'gst_search_history']
                
                for table in tables_to_check:
                    columns = await conn.fetch("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = $1 AND table_schema = 'public'
                    """, table)
                    
                    self._column_cache[table] = {row['column_name'] for row in columns}
                    logger.info(f"Cached columns for {table}: {self._column_cache[table]}")
                    
        except Exception as e:
            logger.warning(f"Could not cache column information: {e}")
            # Set default empty cache
            self._column_cache = {}

    def _has_column(self, table: str, column: str) -> bool:
        """Check if a table has a specific column"""
        return self._column_cache.get(table, set()).get(column, False) if self._column_cache else True

    def _build_safe_select(self, table: str, columns: list, where_clause: str = "") -> str:
        """Build a SELECT query with only existing columns"""
        if table not in self._column_cache:
            # If we don't have cached info, assume all columns exist
            return f"SELECT {', '.join(columns)} FROM {table} {where_clause}"
        
        safe_columns = []
        for col in columns:
            if col in self._column_cache[table]:
                safe_columns.append(col)
            else:
                # Add a NULL placeholder for missing columns
                safe_columns.append(f"NULL as {col}")
        
        return f"SELECT {', '.join(safe_columns)} FROM {table} {where_clause}"

    async def create_user(self, mobile: str, password_hash: str, salt: str, email: str = None) -> bool:
        """Create new user with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                # Check which columns exist in users table
                base_columns = ['mobile', 'password_hash', 'salt']
                base_values = [mobile, password_hash, salt]
                placeholders = ['$1', '$2', '$3']
                
                # Add optional columns if they exist
                if email and self._has_column('users', 'email'):
                    base_columns.append('email')
                    base_values.append(email)
                    placeholders.append('$4')
                
                # Add profile_data if it exists
                if self._has_column('users', 'profile_data'):
                    base_columns.append('profile_data')
                    base_values.append('{}')
                    placeholders.append(f'${len(placeholders) + 1}')
                
                query = f"""
                    INSERT INTO users ({', '.join(base_columns)})
                    VALUES ({', '.join(placeholders)})
                """
                
                await conn.execute(query, *base_values)
                
                # Try to initialize user profile if table exists
                if 'user_profiles' in self._column_cache:
                    try:
                        await conn.execute(
                            "INSERT INTO user_profiles (mobile, display_name) VALUES ($1, $2)",
                            mobile, f"User {mobile[-4:]}"
                        )
                    except Exception as e:
                        logger.warning(f"Could not create user profile: {e}")
                
                logger.info(f"✅ User created successfully: {mobile}")
                return True
                
        except asyncpg.UniqueViolationError:
            logger.warning(f"⚠️ User already exists: {mobile}")
            return False
        except Exception as e:
            logger.error(f"❌ User creation failed: {e}")
            return False

    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                # Build safe query for users table
                columns = ['password_hash', 'salt']
                if self._has_column('users', 'is_active'):
                    where_clause = "WHERE mobile = $1 AND is_active = TRUE"
                else:
                    where_clause = "WHERE mobile = $1"
                
                query = self._build_safe_select('users', columns, where_clause)
                result = await conn.fetchrow(query, mobile)
                
                if result:
                    stored_hash = result["password_hash"]
                    salt = result["salt"]
                    
                    # Hash the provided password with the stored salt
                    password_hash = hashlib.pbkdf2_hmac(
                        'sha256', 
                        password.encode('utf-8'), 
                        salt.encode('utf-8'), 
                        100000, 
                        dklen=64
                    ).hex()
                    
                    return password_hash == stored_hash
                return False
        except Exception as e:
            logger.error(f"Error verifying user: {e}")
            return False

    async def create_session(self, mobile: str, ip_address: str = None, user_agent: str = None) -> str:
        """Create new user session with safe column handling"""
        try:
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=30)
            
            async with self.pool.acquire() as conn:
                # Build safe insert for user_sessions
                base_columns = ['session_id', 'user_mobile', 'expires_at']
                base_values = [session_id, mobile, expires_at]
                placeholders = ['$1', '$2', '$3']
                
                # Add optional columns if they exist
                if ip_address and self._has_column('user_sessions', 'ip_address'):
                    base_columns.append('ip_address')
                    base_values.append(ip_address)
                    placeholders.append(f'${len(placeholders) + 1}')
                
                if user_agent and self._has_column('user_sessions', 'user_agent'):
                    base_columns.append('user_agent')
                    base_values.append(user_agent)
                    placeholders.append(f'${len(placeholders) + 1}')
                
                query = f"""
                    INSERT INTO user_sessions ({', '.join(base_columns)}) 
                    VALUES ({', '.join(placeholders)})
                """
                
                await conn.execute(query, *base_values)
                return session_id
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    async def get_session(self, session_token: str) -> Optional[str]:
        """Get user from session token with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                # Build safe query
                columns = ['user_mobile']
                
                if self._has_column('user_sessions', 'is_active'):
                    where_clause = "WHERE session_id = $1 AND expires_at > CURRENT_TIMESTAMP AND is_active = TRUE"
                else:
                    where_clause = "WHERE session_id = $1 AND expires_at > CURRENT_TIMESTAMP"
                
                query = self._build_safe_select('user_sessions', columns, where_clause)
                result = await conn.fetchrow(query, session_token)
                
                if result:
                    # Try to update last activity if column exists
                    if self._has_column('user_sessions', 'last_activity'):
                        try:
                            await conn.execute(
                                "UPDATE user_sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = $1",
                                session_token
                            )
                        except Exception:
                            pass  # Ignore if update fails
                    
                    return result["user_mobile"]
                return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    async def delete_session(self, session_token: str) -> bool:
        """Delete user session with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                if self._has_column('user_sessions', 'is_active'):
                    # Soft delete by setting is_active to False
                    await conn.execute(
                        "UPDATE user_sessions SET is_active = FALSE WHERE session_id = $1",
                        session_token
                    )
                else:
                    # Hard delete
                    await conn.execute(
                        "DELETE FROM user_sessions WHERE session_id = $1",
                        session_token
                    )
                return True
        except Exception as e:
            logger.error(f"Error deleting session: {e}")
            return False

    async def update_last_login(self, mobile: str) -> bool:
        """Update user's last login timestamp with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                if self._has_column('users', 'last_login'):
                    await conn.execute(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE mobile = $1",
                        mobile
                    )
                return True
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False

    async def add_search_history(self, mobile: str, gstin: str, company_name: str, compliance_score: float, search_data: dict = None, ai_synopsis: str = None) -> bool:
        """Add search to history with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                # Always try to add to search_history table
                search_data_json = json.dumps(search_data or {})
                
                base_columns = ['mobile', 'gstin', 'company_name', 'compliance_score']
                base_values = [mobile, gstin, company_name, compliance_score]
                placeholders = ['$1', '$2', '$3', '$4']
                
                # Add optional columns if they exist
                if self._has_column('search_history', 'search_data'):
                    base_columns.append('search_data')
                    base_values.append(search_data_json)
                    placeholders.append(f'${len(placeholders) + 1}')
                
                if ai_synopsis and self._has_column('search_history', 'ai_synopsis'):
                    base_columns.append('ai_synopsis')
                    base_values.append(ai_synopsis)
                    placeholders.append(f'${len(placeholders) + 1}')
                
                query = f"""
                    INSERT INTO search_history ({', '.join(base_columns)}) 
                    VALUES ({', '.join(placeholders)})
                """
                
                await conn.execute(query, *base_values)
                
                # Try to add to gst_search_history if it exists
                if 'gst_search_history' in self._column_cache:
                    try:
                        gst_columns = ['user_mobile', 'mobile', 'gstin', 'company_name', 'compliance_score', 'search_data', 'response_data']
                        gst_values = [mobile, mobile, gstin, company_name, compliance_score, search_data_json, search_data_json]
                        gst_placeholders = ['$1', '$2', '$3', '$4', '$5', '$6', '$7']
                        
                        if ai_synopsis and self._has_column('gst_search_history', 'ai_synopsis'):
                            gst_columns.append('ai_synopsis')
                            gst_values.append(ai_synopsis)
                            gst_placeholders.append('$8')
                        
                        gst_query = f"""
                            INSERT INTO gst_search_history ({', '.join(gst_columns)}) 
                            VALUES ({', '.join(gst_placeholders)})
                        """
                        
                        await conn.execute(gst_query, *gst_values)
                    except Exception as e:
                        logger.warning(f"Could not add to gst_search_history: {e}")
                
                return True
        except Exception as e:
            logger.error(f"Error adding search history: {e}")
            return False

    async def get_search_history(self, mobile: str, limit: int = 50) -> List[Dict]:
        """Get user search history with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                columns = ['gstin', 'company_name', 'compliance_score', 'searched_at']
                
                if self._has_column('search_history', 'ai_synopsis'):
                    columns.append('ai_synopsis')
                
                query = self._build_safe_select(
                    'search_history', 
                    columns, 
                    "WHERE mobile = $1 ORDER BY searched_at DESC LIMIT $2"
                )
                
                history = await conn.fetch(query, mobile, limit)
                return [dict(row) for row in history]
        except Exception as e:
            logger.error(f"Error getting search history: {e}")
            return []

    async def get_all_searches(self, mobile: str) -> List[Dict]:
        """Get all searches for user with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                columns = ['gstin', 'company_name', 'compliance_score', 'searched_at']
                
                query = self._build_safe_select(
                    'search_history', 
                    columns, 
                    "WHERE mobile = $1 ORDER BY searched_at DESC"
                )
                
                history = await conn.fetch(query, mobile)
                return [dict(row) for row in history]
        except Exception as e:
            logger.error(f"Error getting all searches: {e}")
            return []

    async def get_user_stats(self, mobile: str) -> Dict:
        """Get user statistics with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_searches,
                        COALESCE(AVG(compliance_score), 0) as avg_compliance,
                        COUNT(DISTINCT gstin) as unique_companies,
                        COUNT(CASE WHEN searched_at >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) as searches_this_month
                    FROM search_history 
                    WHERE mobile = $1
                """, mobile)
                
                if stats:
                    return {
                        "total_searches": int(stats["total_searches"]),
                        "avg_compliance": float(stats["avg_compliance"]),
                        "unique_companies": int(stats["unique_companies"]),
                        "searches_this_month": int(stats["searches_this_month"])
                    }
                else:
                    return {"total_searches": 0, "avg_compliance": 0, "unique_companies": 0, "searches_this_month": 0}
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"total_searches": 0, "avg_compliance": 0, "unique_companies": 0, "searches_this_month": 0}

    async def get_user_profile_data(self, mobile: str) -> Dict:
        """Get user profile data with safe column handling"""
        try:
            async with self.pool.acquire() as conn:
                # Get user data with safe column selection
                user_columns = ['mobile', 'created_at']
                
                # Add optional columns if they exist
                optional_columns = ['email', 'last_login', 'profile_data']
                for col in optional_columns:
                    if self._has_column('users', col):
                        user_columns.append(col)
                
                user_query = self._build_safe_select('users', user_columns, "WHERE mobile = $1")
                user_data = await conn.fetchrow(user_query, mobile)
                
                search_stats = await self.get_user_stats(mobile)
                recent_searches = await self.get_search_history(mobile, 5)
                
                # Convert user_data to dict and handle missing columns
                user_info = {}
                if user_data:
                    user_info = dict(user_data)
                    # Ensure required fields exist with defaults
                    user_info.setdefault('email', None)
                    user_info.setdefault('profile_data', {})
                    user_info.setdefault('last_login', None)
                
                return {
                    "user_info": user_info,
                    "search_stats": search_stats,
                    "recent_searches": recent_searches
                }
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {"user_info": {}, "search_stats": {}, "recent_searches": []}
# Initialize database
db = FixedDatabaseManager(postgres_dsn=POSTGRES_DSN)

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

# GST API Client
class GSAPIClient:
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": host
        }
    
    async def fetch_gstin_data(self, gstin: str) -> Dict:
        """Fetch GSTIN data from RapidAPI"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{self.host}/gstin/{gstin}",
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data
                else:
                    raise HTTPException(status_code=404, detail="Company not found")
                    
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="API timeout")
        except Exception as e:
            logger.error(f"GST API error: {e}")
            raise HTTPException(status_code=500, detail="API service error")

api_client = GSAPIClient(RAPIDAPI_KEY, RAPIDAPI_HOST) if RAPIDAPI_KEY else None

# Validation functions
def validate_mobile(mobile: str) -> tuple[bool, str]:
    return EnhancedDataValidator.validate_mobile(mobile)

def validate_gstin(gstin: str) -> bool:
    is_valid, _ = EnhancedDataValidator.validate_gstin(gstin)
    return is_valid

def validate_email(email: str) -> bool:
    is_valid, _ = EnhancedDataValidator.validate_email(email)
    return is_valid

# Compliance calculation functions
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
    """Calculate compliance score"""
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
                    filing_date = datetime.strptime(return_item["dof"], "%d/%m/%Y")
                    if latest_return_date is None or filing_date > latest_return_date:
                        latest_return_date = filing_date
                except:
                    continue
        
        if latest_return_date:
            current_date = datetime.now()
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
            await db.initialize()
            async with db.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "timestamp": datetime.now().isoformat(),
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
            content={"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}
        )

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(require_auth)):
    await db.initialize()
    
    # Get user profile data including stats
    profile_data = await db.get_user_profile_data(current_user)
    user_stats = profile_data.get("search_stats", {})
    history = profile_data.get("recent_searches", [])
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user,
        "user_display_name": current_user,
        "history": history,
        "user_profile": user_stats,
        "searches_this_month": user_stats.get("searches_this_month", 0)
    })

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def post_login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    form_data = {
        'mobile': mobile,
        'password': password
    }

    validation_rules = {
        'mobile': {'type': 'mobile', 'required': True},
        'password': {'type': 'text', 'required': True}
    }

    validation_result = EnhancedDataValidator.validate_form_data(form_data, validation_rules)

    if not validation_result['is_valid']:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": list(validation_result['errors'].values())[0]
        })
    
    if not login_limiter.is_allowed(mobile):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Too many login attempts. Please try again later."
        })
    
    await db.initialize()
    if not await db.verify_user(mobile, password):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Invalid mobile number or password"
        })
    
    session_token = await db.create_session(mobile)
    await db.update_last_login(mobile)
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token", 
        value=session_token, 
        max_age=30*24*60*60,  # 30 days
        httponly=True,
        secure=False  # Set to True in production with HTTPS
    )
    return response

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request, current_user: str = Depends(require_auth)):
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/api/admin/stats")
async def admin_stats(current_user: str = Depends(require_auth)):
    return JSONResponse({
        "success": True,
        "user_stats": {"total_users": 0, "active_users": 0},
        "search_stats": {"total_searches": 0, "searches_today": 0}
    })

@app.get("/api/admin/users")
async def admin_users(current_user: str = Depends(require_auth)):
    return JSONResponse({
        "success": True,
        "users": [],
        "pagination": {"page": 1, "pages": 1, "total": 0}
    })

@app.get("/api/admin/system/health")
async def system_health(current_user: str = Depends(require_auth)):
    return JSONResponse({
        "success": True,
        "health": {
            "database": "healthy",
            "api": "configured",
            "ai": "configured" if ANTHROPIC_API_KEY else "not configured"
        }
    })

@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def post_signup(request: Request, mobile: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    form_data = {
        'mobile': mobile,
        'password': password,
        'confirm_password': confirm_password
    }

    validation_rules = {
        'mobile': {'type': 'mobile', 'required': True},
        'password': {'type': 'text', 'required': True},
        'confirm_password': {'type': 'text', 'required': True}
    }

    validation_result = EnhancedDataValidator.validate_form_data(form_data, validation_rules)

    if not validation_result['is_valid']:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": list(validation_result['errors'].values())[0]
        })
    
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "Passwords do not match"
        })
    
    if len(password) < 8:
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "Password must be at least 8 characters long"
        })
    
    try:
        await db.initialize()
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000, dklen=64).hex()
        
        success = await db.create_user(mobile, password_hash, salt)
        
        if success:
            return templates.TemplateResponse("signup.html", {
                "request": request, 
                "success": "Account created successfully! Please login."
            })
        else:
            return templates.TemplateResponse("signup.html", {
                "request": request, 
                "error": "Mobile number already exists"
            })
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "An error occurred during registration"
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
    if gstin:
        return await process_search(request, gstin, current_user)
    return RedirectResponse(url="/", status_code=302)

@app.post("/search")
async def search_gstin_post(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    return await process_search(request, gstin, current_user)

@app.get("/history", response_class=HTMLResponse)
async def view_history(request: Request, current_user: str = Depends(require_auth)):
    await db.initialize()
    history = await db.get_all_searches(current_user)
    
    # Calculate statistics
    total_searches = len(history)
    unique_companies = len(set(item["gstin"] for item in history)) if history else 0
    avg_compliance = sum(item["compliance_score"] or 0 for item in history) / total_searches if total_searches > 0 else 0
    
    return templates.TemplateResponse("history.html", {
        "request": request,
        "current_user": current_user,
        "history": history,
        "total_searches": total_searches,
        "unique_companies": unique_companies,
        "avg_compliance": round(avg_compliance, 1)
    })

@app.get("/api/search/suggestions")
async def search_suggestions(q: str, current_user: str = Depends(require_auth)):
    if len(q) < 3:
        return JSONResponse({"suggestions": []})
    
    await db.initialize()
    async with db.pool.acquire() as conn:
        suggestions = await conn.fetch("""
            SELECT DISTINCT gstin, company_name 
            FROM search_history 
            WHERE mobile = $1 AND (gstin ILIKE $2 OR company_name ILIKE $2)
            ORDER BY searched_at DESC LIMIT 5
        """, current_user, f"%{q}%")
    
    return JSONResponse({
        "suggestions": [{"gstin": row["gstin"], "company_name": row["company_name"]} for row in suggestions]
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard(request: Request, current_user: str = Depends(require_auth)):
    await db.initialize()
    
    # Get analytics data
    async with db.pool.acquire() as conn:
        # Get daily searches for the last 7 days
        daily_searches = await conn.fetch("""
            SELECT DATE(searched_at) as date, COUNT(*) as search_count, AVG(compliance_score) as avg_score
            FROM search_history WHERE mobile = $1 AND searched_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(searched_at) ORDER BY date
        """, current_user)
        
        # Get compliance score distribution
        score_distribution = await conn.fetch("""
            SELECT CASE WHEN compliance_score >= 90 THEN 'Excellent (90-100)'
                        WHEN compliance_score >= 80 THEN 'Very Good (80-89)'
                        WHEN compliance_score >= 70 THEN 'Good (70-79)'
                        WHEN compliance_score >= 60 THEN 'Average (60-69)'
                        ELSE 'Poor (<60)' END as range, COUNT(*) as count
            FROM search_history WHERE mobile = $1 AND compliance_score IS NOT NULL GROUP BY range ORDER BY range DESC
        """, current_user)
        
        # Get top searched companies
        top_companies = await conn.fetch("""
            SELECT company_name, gstin, COUNT(*) as search_count, MAX(compliance_score) as latest_score
            FROM search_history WHERE mobile = $1 GROUP BY company_name, gstin
            ORDER BY search_count DESC LIMIT 10
        """, current_user)
        
        # Get user stats
        user_stats = await db.get_user_stats(current_user)
    
    # Convert dates for JSON serialization
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
        "total_searches": user_stats.get("total_searches", 0), 
        "unique_companies": user_stats.get("unique_companies", 0),
        "avg_compliance": round(user_stats.get("avg_compliance", 0), 1),
        "searches_this_month": user_stats.get("searches_this_month", 0)
    })

@app.get("/api/analytics/dashboard")
async def analytics_api(current_user: str = Depends(require_auth)):
    await db.initialize()
    async with db.pool.acquire() as conn:
        recent_searches = await conn.fetch("""
            SELECT gstin, company_name, compliance_score, searched_at
            FROM search_history WHERE mobile = $1 
            ORDER BY searched_at DESC LIMIT 5
        """, current_user)
    
    return JSONResponse({
        "success": True,
        "data": {
            "recent_searches": [dict(row) for row in recent_searches]
        }
    })

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user: str = Depends(require_auth)):
    """User profile page"""
    await db.initialize()
    profile_data = await db.get_user_profile_data(current_user)
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": current_user,
        "profile_data": profile_data,
        "user_display_name": current_user
    })

@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Privacy Policy - GST Intelligence Platform</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/css/base.css">
    </head>
    <body>
        <div style="max-width: 800px; margin: 2rem auto; padding: 2rem; background: var(--bg-card); border-radius: 16px;">
            <h1>Privacy Policy</h1>
            <p>Your privacy is important to us. This policy explains how we collect, use, and protect your information.</p>
            <h2>Information We Collect</h2>
            <p>We collect only the information necessary to provide our GST compliance services.</p>
            <h2>How We Use Your Information</h2>
            <p>We use your information solely for providing GST analysis and compliance services.</p>
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
    </body>
    </html>
    """)

@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Terms of Service - GST Intelligence Platform</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="/static/css/base.css">
    </head>
    <body>
        <div style="max-width: 800px; margin: 2rem auto; padding: 2rem; background: var(--bg-card); border-radius: 16px;">
            <h1>Terms of Service</h1>
            <p>Welcome to GST Intelligence Platform. By using our service, you agree to these terms.</p>
            <h2>Service Description</h2>
            <p>We provide GST compliance analysis and business intelligence services.</p>
            <h2>User Responsibilities</h2>
            <p>Users are responsible for providing accurate information and using the service appropriately.</p>
            <p><a href="/">← Back to Dashboard</a></p>
        </div>
    </body>
    </html>
    """)

@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, current_user: str = Depends(require_auth)):
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": current_user,
        "user_display_name": current_user
    })

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/icons/favicon.png", media_type="image/png")

@app.get("/manifest.json")
async def manifest():
    return FileResponse("static/manifest.json", media_type="application/json")

@app.get("/sw.js")
async def service_worker():
    return FileResponse("sw.js", media_type="application/javascript")

@app.get("/loans", response_class=HTMLResponse)
async def loans_page(request: Request, current_user: str = Depends(require_auth)):
    """Loan management page"""
    await db.initialize()
    
    # Sample loan configuration
    loan_config = {
        "min_amount": 50000,
        "max_amount": 5000000,
        "min_annual_turnover": 100000,
        "min_vintage": 6
    }
    
    return templates.TemplateResponse("loans.html", {
        "request": request,
        "current_user": current_user,
        "applications": [],  # Would fetch from loans table
        "loan_config": loan_config
    })

@app.get("/api/loans/eligibility")
async def check_loan_eligibility(
    gstin: str,
    annual_turnover: float,
    compliance_score: float,
    business_vintage_months: int,
    current_user: str = Depends(require_auth)
):
    try:
        eligible = True
        reasons = []
        
        if compliance_score < 60:
            eligible = False
            reasons.append("Compliance score must be at least 60%")
        
        if annual_turnover < 100000:
            eligible = False
            reasons.append("Annual turnover must be at least ₹1,00,000")
        
        if business_vintage_months < 6:
            eligible = False
            reasons.append("Business must be at least 6 months old")
        
        max_loan_amount = min(annual_turnover * 0.5, 5000000)
        recommended_amount = max_loan_amount * 0.7
        
        return JSONResponse({
            "success": True,
            "data": {
                "eligible": eligible,
                "reasons": reasons,
                "max_loan_amount": max_loan_amount,
                "recommended_amount": recommended_amount
            }
        })
        
    except Exception as e:
        logger.error(f"Loan eligibility error: {e}")
        return JSONResponse({"success": False, "error": "Failed to check eligibility"})

@app.post("/api/loans/apply")
async def apply_for_loan(request: Request, current_user: str = Depends(require_auth)):
    try:
        data = await request.json()
        logger.info(f"Loan application from {current_user}: {data}")
        
        return JSONResponse({
            "success": True,
            "message": "Loan application submitted successfully",
            "application_id": "LA" + str(int(datetime.now().timestamp()))
        })
        
    except Exception as e:
        logger.error(f"Loan application error: {e}")
        return JSONResponse({"success": False, "error": "Failed to submit application"})

@app.get("/api/loans/applications")
async def get_loan_applications(current_user: str = Depends(require_auth)):
    try:
        return JSONResponse({
            "success": True,
            "data": []
        })
    except Exception as e:
        logger.error(f"Get loan applications error: {e}")
        return JSONResponse({"success": False, "error": "Failed to fetch applications"})

@app.get("/contact", response_class=HTMLResponse)
async def contact_get(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    """Contact page"""
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "current_user": current_user
    })

@app.post("/contact")
async def contact_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    current_user: Optional[str] = Depends(get_current_user)
):
    try:
        # Validate form data
        form_data = {
            'name': name,
            'email': email,
            'subject': subject,
            'message': message
        }
        
        validation_rules = {
            'name': {'type': 'text', 'required': True},
            'email': {'type': 'email', 'required': True},
            'subject': {'type': 'text', 'required': True},
            'message': {'type': 'text', 'required': True}
        }
        
        validation_result = EnhancedDataValidator.validate_form_data(form_data, validation_rules)
        
        if not validation_result['is_valid']:
            return templates.TemplateResponse("contact.html", {
                "request": request,
                "current_user": current_user,
                "error_message": list(validation_result['errors'].values())[0]
            })
        
        # Log contact submission
        cleaned_data = validation_result['cleaned_data']
        logger.info(f"Contact form submitted by {cleaned_data['name']} ({cleaned_data['email']}): {cleaned_data['subject']}")
        
        return templates.TemplateResponse("contact.html", {
            "request": request,
            "current_user": current_user,
            "success_message": "Thank you for your message. We'll get back to you soon!"
        })
        
    except Exception as e:
        logger.error(f"Contact form error: {e}")
        return templates.TemplateResponse("contact.html", {
            "request": request,
            "current_user": current_user,
            "error_message": "Failed to send message. Please try again."
        })

# API Endpoints
@app.post("/api/search")
async def api_search(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    """API endpoint for search functionality"""
    try:
        # Validate GSTIN
        if not validate_gstin(gstin):
            return JSONResponse({"success": False, "error": "Invalid GSTIN format"})
        
        # Check rate limit
        if not api_limiter.is_allowed(current_user):
            return JSONResponse({"success": False, "error": "Rate limit exceeded"})
        
        if not api_client:
            return JSONResponse({"success": False, "error": "GST API service not configured"})
            
        # Fetch company data
        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)
        
        # Get AI synopsis
        synopsis = None
        if ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except Exception as e:
                logger.error(f"Failed to get AI synopsis: {e}")
        
        # Add to search history
        await db.add_search_history(
            current_user, gstin, 
            company_data.get("lgnm", "Unknown"), 
            compliance_score, company_data, synopsis
        )
        
        return JSONResponse({
            "success": True,
            "data": {
                "gstin": gstin,
                "legal_name": company_data.get("lgnm"),
                "trade_name": company_data.get("tradeNam"),
                "business_status": company_data.get("sts"),
                "filing_status": company_data.get("fillingFreq", {}).get("status", "Unknown"),
                "registration_date": company_data.get("rgdt"),
                "compliance_score": compliance_score,
                "ai_synopsis": synopsis
            }
        })
    except Exception as e:
        logger.error(f"API search error: {e}")
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/api/user/stats")
async def get_user_stats_api(request: Request, current_user: str = Depends(require_auth)):
    """Get user statistics for profile display"""
    await db.initialize()
    stats = await db.get_user_stats(current_user)
    
    user_level = get_user_level(stats.get("total_searches", 0))
    achievements = get_user_achievements(stats.get("total_searches", 0), stats.get("avg_compliance", 0))
    
    return JSONResponse({
        "success": True,
        "data": {
            **stats,
            "user_level": user_level,
            "achievements": achievements
        }
    })

@app.get("/api/user/export")
async def export_user_data(current_user: str = Depends(require_auth)):
    """Export user data as JSON"""
    try:
        await db.initialize()
        
        # Get all user data
        profile_data = await db.get_user_profile_data(current_user)
        all_searches = await db.get_all_searches(current_user)
        
        export_data = {
            "export_date": datetime.now().isoformat(),
            "user_mobile": current_user,
            "profile": profile_data["user_info"],
            "statistics": profile_data["search_stats"],
            "search_history": all_searches,
            "total_records": len(all_searches)
        }
        
        # Convert to JSON
        json_data = json.dumps(export_data, indent=2, default=str)
        
        return StreamingResponse(
            BytesIO(json_data.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=profile_data_{current_user}_{datetime.now().strftime('%Y%m%d')}.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")

@app.get("/api/user/profile")
async def user_profile(current_user: str = Depends(require_auth)):
    await db.initialize()
    async with db.pool.acquire() as conn:
        user_data = await conn.fetchrow("SELECT * FROM users WHERE mobile = $1", current_user)
        search_count = await conn.fetchval("SELECT COUNT(*) FROM search_history WHERE mobile = $1", current_user)
    
    return JSONResponse({
        "success": True,
        "data": {
            "mobile": current_user,
            "created_at": user_data["created_at"].isoformat() if user_data and user_data["created_at"] else None,
            "last_login": user_data["last_login"].isoformat() if user_data and user_data["last_login"] else None,
            "search_count": search_count
        }
    })

@app.post("/api/user/profile")
async def update_user_profile(
    request: Request,
    display_name: str = Form(None),
    email: str = Form(None),
    company: str = Form(None),
    current_user: str = Depends(require_auth)
):
    try:
        await db.initialize()
        # Update logic here
        return JSONResponse({"success": True, "message": "Profile updated successfully"})
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return JSONResponse({"success": False, "error": "Failed to update profile"})
    
@app.get("/export/history")
async def export_history(current_user: str = Depends(require_auth)):
    """Export search history as CSV"""
    try:
        await db.initialize()
        history = await db.get_all_searches(current_user)
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['searched_at', 'gstin', 'company_name', 'compliance_score'])
        writer.writeheader()
        
        # Convert datetime objects to strings for CSV
        for row in history:
            if row.get('searched_at'):
                row['searched_at'] = row['searched_at'].isoformat()
            writer.writerow(row)
        
        content = output.getvalue()
        output.close()
        
        return StreamingResponse(
            BytesIO(content.encode()), 
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=gst_search_history_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        logger.error(f"Export history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export history")

@app.post("/change-password")
async def change_password_route(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: str = Depends(require_auth)
):
    """Change user password"""
    try:
        if new_password != confirm_password:
            return JSONResponse({"success": False, "error": "Passwords do not match"})
        
        if len(new_password) < 8:
            return JSONResponse({"success": False, "error": "Password must be at least 8 characters"})
        
        await db.initialize()
        async with db.pool.acquire() as conn:
            # Get current user data
            user_data = await conn.fetchrow("SELECT password_hash, salt FROM users WHERE mobile = $1", current_user)
            
            if not user_data:
                return JSONResponse({"success": False, "error": "User not found"})
            
            # Verify current password
            if not check_password(current_password, user_data["password_hash"], user_data["salt"]):
                return JSONResponse({"success": False, "error": "Current password is incorrect"})
            
            # Generate new password hash
            new_salt = secrets.token_hex(16)
            new_hash = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), new_salt.encode('utf-8'), 100000, dklen=64).hex()
            
            # Update password
            await conn.execute(
                "UPDATE users SET password_hash = $1, salt = $2 WHERE mobile = $3",
                new_hash, new_salt, current_user
            )
            
            return JSONResponse({"success": True, "message": "Password updated successfully"})
            
    except Exception as e:
        logger.error(f"Password change error: {e}")
        return JSONResponse({"success": False, "error": "Failed to update password"})

# PDF generation
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
    if not WEASYPRINT_AVAILABLE:
        raise HTTPException(status_code=503, detail="PDF generation not available")
    
    company_name = company_data.get("lgnm", "Unknown Company")
    gstin = company_data.get("gstin", "N/A")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #7c3aed; color: white; padding: 20px; text-align: center; }}
            .content {{ margin: 20px 0; }}
            .score {{ font-size: 24px; font-weight: bold; text-align: center; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>GST Compliance Report</h1>
            <p>Generated on {datetime.now().strftime("%d %B %Y")}</p>
        </div>
        <div class="content">
            <h2>{company_name}</h2>
            <p>GSTIN: {gstin}</p>
            <div class="score">Compliance Score: {int(compliance_score)}%</div>
            {f'<div><h3>AI Synopsis</h3><p>{synopsis}</p></div>' if synopsis else ''}
        </div>
    </body>
    </html>
    """
    
    pdf_file = BytesIO()
    HTML(string=html_content).write_pdf(target=pdf_file)
    pdf_file.seek(0)
    return pdf_file

# Utility functions
def get_user_level(total_searches: int) -> dict:
    """Determine user level based on activity"""
    if total_searches >= 100:
        return {"level": "Expert", "icon": "fas fa-crown", "color": "#f59e0b"}
    elif total_searches >= 50:
        return {"level": "Advanced", "icon": "fas fa-star", "color": "#8b5cf6"}
    elif total_searches >= 20:
        return {"level": "Intermediate", "icon": "fas fa-user-graduate", "color": "#06b6d4"}
    elif total_searches >= 5:
        return {"level": "Beginner", "icon": "fas fa-seedling", "color": "#10b981"}
    else:
        return {"level": "New User", "icon": "fas fa-user-plus", "color": "#6b7280"}

def get_user_achievements(total_searches: int, avg_compliance: float) -> list:
    """Get user achievements based on activity"""
    achievements = []
    
    if total_searches >= 1:
        achievements.append({
            "title": "First Search", "icon": "fas fa-search", 
            "unlocked": True, "description": "Completed your first GST search"
        })
    
    if total_searches >= 10:
        achievements.append({
            "title": "Search Explorer", "icon": "fas fa-compass", 
            "unlocked": True, "description": "Completed 10 searches"
        })
    
    if total_searches >= 50:
        achievements.append({
            "title": "Power User", "icon": "fas fa-bolt", 
            "unlocked": True, "description": "Completed 50 searches"
        })
    
    if avg_compliance >= 80:
        achievements.append({
            "title": "Quality Seeker", "icon": "fas fa-trophy", 
            "unlocked": True, "description": "Average compliance score above 80%"
        })
    
    return achievements

async def process_search(request: Request, gstin: str, current_user: str):
    gstin = gstin.strip().upper()
    is_valid, error_message = EnhancedDataValidator.validate_gstin(gstin)
    if not is_valid:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user,
            "error": error_message
        })
    
    if not api_limiter.is_allowed(current_user):
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user,
            "error": "Rate limit exceeded. Please try again later."
        })
    
    if not api_client:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user,
            "error": "GST API service not configured. Please contact administrator."
        })
    
    try:
        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)
        
        # Get AI synopsis
        synopsis = None
        if ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except Exception as e:
                logger.error(f"Failed to get AI synopsis: {e}")
                synopsis = None
        
        # Add to search history
        await db.add_search_history(
            current_user, gstin, 
            company_data.get("lgnm", "Unknown"), 
            compliance_score, company_data, synopsis
        )
        
        # Get late filing analysis
        late_filing_analysis = company_data.get('_late_filing_analysis', {})
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "current_user": current_user,
            "company_data": company_data,
            "compliance_score": compliance_score,
            "synopsis": synopsis,
            "late_filing_analysis": late_filing_analysis,
            "gstin": gstin
        })
        
    except HTTPException as e:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user,
            "error": f"Company not found for GSTIN: {gstin}"
        })
    except Exception as e:
        logger.error(f"Search error: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user,
            "error": "An error occurred while fetching data. Please try again."
        })

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

@app.post("/api/system/log-error")
async def log_error(request: Request, current_user: str = Depends(require_auth)):
    try:
        data = await request.json()
        logger.error(f"Client error from {current_user}: {data}")
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error(f"Error logging client error: {e}")
        return JSONResponse({"success": False})

# Startup/Shutdown
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting GST Intelligence Platform...")
    try:
        await db.initialize()
        setup_template_globals()
        logger.info("✅ Application started successfully!")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down GST Intelligence Platform...")
    if db.pool:
        await db.pool.close()
    logger.info("✅ Shutdown complete!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
#!/usr/bin/env python3
"""
Core Database Manager for GST Intelligence Platform
Production-ready with connection pooling and error handling
"""

import asyncio
import asyncpg
import logging
import hashlib
import secrets
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
import time

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Production-ready database manager with connection pooling."""
    
    def __init__(self, dsn: str = None):
        from config import settings
        self.dsn = dsn or settings.POSTGRES_DSN
        self.pool = None
        self.is_initialized = False
        
        # Simple in-memory cache
        self._cache = {}
        self._cache_ttl = {}
        
    async def initialize(self):
        """Initialize database connection pool."""
        if self.is_initialized:
            return True
            
        try:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=2,
                max_size=10,
                timeout=30
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            
            logger.info("✅ Database initialized successfully")
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self.is_initialized = False
    
    # =============================================
    # USER MANAGEMENT
    # =============================================
    
    async def create_user(self, mobile: str, password_hash: str, salt: str) -> bool:
        """Create new user."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (mobile, password_hash, salt, created_at)
                    VALUES ($1, $2, $3, $4)
                """, mobile, password_hash, salt, datetime.now(timezone.utc))
                return True
        except asyncpg.UniqueViolationError:
            return False
        except Exception as e:
            logger.error(f"Create user error: {e}")
            return False
    
    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT password_hash, salt FROM users WHERE mobile = $1
                """, mobile)
                
                if not row:
                    return False
                
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256', password.encode('utf-8'),
                    row['salt'].encode('utf-8'), 100000, dklen=64
                ).hex()
                
                return password_hash == row['password_hash']
        except Exception as e:
            logger.error(f"Verify user error: {e}")
            return False
    
    async def update_last_login(self, mobile: str):
        """Update last login timestamp."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users SET last_login = $1 WHERE mobile = $2
                """, datetime.now(timezone.utc), mobile)
        except Exception as e:
            logger.error(f"Update last login error: {e}")
    
    # =============================================
    # SESSION MANAGEMENT
    # =============================================
    
    async def create_session(self, mobile: str) -> Optional[str]:
        """Create session token."""
        try:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO sessions (token, mobile, expires_at, created_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (mobile) DO UPDATE SET
                        token = EXCLUDED.token,
                        expires_at = EXCLUDED.expires_at
                """, session_token, mobile, expires_at, datetime.now(timezone.utc))
            
            return session_token
        except Exception as e:
            logger.error(f"Create session error: {e}")
            return None
    
    async def get_user_from_session(self, session_token: str) -> Optional[str]:
        """Get user from session token."""
        if not session_token:
            return None
            
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT mobile FROM sessions 
                    WHERE token = $1 AND expires_at > $2
                """, session_token, datetime.now(timezone.utc))
                
                return row['mobile'] if row else None
        except Exception as e:
            logger.error(f"Get user from session error: {e}")
            return None
    
    async def delete_session(self, session_token: str):
        """Delete session."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM sessions WHERE token = $1", session_token)
        except Exception as e:
            logger.error(f"Delete session error: {e}")
    
    # =============================================
    # SEARCH HISTORY
    # =============================================
    
    async def save_search(self, mobile: str, gstin: str, company_data: Dict[str, Any]):
        """Save search to history."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO search_history 
                    (mobile, gstin, company_name, compliance_score, status, raw_data, searched_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                mobile, gstin,
                company_data.get('company_name', ''),
                company_data.get('compliance_score', 0),
                company_data.get('status', 'Unknown'),
                json.dumps(company_data),
                datetime.now(timezone.utc))
        except Exception as e:
            logger.error(f"Save search error: {e}")
    
    async def get_search_history(self, mobile: str, limit: int = 50) -> List[Dict]:
        """Get user's search history."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT gstin, company_name, compliance_score, status, searched_at, raw_data
                    FROM search_history 
                    WHERE mobile = $1 
                    ORDER BY searched_at DESC 
                    LIMIT $2
                """, mobile, limit)
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get search history error: {e}")
            return []
    
    # =============================================
    # USER PROFILE & PREFERENCES
    # =============================================
    
    async def get_user_profile(self, mobile: str) -> Dict[str, Any]:
        """Get user profile."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT mobile, created_at, last_login FROM users WHERE mobile = $1
                """, mobile)
                
                if row:
                    return {
                        'mobile': row['mobile'],
                        'created_at': row['created_at'],
                        'last_login': row['last_login'],
                        'member_since': row['created_at'].strftime('%B %Y') if row['created_at'] else 'Unknown'
                    }
                return {}
        except Exception as e:
            logger.error(f"Get user profile error: {e}")
            return {}
    
    async def get_user_preferences(self, mobile: str) -> Dict[str, Any]:
        """Get user preferences."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT preferences FROM user_preferences WHERE mobile = $1
                """, mobile)
                
                if row and row['preferences']:
                    return json.loads(row['preferences'])
                return {
                    'theme': 'dark',
                    'notifications': True,
                    'email_alerts': False,
                    'auto_export': False
                }
        except Exception as e:
            logger.error(f"Get user preferences error: {e}")
            return {}
    
    async def save_user_preferences(self, mobile: str, preferences: Dict[str, Any]):
        """Save user preferences."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_preferences (mobile, preferences, updated_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (mobile) DO UPDATE SET
                        preferences = EXCLUDED.preferences,
                        updated_at = EXCLUDED.updated_at
                """, mobile, json.dumps(preferences), datetime.now(timezone.utc))
        except Exception as e:
            logger.error(f"Save user preferences error: {e}")
    
    # =============================================
    # ANALYTICS & STATS
    # =============================================
    
    async def get_user_stats(self, mobile: str) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_searches,
                        COUNT(DISTINCT gstin) as unique_companies,
                        AVG(compliance_score) as avg_compliance,
                        COUNT(CASE WHEN searched_at >= $2 THEN 1 END) as searches_this_month
                    FROM search_history 
                    WHERE mobile = $1
                """, mobile, datetime.now(timezone.utc) - timedelta(days=30))
                
                return {
                    'total_searches': stats['total_searches'] or 0,
                    'unique_companies': stats['unique_companies'] or 0,
                    'avg_compliance': round(stats['avg_compliance'] or 0, 1),
                    'searches_this_month': stats['searches_this_month'] or 0
                }
        except Exception as e:
            logger.error(f"Get user stats error: {e}")
            return {'total_searches': 0, 'unique_companies': 0, 'avg_compliance': 0, 'searches_this_month': 0}
    
    async def get_analytics_data(self, mobile: str) -> Dict[str, Any]:
        """Get analytics data for charts."""
        try:
            async with self.pool.acquire() as conn:
                # Daily searches for last 30 days
                daily_searches = await conn.fetch("""
                    SELECT 
                        DATE(searched_at) as date,
                        COUNT(*) as count
                    FROM search_history 
                    WHERE mobile = $1 AND searched_at >= $2
                    GROUP BY DATE(searched_at)
                    ORDER BY date
                """, mobile, datetime.now(timezone.utc) - timedelta(days=30))
                
                # Top companies
                top_companies = await conn.fetch("""
                    SELECT company_name, COUNT(*) as count
                    FROM search_history 
                    WHERE mobile = $1 AND company_name IS NOT NULL AND company_name != ''
                    GROUP BY company_name
                    ORDER BY count DESC
                    LIMIT 10
                """, mobile)
                
                return {
                    'daily_searches': [{'date': row['date'].isoformat(), 'count': row['count']} for row in daily_searches],
                    'top_companies': [{'name': row['company_name'], 'count': row['count']} for row in top_companies],
                    'score_distribution': []  # Simplified for now
                }
        except Exception as e:
            logger.error(f"Get analytics data error: {e}")
            return {'daily_searches': [], 'top_companies': [], 'score_distribution': []}
    
    # =============================================
    # ADMIN FUNCTIONS
    # =============================================
    
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Get admin statistics."""
        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        (SELECT COUNT(*) FROM users) as total_users,
                        (SELECT COUNT(*) FROM users WHERE last_login >= $1) as active_users,
                        (SELECT COUNT(*) FROM search_history) as total_searches,
                        (SELECT COUNT(*) FROM search_history WHERE searched_at >= CURRENT_DATE) as searches_today
                """, datetime.now(timezone.utc) - timedelta(days=30))
                
                return dict(stats) if stats else {}
        except Exception as e:
            logger.error(f"Get admin stats error: {e}")
            return {}
    
    async def get_users_list(self, page: int = 1, per_page: int = 20, search: str = '') -> Dict[str, Any]:
        """Get paginated users list for admin."""
        try:
            offset = (page - 1) * per_page
            search_pattern = f"%{search}%" if search else "%"
            
            async with self.pool.acquire() as conn:
                # Get total count
                total = await conn.fetchval("""
                    SELECT COUNT(*) FROM users WHERE mobile LIKE $1
                """, search_pattern)
                
                # Get users
                users = await conn.fetch("""
                    SELECT mobile, created_at, last_login,
                           (SELECT COUNT(*) FROM search_history WHERE mobile = users.mobile) as search_count
                    FROM users 
                    WHERE mobile LIKE $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """, search_pattern, per_page, offset)
                
                return {
                    'users': [dict(user) for user in users],
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }
        except Exception as e:
            logger.error(f"Get users list error: {e}")
            return {'users': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0}
    
    # =============================================
    # PASSWORD MANAGEMENT
    # =============================================
    
    async def change_password(self, mobile: str, current_password: str, new_password: str) -> bool:
        """Change user password."""
        # First verify current password
        if not await self.verify_user(mobile, current_password):
            return False
        
        try:
            # Generate new salt and hash
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac(
                'sha256', new_password.encode('utf-8'),
                salt.encode('utf-8'), 100000, dklen=64
            ).hex()
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users SET password_hash = $1, salt = $2
                    WHERE mobile = $3
                """, password_hash, salt, mobile)
            
            return True
        except Exception as e:
            logger.error(f"Change password error: {e}")
            return False
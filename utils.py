#!/usr/bin/env python3
"""
Core Utility Functions for GST Intelligence Platform
Validation, formatting, and helper functions
"""

import re
import json
import asyncio
import logging
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from functools import wraps
import httpx

logger = logging.getLogger(__name__)

# =============================================
# VALIDATION FUNCTIONS
# =============================================

def validate_mobile(mobile: str) -> Tuple[bool, str]:
    """Validate Indian mobile number."""
    if not mobile:
        return False, "Mobile number is required"
    
    # Remove any spaces or special characters
    clean_mobile = re.sub(r'[^\d]', '', mobile)
    
    # Check length
    if len(clean_mobile) != 10:
        return False, "Mobile number must be 10 digits"
    
    # Check if starts with valid digit (6-9)
    if not clean_mobile.startswith(('6', '7', '8', '9')):
        return False, "Mobile number must start with 6, 7, 8, or 9"
    
    # Check if all digits
    if not clean_mobile.isdigit():
        return False, "Mobile number must contain only digits"
    
    return True, clean_mobile

def validate_gstin(gstin: str) -> Tuple[bool, str]:
    """Validate GSTIN format."""
    if not gstin:
        return False, "GSTIN is required"
    
    # Clean and format GSTIN
    clean_gstin = gstin.strip().upper().replace(' ', '')
    
    # Check length
    if len(clean_gstin) != 15:
        return False, "GSTIN must be 15 characters"
    
    # Check format: 2 digits + 5 letters + 4 digits + 1 letter + 1 digit/letter + Z + 1 digit/letter
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    
    if not re.match(pattern, clean_gstin):
        return False, "Invalid GSTIN format"
    
    return True, clean_gstin

def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
    if not password:
        return False, "Password is required"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    if len(password) > 128:
        return False, "Password is too long"
    
    return True, "Password is valid"

# =============================================
# FORMATTING FUNCTIONS
# =============================================

def format_gstin(gstin: str) -> str:
    """Format GSTIN with proper spacing."""
    if not gstin or len(gstin) != 15:
        return gstin
    
    # Format as: XX XXXXX XXXX XXX
    return f"{gstin[:2]} {gstin[2:7]} {gstin[7:11]} {gstin[11:]}"

def format_mobile(mobile: str) -> str:
    """Format mobile number."""
    if not mobile or len(mobile) != 10:
        return mobile
    
    # Format as: +91 XXXXX XXXXX
    return f"+91 {mobile[:5]} {mobile[5:]}"

def format_currency(amount: float, currency: str = "₹") -> str:
    """Format currency amount."""
    if amount >= 10000000:  # 1 crore
        return f"{currency}{amount/10000000:.1f}Cr"
    elif amount >= 100000:  # 1 lakh
        return f"{currency}{amount/100000:.1f}L"
    elif amount >= 1000:  # 1 thousand
        return f"{currency}{amount/1000:.1f}K"
    else:
        return f"{currency}{amount:,.0f}"

def format_date(date_obj, format_str: str = "%d %b %Y") -> str:
    """Format date object to string."""
    if not date_obj:
        return "Not available"
    
    try:
        if isinstance(date_obj, str):
            # Try to parse string date
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        
        return date_obj.strftime(format_str)
    except:
        return str(date_obj)

def format_time_ago(date_obj) -> str:
    """Format date as time ago."""
    if not date_obj:
        return "Never"
    
    try:
        if isinstance(date_obj, str):
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        
        now = datetime.now(date_obj.tzinfo) if date_obj.tzinfo else datetime.now()
        diff = now - date_obj
        
        if diff.days > 30:
            return f"{diff.days // 30} month{'s' if diff.days // 30 > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    except:
        return str(date_obj)

# =============================================
# SECURITY FUNCTIONS
# =============================================

def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """Hash password with salt."""
    if not salt:
        salt = secrets.token_hex(16)
    
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000,
        dklen=64
    ).hex()
    
    return password_hash, salt

def generate_session_token() -> str:
    """Generate secure session token."""
    return secrets.token_urlsafe(32)

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input."""
    if not text:
        return ""
    
    # Remove dangerous characters
    sanitized = re.sub(r'[<>"\';\\]', '', text)
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()

# =============================================
# RATE LIMITING
# =============================================

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        
        # Clean old entries
        self.requests[identifier] = [
            req_time for req_time in self.requests.get(identifier, [])
            if now - req_time < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.requests.get(identifier, [])) >= self.max_requests:
            return False
        
        # Add current request
        if identifier not in self.requests:
            self.requests[identifier] = []
        self.requests[identifier].append(now)
        
        return True
    
    def reset(self, identifier: str):
        """Reset rate limit for identifier."""
        self.requests.pop(identifier, None)

# =============================================
# CACHE MANAGER
# =============================================

class CacheManager:
    """Simple in-memory cache manager."""
    
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        self.memory_cache = {}
        self.cache_ttl = {}
        
        # Try to connect to Redis if URL provided
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url)
                self.redis_client.ping()
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
            else:
                # Memory cache with TTL
                if key in self.memory_cache:
                    if time.time() < self.cache_ttl.get(key, 0):
                        return self.memory_cache[key]
                    else:
                        # Expired
                        self.memory_cache.pop(key, None)
                        self.cache_ttl.pop(key, None)
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL."""
        try:
            if self.redis_client:
                self.redis_client.setex(key, ttl, json.dumps(value))
            else:
                # Memory cache
                self.memory_cache[key] = value
                self.cache_ttl[key] = time.time() + ttl
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache."""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
                self.cache_ttl.pop(key, None)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
    
    async def clear(self):
        """Clear all cache."""
        try:
            if self.redis_client:
                self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
                self.cache_ttl.clear()
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    async def close(self):
        """Close cache connections."""
        if self.redis_client:
            self.redis_client.close()

# =============================================
# API CLIENT
# =============================================

class GSTAPIClient:
    """GST API client with error handling and caching."""
    
    def __init__(self, api_key: str, api_host: str):
        self.api_key = api_key
        self.api_host = api_host
        self.base_url = f"https://{api_host}"
        self.timeout = 30
        
    async def search_gstin(self, gstin: str) -> Dict[str, Any]:
        """Search GSTIN using API."""
        try:
            headers = {
                'X-RapidAPI-Key': self.api_key,
                'X-RapidAPI-Host': self.api_host
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    headers=headers,
                    params={'gstin': gstin}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._process_api_response(data)
                else:
                    logger.error(f"API error: {response.status_code}")
                    return self._get_fallback_data(gstin)
                    
        except Exception as e:
            logger.error(f"GST API request failed: {e}")
            return self._get_fallback_data(gstin)
    
    def _process_api_response(self, data: Dict) -> Dict[str, Any]:
        """Process API response into standard format."""
        return {
            'gstin': data.get('gstin', ''),
            'company_name': data.get('tradeNam', 'Unknown Company'),
            'status': data.get('sts', 'Unknown'),
            'registration_date': data.get('rgdt', ''),
            'business_type': data.get('ctb', 'Unknown'),
            'state': data.get('pradr', {}).get('addr', {}).get('stcd', ''),
            'compliance_score': self._calculate_compliance_score(data),
            'raw_data': data
        }
    
    def _calculate_compliance_score(self, data: Dict) -> int:
        """Calculate compliance score based on available data."""
        score = 50  # Base score
        
        if data.get('sts') == 'Active':
            score += 30
        
        if data.get('rgdt'):
            score += 10
        
        if data.get('tradeNam'):
            score += 10
        
        return min(score, 100)
    
    def _get_fallback_data(self, gstin: str) -> Dict[str, Any]:
        """Get fallback data when API fails."""
        return {
            'gstin': gstin,
            'company_name': 'Data Not Available',
            'status': 'Unknown',
            'registration_date': '',
            'business_type': 'Unknown',
            'state': '',
            'compliance_score': 0,
            'error': 'API service temporarily unavailable',
            'raw_data': {}
        }

# =============================================
# ERROR HANDLING DECORATORS
# =============================================

def handle_api_errors(func):
    """Decorator for handling API errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {e}")
            return {
                'success': False,
                'error': 'Internal server error',
                'message': 'Something went wrong. Please try again.'
            }
    return wrapper

def handle_db_errors(func):
    """Decorator for handling database errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            return None
    return wrapper

# =============================================
# UTILITY FUNCTIONS
# =============================================

def get_user_display_name(mobile: str) -> str:
    """Get display name for user."""
    if not mobile:
        return "Guest"
    
    # Mask mobile number: +91 XXXXX XX890
    if len(mobile) == 10:
        return f"+91 {mobile[:5]} XX{mobile[-3:]}"
    
    return mobile

def calculate_business_insights(search_history: List[Dict]) -> Dict[str, Any]:
    """Calculate business insights from search history."""
    if not search_history:
        return {}
    
    total_searches = len(search_history)
    active_companies = len(set(item.get('gstin') for item in search_history if item.get('gstin')))
    avg_compliance = sum(item.get('compliance_score', 0) for item in search_history) / total_searches
    
    # Recent activity (last 7 days)
    recent_date = datetime.now() - timedelta(days=7)
    recent_searches = [
        item for item in search_history
        if item.get('searched_at') and 
        (datetime.fromisoformat(str(item['searched_at']).replace('Z', '+00:00')) > recent_date)
    ]
    
    return {
        'total_searches': total_searches,
        'active_companies': active_companies,
        'avg_compliance_score': round(avg_compliance, 1),
        'recent_activity': len(recent_searches),
        'most_searched_state': 'Unknown',  # Would need state data
        'trend': 'stable'  # Simplified
    }

def generate_search_suggestions(query: str) -> List[str]:
    """Generate search suggestions."""
    suggestions = []
    
    if len(query) >= 2:
        # Common GSTIN patterns
        if query.isdigit() and len(query) <= 2:
            # State code suggestions
            state_codes = ['07', '09', '23', '27', '29', '06', '24']
            suggestions.extend([code for code in state_codes if code.startswith(query)])
        
        # Add common patterns
        if len(query) < 15:
            suggestions.append(f"{query}...")
    
    return suggestions[:5]  # Limit to 5 suggestions

def export_search_history_csv(search_history: List[Dict]) -> str:
    """Export search history to CSV format."""
    if not search_history:
        return "No data to export"
    
    csv_lines = []
    csv_lines.append("GSTIN,Company Name,Status,Compliance Score,Search Date")
    
    for item in search_history:
        line = f"{item.get('gstin', '')},{item.get('company_name', '')},{item.get('status', '')},{item.get('compliance_score', 0)},{item.get('searched_at', '')}"
        csv_lines.append(line)
    
    return "\n".join(csv_lines)

# =============================================
# ADMIN UTILITIES
# =============================================

def get_system_health() -> Dict[str, Any]:
    """Get system health information."""
    import psutil
    
    try:
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }
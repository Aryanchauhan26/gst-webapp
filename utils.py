#!/usr/bin/env python3
"""
Optimized Core Utility Functions for GST Intelligence Platform
Removed duplicates, improved performance, and enhanced validation
"""

import re
import json
import asyncio
import logging
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from functools import wraps, lru_cache
import httpx

logger = logging.getLogger(__name__)

# =============================================
# VALIDATION FUNCTIONS (OPTIMIZED)
# =============================================

# Compile regex patterns once for better performance
MOBILE_PATTERN = re.compile(r'^[6-9]\d{9}$')
GSTIN_PATTERN = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')

def validate_mobile(mobile: str) -> Tuple[bool, str]:
    """
    Optimized mobile number validation.
    Returns: (is_valid, cleaned_mobile_or_error_message)
    """
    if not mobile:
        return False, "Mobile number is required"
    
    # Remove any non-digit characters
    clean_mobile = re.sub(r'[^\d]', '', mobile)
    
    # Check length
    if len(clean_mobile) != 10:
        return False, "Mobile number must be 10 digits"
    
    # Check pattern (starts with 6-9)
    if not MOBILE_PATTERN.match(clean_mobile):
        return False, "Mobile number must start with 6, 7, 8, or 9"
    
    return True, clean_mobile

def validate_gstin(gstin: str) -> Tuple[bool, str]:
    """
    Optimized GSTIN validation with checksum verification.
    Returns: (is_valid, cleaned_gstin_or_error_message)
    """
    if not gstin:
        return False, "GSTIN is required"
    
    # Clean and format GSTIN
    clean_gstin = gstin.strip().upper().replace(' ', '').replace('-', '')
    
    # Check length
    if len(clean_gstin) != 15:
        return False, "GSTIN must be 15 characters"
    
    # Check basic format
    if not GSTIN_PATTERN.match(clean_gstin):
        return False, "Invalid GSTIN format"
    
    # Optional: Add checksum validation for extra accuracy
    if not _validate_gstin_checksum(clean_gstin):
        return False, "GSTIN checksum validation failed"
    
    return True, clean_gstin

def _validate_gstin_checksum(gstin: str) -> bool:
    """
    Validate GSTIN checksum (last digit).
    This is an optional enhanced validation.
    """
    try:
        # GSTIN checksum algorithm
        factor = 2
        total = 0
        code_point_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        for char in gstin[:-1]:  # Exclude last character
            digit = code_point_chars.index(char)
            total += digit * factor
            factor = 1 if factor == 2 else 2
        
        remainder = total % 37
        check_code_point = (37 - remainder) % 37
        return code_point_chars[check_code_point] == gstin[-1]
    except (ValueError, IndexError):
        return False

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Optimized email validation.
    Returns: (is_valid, cleaned_email_or_error_message)
    """
    if not email:
        return False, "Email is required"
    
    clean_email = email.strip().lower()
    
    if len(clean_email) > 255:
        return False, "Email is too long"
    
    if not EMAIL_PATTERN.match(clean_email):
        return False, "Invalid email format"
    
    return True, clean_email

def validate_password(password: str, min_length: int = 6, max_length: int = 128) -> Tuple[bool, str]:
    """
    Enhanced password validation with configurable requirements.
    Returns: (is_valid, error_message_or_success)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"
    
    if len(password) > max_length:
        return False, f"Password is too long (max {max_length} characters)"
    
    # Optional: Add strength requirements
    strength_score = _calculate_password_strength(password)
    if strength_score < 2:
        return False, "Password is too weak. Include numbers, letters, and symbols"
    
    return True, "Password is valid"

def _calculate_password_strength(password: str) -> int:
    """Calculate password strength score (0-4)."""
    score = 0
    
    # Length bonus
    if len(password) >= 8:
        score += 1
    
    # Character variety
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    
    return min(score, 4)

def validate_pan(pan: str) -> Tuple[bool, str]:
    """
    PAN validation for enhanced business verification.
    Returns: (is_valid, cleaned_pan_or_error_message)
    """
    if not pan:
        return False, "PAN is required"
    
    clean_pan = pan.strip().upper().replace(' ', '')
    
    if len(clean_pan) != 10:
        return False, "PAN must be 10 characters"
    
    if not PAN_PATTERN.match(clean_pan):
        return False, "Invalid PAN format"
    
    return True, clean_pan

# =============================================
# FORMATTING FUNCTIONS (OPTIMIZED)
# =============================================

@lru_cache(maxsize=1000)
def format_gstin(gstin: str) -> str:
    """
    Format GSTIN with proper spacing (cached for performance).
    Format: XX XXXXX XXXX XXX
    """
    if not gstin or len(gstin) != 15:
        return gstin
    
    return f"{gstin[:2]} {gstin[2:7]} {gstin[7:11]} {gstin[11:]}"

@lru_cache(maxsize=1000)
def format_mobile(mobile: str, country_code: str = "+91") -> str:
    """
    Format mobile number with country code (cached for performance).
    Format: +91 XXXXX XXXXX
    """
    if not mobile or len(mobile) != 10:
        return mobile
    
    return f"{country_code} {mobile[:5]} {mobile[5:]}"

def format_currency(amount: Union[int, float], currency: str = "₹", decimal_places: int = 2) -> str:
    """
    Format currency amount with proper Indian numbering system.
    """
    if amount is None:
        return f"{currency}0"
    
    # Convert to float for formatting
    amount = float(amount)
    
    # Format with Indian numbering system (lakhs, crores)
    if amount >= 10000000:  # 1 crore
        formatted = f"{amount/10000000:.{max(0, decimal_places-2)}f} Cr"
    elif amount >= 100000:  # 1 lakh
        formatted = f"{amount/100000:.{max(0, decimal_places-1)}f} L"
    elif amount >= 1000:  # 1 thousand
        formatted = f"{amount/1000:.{max(0, decimal_places-1)}f} K"
    else:
        formatted = f"{amount:.{decimal_places}f}"
    
    return f"{currency}{formatted}"

def format_date(date_input: Union[str, datetime], format_string: str = "%d %b %Y") -> str:
    """
    Format date with error handling.
    """
    try:
        if isinstance(date_input, str):
            # Try to parse common date formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
                try:
                    date_obj = datetime.strptime(date_input.split('T')[0], fmt.split('T')[0])
                    break
                except ValueError:
                    continue
            else:
                return date_input  # Return original if parsing fails
        elif isinstance(date_input, datetime):
            date_obj = date_input
        else:
            return str(date_input)
        
        return date_obj.strftime(format_string)
    except Exception:
        return str(date_input)

# =============================================
# SECURITY FUNCTIONS (ENHANCED)
# =============================================

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token."""
    return secrets.token_urlsafe(length)

def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """
    Hash password with salt using modern algorithm.
    Returns: (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(32)
    
    # Use SHA-256 for now, consider upgrading to bcrypt/scrypt for production
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt

def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify password against hash."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, hashed_password)

def sanitize_input(input_string: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    """
    if not input_string:
        return ""
    
    # Basic HTML entity encoding
    sanitized = (input_string
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;')
                .replace('/', '&#x2F;'))
    
    # Truncate if too long
    return sanitized[:max_length] if len(sanitized) > max_length else sanitized

# =============================================
# PERFORMANCE UTILITIES
# =============================================

def timing_decorator(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            logger.debug(f"{func.__name__} executed in {execution_time:.2f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"{func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            logger.debug(f"{func.__name__} executed in {execution_time:.2f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"{func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

def rate_limit_decorator(max_calls: int, window_seconds: int):
    """Rate limiting decorator with sliding window."""
    call_times = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Use first argument as key (usually user ID)
            key = str(args[0]) if args else "default"
            current_time = time.time()
            
            # Clean old entries
            if key in call_times:
                call_times[key] = [t for t in call_times[key] if current_time - t < window_seconds]
            else:
                call_times[key] = []
            
            # Check rate limit
            if len(call_times[key]) >= max_calls:
                raise Exception(f"Rate limit exceeded: {max_calls} calls per {window_seconds} seconds")
            
            # Record this call
            call_times[key].append(current_time)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# =============================================
# DATA PROCESSING UTILITIES
# =============================================

def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with dict2 values taking precedence.
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def extract_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Extract value from nested dictionary using dot notation.
    Example: extract_nested_value(data, "user.profile.name")
    """
    keys = key_path.split('.')
    current_data = data
    
    try:
        for key in keys:
            if isinstance(current_data, dict) and key in current_data:
                current_data = current_data[key]
            else:
                return default
        return current_data
    except (KeyError, TypeError):
        return default

def flatten_dict(data: Dict[str, Any], prefix: str = "", separator: str = ".") -> Dict[str, Any]:
    """
    Flatten nested dictionary structure.
    """
    flattened = {}
    
    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        
        if isinstance(value, dict):
            flattened.update(flatten_dict(value, new_key, separator))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    flattened.update(flatten_dict(item, f"{new_key}[{i}]", separator))
                else:
                    flattened[f"{new_key}[{i}]"] = item
        else:
            flattened[new_key] = value
    
    return flattened

# =============================================
# HTTP CLIENT UTILITIES
# =============================================

class OptimizedHTTPClient:
    """Optimized HTTP client with connection pooling and retry logic."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries} retries: {e}")
        
        raise last_exception
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# =============================================
# FILE UTILITIES
# =============================================

def generate_filename(prefix: str, extension: str, include_timestamp: bool = True) -> str:
    """Generate unique filename with optional timestamp."""
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    else:
        random_suffix = secrets.token_hex(4)
        return f"{prefix}_{random_suffix}.{extension}"

def get_file_size_string(size_bytes: int) -> str:
    """Convert file size to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

# =============================================
# LOGGING UTILITIES
# =============================================

def setup_logger(name: str, level: str = "INFO", log_file: str = None) -> logging.Logger:
    """Setup optimized logger with proper formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# =============================================
# EXPORTS
# =============================================

__all__ = [
    # Validation functions
    'validate_mobile', 'validate_gstin', 'validate_email', 'validate_password', 'validate_pan',
    
    # Formatting functions
    'format_gstin', 'format_mobile', 'format_currency', 'format_date',
    
    # Security functions
    'generate_secure_token', 'hash_password', 'verify_password', 'sanitize_input',
    
    # Performance utilities
    'timing_decorator', 'rate_limit_decorator',
    
    # Data processing
    'deep_merge_dicts', 'extract_nested_value', 'flatten_dict',
    
    # HTTP client
    'OptimizedHTTPClient',
    
    # File utilities
    'generate_filename', 'get_file_size_string',
    
    # Logging
    'setup_logger'
]
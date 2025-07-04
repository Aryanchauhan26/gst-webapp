#!/usr/bin/env python3
"""
GST Intelligence Platform - Complete Main Application
Enhanced with clean architecture and comprehensive functionality
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
from datetime import datetime, timedelta
from functools import wraps
from razorpay_lending import RazorpayLendingClient, LoanManager, LoanConfig, LoanStatus
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from typing import Optional, Dict, List, Any, Tuple, Union, Callable
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from io import BytesIO, StringIO
from enum import Enum
import jwt
import redis
import fnmatch
import csv
import time
import re
from typing import Dict, List, Any, Tuple
from datetime import datetime, date
import html
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    logger.warning("WeasyPrint not available - PDF generation disabled")
    HAS_WEASYPRINT = False
    HTML = None
from dotenv import load_dotenv
from anthro_ai import get_anthropic_synopsis
from pydantic import BaseModel, field_validator, validator
import html

# Load environment variables
load_dotenv()

# Configuration
try:
    from config import settings as config
    print(f"✅ Config loaded successfully - Environment: {config.ENVIRONMENT}")
except Exception as e:
    print(f"❌ Config loading failed: {e}")
    raise

class DataValidator:
    """Enhanced data validator with comprehensive error handling."""
    
    # GSTIN validation patterns
    GSTIN_PATTERN = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
    PAN_PATTERN = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
    
    # State codes for GSTIN validation
    STATE_CODES = {
        '01': 'Jammu and Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab',
        '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana',
        '07': 'Delhi', '08': 'Rajasthan', '09': 'Uttar Pradesh',
        '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh',
        '13': 'Nagaland', '14': 'Manipur', '15': 'Mizoram',
        '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam',
        '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha',
        '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
        '25': 'Daman and Diu', '26': 'Dadra and Nagar Haveli',
        '27': 'Maharashtra', '28': 'Andhra Pradesh', '29': 'Karnataka',
        '30': 'Goa', '31': 'Lakshadweep', '32': 'Kerala',
        '33': 'Tamil Nadu', '34': 'Puducherry', '35': 'Andaman and Nicobar Islands',
        '36': 'Telangana', '37': 'Andhra Pradesh', '38': 'Ladakh'
    }
    
    @staticmethod
    def validate_gstin(gstin: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Enhanced GSTIN validation with detailed error reporting.
        
        Returns:
            Tuple[bool, str, Dict]: (is_valid, error_message, extracted_info)
        """
        if not gstin:
            return False, "GSTIN is required", {}
        
        # Clean and uppercase
        gstin = gstin.strip().upper()
        
        # Length check
        if len(gstin) != 15:
            return False, f"GSTIN must be 15 characters long, got {len(gstin)}", {}
        
        # Pattern check
        if not DataValidator.GSTIN_PATTERN.match(gstin):
            return False, "Invalid GSTIN format", {}
        
        # Extract components
        state_code = gstin[:2]
        pan_part = gstin[2:12]
        entity_code = gstin[12]
        check_digit = gstin[13]
        default_z = gstin[14]
        
        # Validate state code
        if state_code not in DataValidator.STATE_CODES:
            return False, f"Invalid state code: {state_code}", {}
        
        # Validate PAN part
        if not DataValidator.PAN_PATTERN.match(pan_part):
            return False, "Invalid PAN format in GSTIN", {}
        
        # Validate default 'Z'
        if default_z != 'Z':
            return False, "14th character must be 'Z'", {}
        
        # Extract information
        extracted_info = {
            'state_code': state_code,
            'state_name': DataValidator.STATE_CODES[state_code],
            'pan': pan_part,
            'entity_code': entity_code,
            'check_digit': check_digit,
            'is_valid': True
        }
        
        return True, "", extracted_info
    
    @staticmethod
    def validate_mobile(mobile: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Enhanced mobile number validation with international support.
        
        Returns:
            Tuple[bool, str, Dict]: (is_valid, error_message, formatted_number)
        """
        if not mobile:
            return False, "Mobile number is required", {}
        
        # Clean the number
        mobile = mobile.strip()
        
        try:
            # Try parsing as Indian number first
            if mobile.startswith('+91'):
                parsed = phonenumbers.parse(mobile, None)
            elif mobile.startswith('91') and len(mobile) == 12:
                parsed = phonenumbers.parse(f'+{mobile}', None)
            elif len(mobile) == 10:
                parsed = phonenumbers.parse(mobile, 'IN')
            else:
                # Try parsing with country detection
                parsed = phonenumbers.parse(mobile, None)
            
            # Validate the parsed number
            if not phonenumbers.is_valid_number(parsed):
                return False, "Invalid mobile number", {}
            
            # Format the number
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
            
            return True, "", {
                'formatted': formatted,
                'national': national,
                'country_code': parsed.country_code,
                'national_number': parsed.national_number
            }
            
        except NumberParseException as e:
            return False, f"Invalid mobile number: {str(e)}", {}
        except Exception as e:
            return False, f"Mobile validation error: {str(e)}", {}
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Enhanced email validation."""
        if not email:
            return False, "Email is required"
        
        email = email.strip().lower()
        
        # Basic regex for email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        # Additional checks
        if len(email) > 254:
            return False, "Email address too long"
        
        local_part = email.split('@')[0]
        if len(local_part) > 64:
            return False, "Email local part too long"
        
        return True, ""
    
    @staticmethod
    def validate_amount(amount: Union[str, int, float, Decimal]) -> Tuple[bool, str, Optional[Decimal]]:
        """
        Enhanced amount validation with decimal precision.
        
        Returns:
            Tuple[bool, str, Optional[Decimal]]: (is_valid, error_message, decimal_amount)
        """
        if amount is None:
            return False, "Amount is required", None
        
        try:
            # Convert to Decimal for precision
            if isinstance(amount, str):
                amount = amount.strip().replace(',', '')
            
            decimal_amount = Decimal(str(amount))
            
            # Check if positive
            if decimal_amount <= 0:
                return False, "Amount must be positive", None
            
            # Check reasonable limits
            if decimal_amount > Decimal('999999999999.99'):  # 999 billion
                return False, "Amount too large", None
            
            # Check decimal places (max 2 for currency)
            if decimal_amount.as_tuple().exponent < -2:
                return False, "Amount can have maximum 2 decimal places", None
            
            return True, "", decimal_amount
            
        except (InvalidOperation, ValueError) as e:
            return False, f"Invalid amount format: {str(e)}", None
    
    @staticmethod
    def validate_date(date_str: str, format_str: str = "%Y-%m-%d") -> Tuple[bool, str, Optional[datetime]]:
        """
        Enhanced date validation.
        
        Returns:
            Tuple[bool, str, Optional[datetime]]: (is_valid, error_message, parsed_date)
        """
        if not date_str:
            return False, "Date is required", None
        
        try:
            parsed_date = datetime.strptime(date_str.strip(), format_str)
            
            # Check reasonable date range
            min_date = datetime(1900, 1, 1)
            max_date = datetime(2100, 12, 31)
            
            if parsed_date < min_date or parsed_date > max_date:
                return False, "Date out of reasonable range", None
            
            return True, "", parsed_date
            
        except ValueError as e:
            return False, f"Invalid date format: {str(e)}", None

# =============================================================================
# BUSINESS LOGIC VALIDATORS
# =============================================================================

class BusinessValidator:
    """Business-specific validation logic."""
    
    @staticmethod
    def validate_compliance_score(score: Union[int, float]) -> Tuple[bool, str]:
        """Validate compliance score range."""
        try:
            score = float(score)
            if 0 <= score <= 100:
                return True, ""
            else:
                return False, "Compliance score must be between 0 and 100"
        except (ValueError, TypeError):
            return False, "Compliance score must be a number"
    
    @staticmethod
    def validate_business_vintage(months: int) -> Tuple[bool, str]:
        """Validate business vintage in months."""
        try:
            months = int(months)
            if months < 0:
                return False, "Business vintage cannot be negative"
            if months > 1200:  # 100 years
                return False, "Business vintage seems unreasonably high"
            return True, ""
        except (ValueError, TypeError):
            return False, "Business vintage must be a number"
    
    @staticmethod
    def validate_turnover_consistency(monthly_revenue: float, annual_turnover: float) -> Tuple[bool, str]:
        """Validate consistency between monthly revenue and annual turnover."""
        try:
            expected_annual = monthly_revenue * 12
            variance = abs(annual_turnover - expected_annual) / expected_annual
            
            if variance > 0.5:  # 50% variance allowed
                return False, "Monthly revenue and annual turnover seem inconsistent"
            
            return True, ""
        except (ValueError, TypeError, ZeroDivisionError):
            return False, "Invalid revenue data for consistency check"

# =============================================================================
# DATA SANITIZATION
# =============================================================================

class DataSanitizer:
    """Data sanitization utilities."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input."""
        if not value:
            return ""
        
        # Remove control characters and excessive whitespace
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(value))
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()
        
        return sanitized
    
    @staticmethod
    def sanitize_gstin(gstin: str) -> str:
        """Sanitize GSTIN input."""
        if not gstin:
            return ""
        
        # Remove spaces and convert to uppercase
        return re.sub(r'\s+', '', gstin.upper())
    
    @staticmethod
    def sanitize_mobile(mobile: str) -> str:
        """Sanitize mobile number input."""
        if not mobile:
            return ""
        
        # Remove all non-digit characters except + at start
        mobile = mobile.strip()
        if mobile.startswith('+'):
            return '+' + re.sub(r'\D', '', mobile[1:])
        else:
            return re.sub(r'\D', '', mobile)

# =============================================================================
# COMPREHENSIVE DATA PROCESSOR
# =============================================================================

class DataProcessor:
    """Comprehensive data processing with validation and sanitization."""
    
    def __init__(self):
        self.validator = DataValidator()
        self.business_validator = BusinessValidator()
        self.sanitizer = DataSanitizer()
        self.errors = []
        self.warnings = []
    
    def process_user_data(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Process user registration/profile data.
        
        Returns:
            Tuple[bool, Dict, List]: (is_valid, processed_data, error_messages)
        """
        self.errors = []
        self.warnings = []
        processed = {}
        
        # Mobile validation
        if 'mobile' in data:
            mobile = self.sanitizer.sanitize_mobile(data['mobile'])
            is_valid, error, formatted = self.validator.validate_mobile(mobile)
            if is_valid:
                processed['mobile'] = formatted['formatted']
                processed['mobile_national'] = formatted['national']
            else:
                self.errors.append(f"Mobile: {error}")
        
        # Email validation
        if 'email' in data:
            email = self.sanitizer.sanitize_string(data['email'])
            is_valid, error = self.validator.validate_email(email)
            if is_valid:
                processed['email'] = email.lower()
            else:
                self.errors.append(f"Email: {error}")
        
        # Name validation
        if 'display_name' in data:
            name = self.sanitizer.sanitize_string(data['display_name'], 100)
            if len(name) < 2:
                self.errors.append("Display name must be at least 2 characters")
            else:
                processed['display_name'] = name
        
        # Company validation
        if 'company' in data:
            company = self.sanitizer.sanitize_string(data['company'], 200)
            processed['company'] = company
        
        return len(self.errors) == 0, processed, self.errors
    
    def process_loan_data(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Process loan application data.
        
        Returns:
            Tuple[bool, Dict, List]: (is_valid, processed_data, error_messages)
        """
        self.errors = []
        self.warnings = []
        processed = {}
        
        # GSTIN validation
        if 'gstin' in data:
            gstin = self.sanitizer.sanitize_gstin(data['gstin'])
            is_valid, error, info = self.validator.validate_gstin(gstin)
            if is_valid:
                processed['gstin'] = gstin
                processed['state_code'] = info['state_code']
                processed['state_name'] = info['state_name']
                processed['pan'] = info['pan']
            else:
                self.errors.append(f"GSTIN: {error}")
        
        # Amount validations
        for field in ['loan_amount', 'annual_turnover', 'monthly_revenue']:
            if field in data:
                is_valid, error, amount = self.validator.validate_amount(data[field])
                if is_valid:
                    processed[field] = float(amount)
                else:
                    self.errors.append(f"{field.replace('_', ' ').title()}: {error}")
        
        # Business vintage validation
        if 'business_vintage_months' in data:
            is_valid, error = self.business_validator.validate_business_vintage(data['business_vintage_months'])
            if is_valid:
                processed['business_vintage_months'] = int(data['business_vintage_months'])
            else:
                self.errors.append(f"Business vintage: {error}")
        
        # Compliance score validation
        if 'compliance_score' in data:
            is_valid, error = self.business_validator.validate_compliance_score(data['compliance_score'])
            if is_valid:
                processed['compliance_score'] = float(data['compliance_score'])
            else:
                self.errors.append(f"Compliance score: {error}")
        
        # Cross-validation
        if 'monthly_revenue' in processed and 'annual_turnover' in processed:
            is_valid, error = self.business_validator.validate_turnover_consistency(
                processed['monthly_revenue'], processed['annual_turnover']
            )
            if not is_valid:
                self.warnings.append(f"Turnover consistency: {error}")
        
        return len(self.errors) == 0, processed, self.errors + self.warnings

# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def example_usage():
    """Example of how to use the enhanced validation system."""
    processor = DataProcessor()
    
    # Example user data
    user_data = {
        'mobile': '+91 98765 43210',
        'email': 'test@example.com',
        'display_name': 'John Doe',
        'company': 'Example Corp'
    }
    
    is_valid, processed, errors = processor.process_user_data(user_data)
    
    if is_valid:
        print("✅ User data is valid:", processed)
    else:
        print("❌ User data validation failed:", errors)
    
    # Example loan data
    loan_data = {
        'gstin': '07AABCU9603R1ZX',
        'loan_amount': '1000000',
        'annual_turnover': '5000000',
        'monthly_revenue': '400000',
        'business_vintage_months': 36,
        'compliance_score': 85
    }
    
    is_valid, processed, errors = processor.process_loan_data(loan_data)
    
    if is_valid:
        print("✅ Loan data is valid:", processed)
    else:
        print("❌ Loan data validation failed:", errors)

if __name__ == "__main__":
    example_usage()

# PydanticModels
class LoanApplicationRequest(BaseModel):
    gstin: str
    company_name: str
    loan_amount: float
    purpose: str
    tenure_months: int
    annual_turnover: float
    monthly_revenue: float
    compliance_score: float
    business_vintage_months: int
    
    @field_validator('loan_amount', 'annual_turnover', 'monthly_revenue')
    @classmethod
    def validate_positive_amounts(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
    
    @field_validator('tenure_months', 'business_vintage_months')
    @classmethod
    def validate_positive_months(cls, v):
        if v <= 0:
            raise ValueError('Months must be positive')
        return v
    
    @field_validator('compliance_score')
    @classmethod
    def validate_compliance_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Compliance score must be between 0 and 100')
        return v
    
class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
    
    @field_validator('newPassword')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

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

class BatchSearchRequest(BaseModel):
    gstins: List[str]
    
    @field_validator('gstins')
    @classmethod
    def validate_gstins(cls, v):
        if len(v) > 10:
            raise ValueError('Maximum 10 GSTINs allowed')
        return v

class ErrorLogRequest(BaseModel):
    type: str
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    userAgent: Optional[str] = None
    timestamp: Optional[str] = None

def handle_api_errors(func):
    """Decorator for handling API errors consistently"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"API error in {func.__name__}: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Internal server error"}
            )
    return wrapper

class CacheManager:
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager with robust Redis fallback."""
        self.redis_client = None
        self.memory_cache = {}
        self.cache_ttl = 300  # 5 minutes default
        self.redis_url = redis_url
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        
        # Try to connect to Redis
        if redis_url:
            self._init_redis_connection()
        else:
            logger.info("📝 Redis not configured - using in-memory cache only")
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_memory_cache())

    def _init_redis_connection(self):
        """Initialize Redis connection with retry logic."""
        try:
            import redis
            
            # Parse Redis URL for better error reporting
            if self.redis_url.startswith('redis://'):
                logger.info(f"🔄 Attempting Redis connection...")
                
            self.redis_client = redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis cache connected successfully")
            
        except ImportError:
            logger.warning("⚠️ Redis package not installed - using memory cache")
            self.redis_client = None
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            logger.info("📝 Falling back to in-memory cache")
            self.redis_client = None

    async def _test_redis_connection(self) -> bool:
        """Test if Redis connection is still alive."""
        if not self.redis_client:
            return False
            
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis connection test failed: {e}")
            self.redis_client = None
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with Redis health check."""
        try:
            # Try Redis first if available
            if self.redis_client and await self._test_redis_connection():
                try:
                    value = self.redis_client.get(key)
                    if value:
                        return json.loads(value)
                except Exception as e:
                    logger.warning(f"Redis get error for key {key}: {e}")
                    # Fall through to memory cache
            
            # Use memory cache
            if key in self.memory_cache:
                item = self.memory_cache[key]
                expires = item.get('expires', 0)
                
                # Ensure expires is a valid number
                try:
                    expires_time = float(expires)
                    if time.time() < expires_time:
                        return item.get('value')
                    else:
                        # Cleanup expired entry
                        del self.memory_cache[key]
                except (ValueError, TypeError):
                    # Remove entries with invalid expires
                    del self.memory_cache[key]
                    
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL."""
        try:
            if ttl is None:
                ttl = self.cache_ttl
                
            # Try Redis first if available
            if self.redis_client and await self._test_redis_connection():
                try:
                    json_value = json.dumps(value)
                    self.redis_client.setex(key, ttl, json_value)
                    logger.debug(f"✅ Set Redis cache: {key}")
                    return True
                except Exception as e:
                    logger.warning(f"Redis set error for key {key}: {e}")
                    # Fall through to memory cache
            
            # Use memory cache
            expires_time = time.time() + ttl
            self.memory_cache[key] = {
                'value': value,
                'expires': expires_time
            }
            logger.debug(f"✅ Set memory cache: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            # Try Redis first if available
            if self.redis_client and await self._test_redis_connection():
                try:
                    self.redis_client.delete(key)
                    logger.debug(f"🗑️ Deleted Redis cache: {key}")
                except Exception as e:
                    logger.warning(f"Redis delete error for key {key}: {e}")
            
            # Remove from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
                logger.debug(f"🗑️ Deleted memory cache: {key}")
            
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str = "*") -> int:
        """Clear cache entries matching pattern."""
        count = 0
        
        try:
            # Clear Redis cache
            if self.redis_client and await self._test_redis_connection():
                try:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        deleted = self.redis_client.delete(*keys)
                        count += deleted
                        logger.info(f"🗑️ Cleared {deleted} Redis entries matching: {pattern}")
                except Exception as e:
                    logger.warning(f"Redis clear pattern error: {e}")
            
            # Clear memory cache
            memory_keys = list(self.memory_cache.keys())
            for key in memory_keys:
                if fnmatch.fnmatch(key, pattern):
                    del self.memory_cache[key]
                    count += 1
            
            if count > 0:
                logger.info(f"🗑️ Cleared {count} total cache entries matching: {pattern}")
            
            return count
            
        except Exception as e:
            logger.error(f"Cache clear pattern error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            # Check Redis first
            if self.redis_client and await self._test_redis_connection():
                try:
                    return bool(self.redis_client.exists(key))
                except Exception as e:
                    logger.warning(f"Redis exists error for key {key}: {e}")
            
            # Check memory cache
            if key in self.memory_cache:
                item = self.memory_cache[key]
                expires = item.get('expires', 0)
                
                try:
                    expires_time = float(expires)
                    if time.time() < expires_time:
                        return True
                    else:
                        # Cleanup expired entry
                        del self.memory_cache[key]
                except (ValueError, TypeError):
                    # Remove entries with invalid expires
                    del self.memory_cache[key]
            
            return False
            
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive cache health status."""
        status = {
            'type': 'memory',
            'redis_configured': bool(self.redis_url),
            'redis_connected': False,
            'memory_entries': len(self.memory_cache),
            'last_cleanup': getattr(self, '_last_cleanup', 'never')
        }
        
        if self.redis_client:
            try:
                if await self._test_redis_connection():
                    status['type'] = 'redis'
                    status['redis_connected'] = True
                    
                    # Get Redis info if possible
                    try:
                        info = self.redis_client.info('memory')
                        status['redis_memory'] = info.get('used_memory_human', 'unknown')
                        status['redis_keys'] = info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)
                    except Exception:
                        pass
            except Exception:
                pass
        
        return status

    async def _cleanup_memory_cache(self):
        """Periodic cleanup of expired memory cache entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                if not self.redis_client:  # Only for memory cache
                    current_time = time.time()
                    expired_keys = []

                    for key, item in list(self.memory_cache.items()):
                        try:
                            expires_time = float(item.get('expires', 0))
                            if current_time > expires_time:
                                expired_keys.append(key)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid expires value for key {key}: {item.get('expires')}")
                            expired_keys.append(key)

                    # Clean up expired entries
                    for key in expired_keys:
                        try:
                            del self.memory_cache[key]
                        except KeyError:
                            pass

                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
                    self._last_cleanup = datetime.now().isoformat()
                    
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'memory_entries': len(self.memory_cache),
            'redis_configured': bool(self.redis_url),
            'redis_connected': bool(self.redis_client),
            'type': 'redis' if self.redis_client else 'memory'
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats.update({
                    'redis_memory': info.get('used_memory_human', 'unknown'),
                    'redis_keys': info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0),
                    'redis_hits': info.get('keyspace_hits', 0),
                    'redis_misses': info.get('keyspace_misses', 0)
                })
            except Exception:
                stats['redis_connected'] = False
        
        return stats

# Initialize FastAPI app
app = FastAPI(
    title="GST Intelligence Platform", 
    version="2.0.0",
    description="Advanced GST Compliance Analytics Platform"
)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize security components on startup."""
    logger.info("🔐 Security system initialized")
    app.start_time = time.time()

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Rate Limiter
class AdvancedRateLimiter:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.memory_store = defaultdict(list)
    
    async def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        key = f"rate_limit:{identifier}"
        
        if self.redis:
            return await self._redis_rate_limit(key, limit, window, now, identifier)
        else:
            return self._memory_rate_limit(identifier, limit, window, now)
    
    async def _redis_rate_limit(self, key: str, limit: int, window: int, now: float, identifier: str) -> bool:
        """Redis-based rate limiting using sliding window."""
        try:
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            return current_requests < limit
        except Exception as e:
            logger.warning(f"Redis rate limiting failed, falling back to memory: {e}")
            return self._memory_rate_limit(identifier, limit, window, now)
    
    def _memory_rate_limit(self, identifier: str, limit: int, window: int, now: float) -> bool:
        """Memory-based rate limiting fallback."""
        requests = self.memory_store[identifier]
        
        # Remove expired requests
        cutoff = now - window
        self.memory_store[identifier] = [req_time for req_time in requests if req_time > cutoff]
        
        if len(self.memory_store[identifier]) >= limit:
            return False
        
        self.memory_store[identifier].append(now)
        return True

# (Moved rate limiter initialization below cache_manager definition)


# Database Manager
class EnhancedDatabaseManager:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None
        self.connection_retry_count = 0
        self.max_retries = 3
        
    async def initialize(self):
        """Initialize database with retry logic."""
        for attempt in range(self.max_retries):
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    min_size=5,
                    max_size=20,
                    max_queries=50000,
                    max_inactive_connection_lifetime=300,
                    command_timeout=60
                )
                await self._ensure_tables()
                logger.info("✅ Database connection established")
                return
                
            except Exception as e:
                self.connection_retry_count = attempt + 1
                logger.error(f"❌ Database connection attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise ConnectionError(f"Failed to connect to database after {self.max_retries} attempts")
    
    async def get_connection(self):
        """Get database connection with health check."""
        if not self.pool:
            raise ConnectionError("Database not initialized")
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
                return conn
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            # Attempt to reinitialize
            await self.initialize()
            return await self.pool.acquire()
        
async def get_connection_with_retry(self):
    """Get database connection with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if not self.pool:
                await self.initialize()
            
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")  # Health check
                return conn
        except Exception as e:
            logger.error(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise ConnectionError(f"Failed to connect to database after {max_retries} attempts")

async def get_user_role(self, username: str) -> str:
    """Get user role from database."""
    try:
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT role FROM users WHERE username = $1", username
            )
            return result if result else UserRole.USER
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return UserRole.USER
    
    async def _ensure_tables(self):
    """Ensure all required tables exist with proper indexes."""
    async with self.pool.acquire() as conn:
        await conn.execute("""
            -- Users table with proper constraints
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                mobile VARCHAR(10) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(32) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                email_verified BOOLEAN DEFAULT false,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP NULL
            );
            
            -- Indexes for performance
            CREATE INDEX IF NOT EXISTS idx_users_mobile ON users(mobile);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
            CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
            
            -- Sessions table
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_token VARCHAR(255) PRIMARY KEY,
                username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address INET,
                user_agent TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_sessions_username ON user_sessions(username);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);
            
            -- GST searches table
            CREATE TABLE IF NOT EXISTS gst_searches (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
                gstin VARCHAR(15) NOT NULL,
                company_name VARCHAR(255),
                search_data JSONB,
                compliance_score INTEGER,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_searches_username ON gst_searches(username);
            CREATE INDEX IF NOT EXISTS idx_searches_gstin ON gst_searches(gstin);
            CREATE INDEX IF NOT EXISTS idx_searches_date ON gst_searches(searched_at);
            CREATE INDEX IF NOT EXISTS idx_searches_data ON gst_searches USING GIN(search_data);
            
            -- User preferences table
            CREATE TABLE IF NOT EXISTS user_preferences (
                username VARCHAR(50) PRIMARY KEY,
                preferences JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_user_preferences_username ON user_preferences(username);
            
            -- Error logs table
            CREATE TABLE IF NOT EXISTS error_logs (
                id SERIAL PRIMARY KEY,
                error_type VARCHAR(50),
                message TEXT,
                stack_trace TEXT,
                url TEXT,
                user_agent TEXT,
                username VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_errors_type ON error_logs(error_type);
            CREATE INDEX IF NOT EXISTS idx_errors_date ON error_logs(created_at);
            
            -- Search history table (if different from gst_searches)
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                mobile VARCHAR(10) NOT NULL,
                gstin VARCHAR(15) NOT NULL,
                company_name TEXT NOT NULL,
                compliance_score DECIMAL(5,2),
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);
            CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);
            CREATE INDEX IF NOT EXISTS idx_search_history_gstin ON search_history(gstin);
        """)
        
        print("✅ Database tables and indexes created successfully")

    async def create_user(self, mobile: str, password_hash: str, salt: str) -> bool:
        """Create a new user."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO users (mobile, password_hash, salt) VALUES ($1, $2, $3)",
                    mobile, password_hash, salt
                )
                return True
        except asyncpg.UniqueViolationError:
            return False

    async def verify_user(self, mobile: str, password: str) -> bool:
        """Verify user credentials."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash, salt FROM users WHERE mobile=$1", mobile
            )
            if not row:
                return False
            return self._check_password(password, row['password_hash'], row['salt'])

    async def change_password(self, mobile: str, old_password: str, new_password: str) -> bool:
        """Change user password after verifying old password."""
        async with self.pool.acquire() as conn:
            # Verify old password
            row = await conn.fetchrow("SELECT password_hash, salt FROM users WHERE mobile=$1", mobile)
            if not row or not self._check_password(old_password, row['password_hash'], row['salt']):
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
        """Create a new session for user."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + config.SESSION_DURATION
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO sessions (session_token, mobile, expires_at) VALUES ($1, $2, $3)",
                    session_token, mobile, expires_at
                )
            return session_token
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None

    async def get_session(self, session_token: str) -> Optional[str]:
        """Get user from session token."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT mobile, expires_at FROM sessions WHERE session_token=$1",
                session_token
            )
            if row and row['expires_at'] > datetime.now():
                return row['mobile']
        return None

    async def delete_session(self, session_token: str):
        """Delete a session."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM sessions WHERE session_token=$1", session_token)

    async def update_last_login(self, mobile: str):
        """Update user's last login time."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login=$1 WHERE mobile=$2", 
                datetime.now(), mobile
            )

    async def add_search_history(self, mobile: str, gstin: str, 
                               company_name: str, compliance_score: Optional[float] = None):
        """Add search to history."""
        async with self.pool.acquire() as conn:
            # Keep only latest entries per user
            await conn.execute("""
                DELETE FROM search_history 
                WHERE mobile = $1 AND id NOT IN (
                    SELECT id FROM search_history 
                    WHERE mobile = $1 
                    ORDER BY searched_at DESC 
                    LIMIT $2
                )
            """, mobile, config.MAX_SEARCH_HISTORY - 1)
            
            await conn.execute(
                "INSERT INTO search_history (mobile, gstin, company_name, compliance_score) VALUES ($1, $2, $3, $4)",
                mobile, gstin, company_name, compliance_score
            )

    async def get_search_history(self, mobile: str, limit: int = 10) -> List[Dict]:
        """Get user's search history."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=$1 ORDER BY searched_at DESC LIMIT $2",
                mobile, limit
            )
            return [dict(row) for row in rows]

    async def get_all_searches(self, mobile: str) -> List[Dict]:
        """Get all user searches for history page."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT gstin, company_name, searched_at, compliance_score FROM search_history WHERE mobile=$1 ORDER BY searched_at DESC",
                mobile
            )
            return [dict(row) for row in rows]

    async def get_user_stats(self, mobile: str) -> Dict:
        """Get comprehensive user statistics."""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_searches,
                    COUNT(DISTINCT gstin) as unique_companies,
                    AVG(compliance_score) as avg_compliance,
                    COUNT(CASE WHEN searched_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_searches,
                    MAX(searched_at) as last_search
                FROM search_history 
                WHERE mobile = $1
            """, mobile)
            
            return {
                "total_searches": stats["total_searches"] or 0,
                "unique_companies": stats["unique_companies"] or 0,
                "avg_compliance": float(stats["avg_compliance"]) if stats["avg_compliance"] else 0,
                "recent_searches": stats["recent_searches"] or 0,
                "last_search": stats["last_search"].isoformat() if stats["last_search"] else None,
                "user_level": self._get_user_level(stats["total_searches"] or 0),
                "achievements": self._get_achievements(stats["total_searches"] or 0)
            }

    async def get_analytics_data(self, mobile: str) -> Dict:
        """Get analytics data for charts."""
        async with self.pool.acquire() as conn:
            # Daily searches for last 7 days
            daily_searches = await conn.fetch("""
                SELECT DATE(searched_at) as date, COUNT(*) as search_count, AVG(compliance_score) as avg_score
                FROM search_history WHERE mobile = $1 AND searched_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE(searched_at) ORDER BY date
            """, mobile)
        
            # Score distribution
            score_distribution = await conn.fetch("""
                SELECT CASE WHEN compliance_score >= 90 THEN 'Excellent (90-100%)'
                            WHEN compliance_score >= 80 THEN 'Very Good (80-89%)'
                            WHEN compliance_score >= 70 THEN 'Good (70-79%)'
                            WHEN compliance_score >= 60 THEN 'Average (60-69%)'
                            ELSE 'Poor (<60%)' END as range, COUNT(*) as count
                FROM search_history WHERE mobile = $1 AND compliance_score IS NOT NULL 
                GROUP BY range ORDER BY range DESC
            """, mobile)
        
            # Top companies
            top_companies = await conn.fetch("""
                SELECT company_name, gstin, COUNT(*) as search_count, MAX(compliance_score) as latest_score
                FROM search_history WHERE mobile = $1 GROUP BY company_name, gstin
                ORDER BY search_count DESC LIMIT 10
            """, mobile)
        
            # Convert date objects to strings to fix JSON serialization
            daily_searches_serializable = []
            for row in daily_searches:
                row_dict = dict(row)
                if row_dict.get('date'):
                    row_dict['date'] = row_dict['date'].isoformat()
                daily_searches_serializable.append(row_dict)
        
            return {
                "daily_searches": daily_searches_serializable,
                "score_distribution": [dict(row) for row in score_distribution],
                "top_companies": [dict(row) for row in top_companies]
            }

    def _get_user_level(self, total_searches: int) -> Dict:
        """Determine user level based on activity."""
        levels = [
            (100, "Expert", "fas fa-crown", "#f59e0b"),
            (50, "Advanced", "fas fa-star", "#3b82f6"),
            (20, "Intermediate", "fas fa-chart-line", "#10b981"),
            (5, "Beginner", "fas fa-seedling", "#8b5cf6"),
            (0, "New User", "fas fa-user-plus", "#6b7280")
        ]
        
        for threshold, level, icon, color in levels:
            if total_searches >= threshold:
                return {"level": level, "icon": icon, "color": color}
        
        return {"level": levels[-1][1], "icon": levels[-1][2], "color": levels[-1][3]}

    def _get_achievements(self, total_searches: int) -> List[Dict]:
        """Get user achievements."""
        achievements = []
        
        achievement_data = [
            (1, "First Search", "Completed your first GST search", "fas fa-search"),
            (10, "Research Enthusiast", "Completed 10 searches", "fas fa-chart-bar"),
            (50, "Compliance Expert", "Completed 50 searches", "fas fa-medal"),
        ]
        
        for threshold, title, desc, icon in achievement_data:
            achievements.append({
                "title": title,
                "description": desc,
                "icon": icon,
                "unlocked": total_searches >= threshold
            })
        
        return achievements

    async def save_user_preferences(self, mobile: str, preferences: Dict):
        """Save user preferences."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_preferences (mobile, preferences, updated_at) 
                VALUES ($1, $2, $3)
                ON CONFLICT (mobile) 
                DO UPDATE SET preferences = $2, updated_at = $3
            """, mobile, json.dumps(preferences), datetime.now())

    async def get_user_preferences(self, mobile: str) -> Dict:
        """Get user preferences."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT preferences FROM user_preferences WHERE mobile = $1", mobile
            )
            return json.loads(row['preferences']) if row else {}

    async def save_user_profile(self, mobile: str, profile_data: Dict):
        """Save user profile information."""
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

    async def get_user_profile(self, mobile: str) -> Dict:
        """Get user profile information."""
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

    async def clear_user_data(self, mobile: str) -> int:
        """Clear user search history."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("DELETE FROM search_history WHERE mobile = $1 RETURNING COUNT(*)", mobile)
            return result or 0

    def _check_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash."""
        hash_attempt = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), 
            salt.encode('utf-8'), 100000, dklen=64
        ).hex()
        return hash_attempt == stored_hash

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM sessions WHERE expires_at < $1', datetime.now())

    async def log_error_to_db(self, error_data: Dict):
        """Log errors to database for analysis."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO error_logs (
                        error_type, message, stack_trace, url, user_agent, 
                        user_mobile, created_at, additional_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                    error_data.get('type'),
                    error_data.get('message'),
                    error_data.get('stack'),
                    error_data.get('url'),
                    error_data.get('userAgent'),
                    error_data.get('user_mobile'),
                    datetime.now(),
                    json.dumps(error_data.get('context', {}))
                )
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")

    async def get_error_analytics(self, days: int = 30) -> Dict:
        """Get error analytics for the dashboard."""
        try:
            async with self.pool.acquire() as conn:
                # Error count by type
                error_types = await conn.fetch("""
                    SELECT error_type, COUNT(*) as count
                    FROM error_logs 
                    WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                    GROUP BY error_type
                    ORDER BY count DESC
                    LIMIT 10
                """, days)
                
                # Daily error counts
                daily_errors = await conn.fetch("""
                    SELECT DATE(created_at) as date, COUNT(*) as error_count
                    FROM error_logs
                    WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """, days)
                
                # Most frequent errors
                frequent_errors = await conn.fetch("""
                    SELECT message, COUNT(*) as count, MAX(created_at) as last_seen
                    FROM error_logs
                    WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                    GROUP BY message
                    ORDER BY count DESC
                    LIMIT 5
                """, days)
                
                return {
                    'error_types': [dict(row) for row in error_types],
                    'daily_errors': [dict(row) for row in daily_errors],
                    'frequent_errors': [dict(row) for row in frequent_errors],
                    'total_errors': sum(row['count'] for row in error_types)
                }
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {'error_types': [], 'daily_errors': [], 'frequent_errors': [], 'total_errors': 0}        

# Initialize database
db = EnhancedDatabaseManager(config.POSTGRES_DSN)

# ADD THIS CODE HERE - Initialize Razorpay Lending
razorpay_key = os.getenv("RAZORPAY_KEY_ID")
razorpay_secret = os.getenv("RAZORPAY_KEY_SECRET")
is_production = os.getenv("RAZORPAY_ENVIRONMENT", "test") == "live"

if razorpay_key and razorpay_secret:
    razorpay_lending_client = RazorpayLendingClient(razorpay_key, razorpay_secret, is_production)
    loan_manager = LoanManager(razorpay_lending_client, db)
else:
    razorpay_lending_client = None
    loan_manager = None

# GST API Client
class GSTAPIClient:
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": host,
            "User-Agent": "GST-Intelligence-Platform/2.0"
        }
    
    async def fetch_gstin_data(self, gstin: str) -> Dict:
        """Fetch GSTIN data from API."""
        import httpx
        url = f"https://{self.host}/free/gstin/{gstin}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self.headers)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and "data" in data:
                    return data["data"]
                elif "data" in data:
                    return data["data"]
                else:
                    return data
            
            raise HTTPException(
                status_code=404, 
                detail="GSTIN not found or API error"
            )

# Initialize API client
api_client = GSTAPIClient(config.RAPIDAPI_KEY, config.RAPIDAPI_HOST) if config.RAPIDAPI_KEY else None

# Add cache-aware API functions
async def get_cached_gstin_data(gstin: str) -> Optional[Dict]:
    """Get GSTIN data from cache first, then API."""
    cache_key = f"gstin:{gstin}"
    
    # Try cache first
    cached_data = await cache_manager.get(cache_key)
    if cached_data:
        logger.info(f"Cache hit for GSTIN: {gstin}")
        return cached_data
    
    # Cache miss - fetch from API
    if api_client:
        try:
            company_data = await api_client.fetch_gstin_data(gstin)
            # Cache for 1 hour
            await cache_manager.set(cache_key, company_data, ttl=3600)
            logger.info(f"Cached GSTIN data: {gstin}")
            return company_data
        except Exception as e:
            logger.error(f"API fetch failed for {gstin}: {e}")
            raise
    
    return None

# Initialize cache manager
cache_manager = CacheManager(os.getenv("REDIS_URL"))
# Initialize cache manager
cache_manager = CacheManager(os.getenv("REDIS_URL"))

# Update rate limiter initialization (now that cache_manager is defined)
login_limiter = AdvancedRateLimiter(cache_manager.redis_client if hasattr(cache_manager, 'redis_client') else None)
api_limiter = AdvancedRateLimiter(cache_manager.redis_client if hasattr(cache_manager, 'redis_client') else None)

# Validation utilities

def add_template_context(
    request: Request,
    current_user: str = None,
    user_display_name: Optional[str] = None,
    user_profile: Optional[Dict] = None,
    **kwargs
    ):
    """Helper function to ensure all templates have required context variables."""
    context = {
        "request": request,
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile or {},
        **kwargs
    }
    return context

def validate_mobile(mobile: str) -> tuple[bool, str]:
    """Validate mobile number format."""
    mobile = mobile.strip()
    if not mobile.isdigit() or len(mobile) != 10 or mobile[0] not in "6789":
        return False, "Invalid mobile number format"
    return True, ""

def validate_gstin(gstin: str) -> bool:
    """Validate GSTIN format."""
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    return bool(re.match(pattern, gstin.upper()))

def calculate_return_due_date(return_type: str, tax_period: str, fy: str) -> Optional[datetime]:
    """Calculate due date for GST returns."""
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
    """Analyze late filing patterns."""
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

def calculate_compliance_score(company_data: Dict) -> float:
    """Calculate compliance score based on company data."""
    score = 100.0
    
    # Registration Status (25 points)
    if company_data.get("sts") != "Active":
        score -= 25
    
    # Filing Compliance (20 points)
    returns = company_data.get("returns", [])
    if returns:
        current_date = datetime.now()
        gstr1_returns = [r for r in returns if r.get("rtntype") == "GSTR1"]
        
        # Calculate expected returns based on registration date
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

def generate_pdf_report(company_data: Dict, compliance_score: float, synopsis: str = None, late_filing_analysis: Dict = None) -> BytesIO:
    """Generate comprehensive PDF report."""
    company_name = html.escape(company_data.get("lgnm", "Unknown Company"))
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
        
        {f'<div style="background: #e0e7ff; border-radius: 12px; padding: 20px; margin-bottom: 20px;"><h3>Company Overview</h3><p>{html.escape(synopsis)}</p></div>' if synopsis else ''}
        
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

async def get_user_display_name(mobile: str) -> str:
    """Get user display name or fallback to mobile."""
    try:
        profile = await db.get_user_profile(mobile)
        display_name = profile.get('display_name')
        if display_name:
            return display_name
        return f"User {mobile[-4:]}"
    except:
        return f"User {mobile[-4:]}"

# Authentication dependencies
async def get_current_user(request: Request) -> Optional[str]:
    """Get current user from session."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    return await db.get_session(session_token)

async def require_auth(request: Request) -> str:
    """Require authentication for protected routes."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"}
        )
    return user

# Admin authentication decorator
class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user" 
    VIEWER = "viewer"

class SecurityManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        
    def create_access_token(self, data: dict) -> str:
        """Create a secure JWT token."""
        to_encode = data.copy()
        expire = datetime.now() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    def hash_password(self, password: str) -> str:
        """Hash password with salt."""
        password_hash = security_manager.hash_password(password)
    
    def verify_password(self, stored_password: str, provided_password: str) -> bool:
        """Verify password against hash."""
        salt = stored_password[:32]
        stored_hash = stored_password[32:]
        pwdhash = hashlib.pbkdf2_hmac('sha256',
                                      provided_password.encode('utf-8'),
                                      salt.encode('utf-8'),
                                      100000)
        return pwdhash.hex() == stored_hash

# Initialize security manager
security_manager = SecurityManager(config.SECRET_KEY)

# Enhanced role-based authentication
async def require_role(required_role: UserRole):
    """Enhanced role-based authentication decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = await get_current_user(request)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_role = await db.get_user_role(user)
            if not has_permission(user_role, required_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def has_permission(user_role: str, required_role: UserRole) -> bool:
    """Check if user role has required permissions."""
    role_hierarchy = {
        UserRole.VIEWER: 1,
        UserRole.USER: 2,  
        UserRole.ADMIN: 3
    }
    
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level

# Updated admin requirement using new system
async def require_admin(request: Request) -> str:
    """Require admin authentication with enhanced security."""
    return await require_role(UserRole.ADMIN)(lambda r: get_current_user(r))(request)



# Main Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        async with db.pool.acquire() as conn:
            await conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "checks": {
                "database": "healthy",
                "gst_api": "configured" if config.RAPIDAPI_KEY else "missing",
                "ai_features": "configured" if config.ANTHROPIC_API_KEY else "disabled",
                "cache": "redis" if cache_manager.redis_client else "memory"
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
async def dashboard(request: Request, current_user: str = Depends(require_auth)):
    """Main dashboard page."""
    history = await db.get_search_history(current_user)
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
    # Calculate recent activity
    now = datetime.now()
    last_30_days = now - timedelta(days=30)
    searches_this_month = sum(
        1 for item in history
        if item.get('searched_at') and item['searched_at'] >= last_30_days
    )
    
    context = add_template_context(
        request=request,
        current_user=current_user,
        user_display_name=user_display_name,
        user_profile=user_profile,
        history=history,
        searches_this_month=searches_this_month
    )
    
    return templates.TemplateResponse("index.html", context)

# Admin Dashboard Routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: str = Depends(require_admin)):
    """Admin dashboard page."""
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
    return templates.TemplateResponse("admin_dashboard.html", {  # Use dashboard.html, not admin/dashboard.html
        "request": request,
        "current_user": current_user,
        "user_display_name": user_display_name,
        "user_profile": user_profile
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    # Check if user is already logged in
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "current_user": None,  # Explicitly set to None for login page
        "user_display_name": None,
        "user_profile": None
    })

@app.post("/login")
async def login(request: Request, mobile: str = Form(...), password: str = Form(...)):
    """Handle login."""
    client_ip = request.client.host
    is_allowed = await login_limiter.is_allowed(f"login:{client_ip}", 5, 900)  # 5 attempts per 15 min
    
    if not is_allowed:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Too many login attempts. Please try again later."
        })
    
    if not login_limiter.is_allowed(mobile):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Too many login attempts. Please try again later."
        })
    
    if not await db.verify_user(mobile, password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid credentials"
        })
    
    session_token = await db.create_session(mobile)
    if not session_token:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Failed to create session"
        })
    
    await db.update_last_login(mobile)
    
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=int(config.SESSION_DURATION.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )
    return response

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page."""
    # Check if user is already logged in
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
        
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "current_user": None,  # Explicitly set to None for signup page
        "user_display_name": None,
        "user_profile": None
    })

@app.post("/signup")
async def signup(request: Request, mobile: str = Form(...), 
                password: str = Form(...), confirm_password: str = Form(...)):
    """Handle signup."""
    is_valid, message = validate_mobile(mobile)
    if not is_valid:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": message
        })
    
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
    
    # Create password hash
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), 
        salt.encode('utf-8'), 100000, dklen=64
    ).hex()
    
    success = await db.create_user(mobile, password_hash, salt)
    if not success:
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Mobile number already registered"
        })
    
    return RedirectResponse(url="/login?registered=true", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    """Handle logout."""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.delete_session(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

@app.get("/search")
async def search_gstin_get(request: Request, gstin: str = None, current_user: str = Depends(require_auth)):
    """Handle GET search requests."""
    if not gstin:
        return RedirectResponse(url="/", status_code=302)
    
    return await process_search(request, gstin, current_user)

def sanitize_input(value: str, max_length: int = 255) -> str:
    """Sanitize input string by removing control characters and truncating."""
    if not value:
        return ""
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(value))
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    return sanitized

@app.post("/api/system/error")
@handle_api_errors
async def log_frontend_error(error_data: ErrorLogRequest):
    """Enhanced frontend error logging."""
    try:
        # Sanitize error data
        sanitized_data = {
            'type': sanitize_input(error_data.type, 50),
            'message': sanitize_input(error_data.message, 500),
            'url': sanitize_input(error_data.url or '', 200),
            'userAgent': sanitize_input(error_data.userAgent or '', 300),
            'timestamp': error_data.timestamp or datetime.now().isoformat(),
            'stack': sanitize_input(error_data.stack or '', 2000)
        }
        
        # Log with appropriate level based on error type
        if 'TypeError' in sanitized_data['message'] or 'ReferenceError' in sanitized_data['message']:
            logger.error(f"Frontend Error: {sanitized_data}")
        else:
            logger.warning(f"Frontend Warning: {sanitized_data}")
        
        # Store in database for analysis (optional)
        # await db.store_error_log(sanitized_data)
        
        return {"success": True, "message": "Error logged successfully"}
        
    except Exception as e:
        logger.error(f"Failed to log frontend error: {e}")
        return {"success": False, "error": "Failed to log error"}

# Fix the process_search function to use web scraping + AI
async def process_search(request: Request, gstin: str, current_user: str):
    """Process GST search request."""
    gstin = gstin.strip().upper()
    if not validate_gstin(gstin):
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user, 
            "error": "Invalid GSTIN format", 
            "history": history
        })
    
    if not api_limiter.is_allowed(current_user):
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user, 
            "error": "API rate limit exceeded. Please try again later.", 
            "history": history
        })
    
    try:
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await get_cached_gstin_data(gstin)
        if not company_data:
            raise HTTPException(status_code=503, detail="GST API service not available")
        
        # Calculate compliance score
        compliance_score = calculate_compliance_score(company_data)
        logger.info(f"Final compliance score for template: {compliance_score}")
        
        # Enhanced AI synopsis with web scraping

        synopsis = None
        if config.ANTHROPIC_API_KEY:
            try:
                    logger.info("Generating AI synopsis with web intelligence...")
                    synopsis = await get_anthropic_synopsis(company_data, compliance_score)
                    if synopsis:
                        logger.info(f"AI synopsis generated successfully: {synopsis[:100]}...")
                    else:
                        logger.warning("AI synopsis generation returned empty result")
            except Exception as e:
                        logger.error(f"AI synopsis generation failed: {e}")
                        synopsis = None
        
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
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        history = await db.get_search_history(current_user)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "current_user": current_user, 
            "error": "An error occurred while searching. Please try again.", 
            "history": history
        })

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, current_user: str = Depends(require_auth)):
    """Search history page."""
    history = await db.get_all_searches(current_user)
    user_profile = await db.get_user_profile(current_user)
    user_display_name = await get_user_display_name(current_user)
    
    # Calculate recent activity
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
async def analytics_page(request: Request, current_user: str = Depends(require_auth)):
    """Analytics dashboard page."""
    try:
        user_profile = await db.get_user_profile(current_user)
        user_display_name = await get_user_display_name(current_user)
        
        # Get analytics data with better error handling
        try:
            analytics_data = await db.get_analytics_data(current_user)
        except Exception as e:
            logger.error(f"Analytics data error: {e}")
            analytics_data = {
                "daily_searches": [],
                "score_distribution": [],
                "top_companies": []
            }
        
        # Get overall stats
        try:
            stats = await db.get_user_stats(current_user)
        except Exception as e:
            logger.error(f"User stats error: {e}")
            stats = {
                "total_searches": 0,
                "unique_companies": 0,
                "avg_compliance": 0,
                "recent_searches": 0
            }
        
        # Calculate recent activity
        now = datetime.now()
        last_30_days = now - timedelta(days=30)
        
        # Get history for recent searches calculation
        try:
            history = await db.get_search_history(current_user)
            searches_this_month = sum(
                1 for item in history
                if item.get('searched_at') and item['searched_at'] >= last_30_days
            )
        except Exception as e:
            logger.error(f"History data error: {e}")
            searches_this_month = 0
        
        return templates.TemplateResponse("analytics.html", {
            "request": request, 
            "current_user": current_user,
            "user_display_name": user_display_name,
            "user_profile": user_profile,
            "daily_searches": analytics_data.get("daily_searches", []),
            "score_distribution": analytics_data.get("score_distribution", []),
            "top_companies": analytics_data.get("top_companies", []),
            "total_searches": stats.get("total_searches", 0),
            "unique_companies": stats.get("unique_companies", 0),
            "avg_compliance": stats.get("avg_compliance", 0),
            "searches_this_month": searches_this_month
        })
    except Exception as e:
        logger.error(f"Analytics page error: {e}")
        # Fallback response with empty data
        return templates.TemplateResponse("analytics.html", {
            "request": request, 
            "current_user": current_user,
            "user_display_name": current_user[-4:] if current_user else "User",
            "user_profile": {},
            "daily_searches": [],
            "score_distribution": [],
            "top_companies": [],
            "total_searches": 0,
            "unique_companies": 0,
            "avg_compliance": 0,
            "searches_this_month": 0
        })
    
@app.get("/loans", response_class=HTMLResponse)
async def loans_page(request: Request, current_user: str = Depends(require_auth)):
    """Loans dashboard page"""
    try:
        # Get user's loan applications
        applications = []
        if loan_manager:
            applications = await loan_manager.get_user_loan_applications(current_user)
        
        # Get user profile for pre-filling forms
        user_profile = await db.get_user_profile(current_user)
        user_display_name = await get_user_display_name(current_user)
        
        return templates.TemplateResponse("loans.html", {
            "request": request,
            "current_user": current_user,
            "user_display_name": user_display_name,
            "user_profile": user_profile,
            "applications": applications,
            "loan_config": {
                "min_amount": LoanConfig.MIN_LOAN_AMOUNT,
                "max_amount": LoanConfig.MAX_LOAN_AMOUNT,
                "min_compliance": LoanConfig.MIN_COMPLIANCE_SCORE,
                "min_vintage": LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS
            }
        })
    except Exception as e:
        logger.error(f"Loans page error: {e}")
        return templates.TemplateResponse("loans.html", {
            "request": request,
            "current_user": current_user,
            "error": "Unable to load loans page"
        })

# API Routes
@app.get("/api/user/stats")
@handle_api_errors
async def get_user_stats_api(current_user: str = Depends(require_auth)):
    """Get user statistics API."""
    stats = await db.get_user_stats(current_user)
    return {"success": True, "data": stats}

@app.post("/api/user/change-password")
@handle_api_errors
async def change_password_api(request: ChangePasswordRequest, current_user: str = Depends(require_auth)):
    """Change user password API."""
    success = await db.change_password(current_user, request.currentPassword, request.newPassword)
    
    if success:
        return {"success": True, "message": "Password changed successfully"}
    else:
        return {"success": False, "message": "Current password is incorrect"}

@app.get("/api/user/preferences")
@handle_api_errors
async def get_user_preferences_api(current_user: str = Depends(require_auth)):
    """Get user preferences API."""
    preferences = await db.get_user_preferences(current_user)
    return {"success": True, "data": preferences}

@app.post("/api/user/preferences")
@handle_api_errors
async def save_user_preferences_api(request: UserPreferencesRequest, current_user: str = Depends(require_auth)):
    """Save user preferences API."""
    preferences = request.dict()
    await db.save_user_preferences(current_user, preferences)
    return {"success": True, "message": "Preferences saved successfully"}

@app.get("/api/user/profile")
@handle_api_errors
async def get_user_profile_api(current_user: str = Depends(require_auth)):
    """Get user profile API."""
    profile = await db.get_user_profile(current_user)
    return {"success": True, "data": profile}

@app.post("/api/user/profile")
@handle_api_errors
async def save_user_profile_api(request: UserProfileRequest, current_user: str = Depends(require_auth)):
    """Save user profile API."""
    profile_data = {k: v for k, v in request.dict().items() if v is not None}
    await db.save_user_profile(current_user, profile_data)
    return {"success": True, "message": "Profile saved successfully"}

@app.delete("/api/user/data")
@handle_api_errors
async def clear_user_data_api(current_user: str = Depends(require_auth)):
    """Clear user data API."""
    deleted_count = await db.clear_user_data(current_user)
    return {"success": True, "deleted_count": deleted_count}

@app.post("/api/search/batch")
@handle_api_errors
async def batch_search_api(request: BatchSearchRequest, current_user: str = Depends(require_auth)):
    """Enhanced batch GSTIN search API with better error handling."""
    try:
        gstins = [gstin.strip().upper() for gstin in request.gstins[:10]]  # Limit to 10
        results = []
        successful = 0
        failed = 0
        
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
        
        # Rate limiting check
        if not api_limiter.is_allowed(current_user):
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": "Rate limit exceeded"}
            )
        
        for i, gstin in enumerate(gstins):
            if not validate_gstin(gstin):
                results.append({
                    'gstin': gstin,
                    'success': False,
                    'error': 'Invalid GSTIN format'
                })
                failed += 1
                continue
            
            try:
                # Add progress tracking
                logger.info(f"Processing GSTIN {i+1}/{len(gstins)}: {gstin}")
                
                company_data = await api_client.fetch_gstin_data(gstin)
                compliance_score = calculate_compliance_score(company_data)
                
                # Add to search history
                await db.add_search_history(
                    current_user, 
                    gstin, 
                    company_data.get("lgnm", "Unknown"), 
                    compliance_score
                )
                
                results.append({
                    'gstin': gstin,
                    'success': True,
                    'company_name': company_data.get('lgnm', 'Unknown'),
                    'compliance_score': compliance_score,
                    'status': company_data.get('sts', 'Unknown'),
                    'registration_date': company_data.get('rgdt'),
                    'state': company_data.get('stj', '').split('State - ')[1].split(',')[0] if 'State - ' in company_data.get('stj', '') else 'Unknown'
                })
                successful += 1
                
                # Small delay to avoid overwhelming the API
                await asyncio.sleep(0.5)
                
            except HTTPException as he:
                logger.error(f"HTTP error processing GSTIN {gstin}: {he.detail}")
                results.append({
                    'gstin': gstin,
                    'success': False,
                    'error': he.detail
                })
                failed += 1
                
            except Exception as e:
                logger.error(f"Error processing GSTIN {gstin}: {e}")
                results.append({
                    'gstin': gstin,
                    'success': False,
                    'error': 'Processing failed'
                })
                failed += 1
        
        return {
            'success': True,
            'results': results,
            'summary': {
                'total': len(gstins),
                'successful': successful,
                'failed': failed,
                'processing_time': f"{len(gstins) * 0.5:.1f}s estimated"
            }
        }
        
    except Exception as e:
        logger.error(f"Batch search error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'Batch search failed',
                'results': [],
                'summary': {'total': 0, 'successful': 0, 'failed': 0}
            }
        )
    
@app.get("/api/search/batch/status/{batch_id}")
@handle_api_errors
async def get_batch_status(batch_id: str, current_user: str = Depends(require_auth)):
    """Get status of a batch search operation."""
    # This would require implementing a background task system
    # For now, return a simple response
    return {
        'success': True,
        'batch_id': batch_id,
        'status': 'completed',
        'message': 'Batch processing completed'
    }    

@app.get("/api/search/suggestions")
@handle_api_errors
async def get_search_suggestions_api(q: str, current_user: str = Depends(require_auth)):
    """Search suggestions API."""
    try:
        if len(q) < 2:
            return {"success": True, "suggestions": []}
        
        # Get suggestions from search history
        async with db.pool.acquire() as conn:
            # Fixed SQL query - remove ORDER BY from DISTINCT query
            suggestions = await conn.fetch("""
                SELECT DISTINCT gstin, company_name, compliance_score
                FROM search_history 
                WHERE mobile = $1 
                AND (
                    UPPER(gstin) LIKE UPPER($2) 
                    OR UPPER(company_name) LIKE UPPER($2)
                )
                AND company_name IS NOT NULL
                LIMIT 5
            """, current_user, f"%{q}%")
            
            # Sort the results after fetching
            sorted_suggestions = sorted(
                [dict(row) for row in suggestions], 
                key=lambda x: x.get('searched_at', datetime.min) if hasattr(x, 'searched_at') else datetime.min, 
                reverse=True
            )
            
            formatted_suggestions = []
            for suggestion in sorted_suggestions:
                formatted_suggestions.append({
                    'gstin': suggestion['gstin'],
                    'company': suggestion['company_name'],
                    'compliance_score': suggestion.get('compliance_score'),
                    'type': 'recent',
                    'source': 'history'
                })
        
        return {"success": True, "suggestions": formatted_suggestions}
        
    except Exception as e:
        logger.error(f"Search suggestions error: {e}")
        return {"success": True, "suggestions": []}

@app.post("/api/system/error")
@handle_api_errors
async def log_frontend_error(error_data: ErrorLogRequest):
    """Enhanced frontend error logging."""
    try:
        # Sanitize error data
        sanitized_data = {
            'type': sanitize_input(error_data.type, 50),
            'message': sanitize_input(error_data.message, 500),
            'url': sanitize_input(error_data.url or '', 200),
            'userAgent': sanitize_input(error_data.userAgent or '', 300),
            'timestamp': error_data.timestamp or datetime.now().isoformat(),
            'stack': sanitize_input(error_data.stack or '', 2000)
        }
        
        # Log with appropriate level based on error type
        if 'TypeError' in sanitized_data['message'] or 'ReferenceError' in sanitized_data['message']:
            logger.error(f"Frontend Error: {sanitized_data}")
        else:
            logger.warning(f"Frontend Warning: {sanitized_data}")
        
        # Store in database for analysis (optional)
        # await db.store_error_log(sanitized_data)
        
        return {"success": True, "message": "Error logged successfully"}
        
    except Exception as e:
        logger.error(f"Failed to log frontend error: {e}")
        return {"success": False, "error": "Failed to log error"}

@app.get("/api/user/activity")
@handle_api_errors
async def get_user_activity_api(days: int = 30, current_user: str = Depends(require_auth)):
    """User activity API."""
    try:
        analytics_data = await db.get_analytics_data(current_user)
        
        return {
            'success': True,
            'data': {
                'daily_activity': analytics_data["daily_searches"],
                'score_distribution': analytics_data["score_distribution"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return {'success': False, 'error': 'Failed to get activity data'}

@app.get("/api/system/status")
@handle_api_errors
async def get_system_status_api():
    """System status API."""
    try:
        status = {
            'database': 'healthy',
            'gst_api': 'configured' if config.RAPIDAPI_KEY else 'missing',
            'ai_service': 'configured' if config.ANTHROPIC_API_KEY else 'disabled',
            'timestamp': datetime.now().isoformat()
        }
        
        # Test database connection
        try:
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
    
@app.get("/api/system/health/detailed")
@handle_api_errors
async def detailed_health_check():
    """Comprehensive health check with metrics."""
    try:
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'version': '2.0.0',
            'uptime': time.time() - app.start_time if hasattr(app, 'start_time') else 0,
            'checks': {}
        }
        
        # Database health
        try:
            start_time = time.time()
            async with db.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            db_response_time = (time.time() - start_time) * 1000
            
            health_data['checks']['database'] = {
                'status': 'healthy',
                'response_time_ms': round(db_response_time, 2)
            }
        except Exception as e:
            health_data['checks']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_data['status'] = 'degraded'
        
        # Cache health
        cache_status = await cache_manager.get_health_status()
        health_data['checks']['cache'] = cache_status
        
        # API service health
        health_data['checks']['gst_api'] = {
            'status': 'configured' if config.RAPIDAPI_KEY else 'missing',
            'host': config.RAPIDAPI_HOST if config.RAPIDAPI_KEY else None
        }
        
        # AI service health
        health_data['checks']['ai_service'] = {
            'status': 'configured' if config.ANTHROPIC_API_KEY else 'disabled'
        }
        
        # System resources
        try:
            import psutil
            health_data['system'] = {
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'cpu_percent': psutil.cpu_percent()
            }
        except ImportError:
            health_data['system'] = {'status': 'monitoring_unavailable'}
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        )
    
# Admin API Routes
@app.get("/api/admin/stats")
@handle_api_errors
async def get_admin_stats(current_user: str = Depends(require_admin)):
    """Get comprehensive admin statistics."""
    try:
        async with db.pool.acquire() as conn:
            # User statistics
            user_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN last_login >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as active_users,
                    COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as new_users_week
                FROM users
            """)
            
            # Search statistics
            search_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_searches,
                    COUNT(CASE WHEN searched_at >= CURRENT_DATE - INTERVAL '24 hours' THEN 1 END) as searches_today,
                    COUNT(DISTINCT mobile) as unique_searchers,
                    AVG(compliance_score) as avg_compliance
                FROM search_history
            """)
            
            # Top searched companies
            top_companies = await conn.fetch("""
                SELECT gstin, company_name, COUNT(*) as search_count
                FROM search_history
                GROUP BY gstin, company_name
                ORDER BY search_count DESC
                LIMIT 10
            """)
            
            # Daily search trends (last 30 days)
            daily_trends = await conn.fetch("""
                SELECT DATE(searched_at) as date, COUNT(*) as searches
                FROM search_history
                WHERE searched_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(searched_at)
                ORDER BY date
            """)
            
            return {
                'success': True,
                'user_stats': dict(user_stats) if user_stats else {},
                'search_stats': dict(search_stats) if search_stats else {},
                'top_companies': [dict(row) for row in top_companies],
                'daily_trends': [dict(row) for row in daily_trends]
            }
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        return {'success': False, 'error': str(e)}

@app.get("/api/admin/users")
@handle_api_errors
async def get_all_users(
    page: int = 1, 
    limit: int = 50,
    search: str = "",
    current_user: str = Depends(require_admin)
):
    """Get all users with pagination and search."""
    try:
        offset = (page - 1) * limit
        
        async with db.pool.acquire() as conn:
            # Build search condition
            search_condition = ""
            params = [limit, offset]
            if search:
                search_condition = "WHERE mobile LIKE $3"
                params.append(f"%{search}%")
            
            # Get users
            query = f"""
                SELECT mobile, created_at, last_login,
                       (SELECT COUNT(*) FROM search_history WHERE search_history.mobile = users.mobile) as search_count
                FROM users
                {search_condition}
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            
            users = await conn.fetch(query, *params)
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM users {search_condition}"
            if search:
                total = await conn.fetchval(count_query, f"%{search}%")
            else:
                total = await conn.fetchval(count_query)
            
            return {
                'success': True,
                'users': [dict(row) for row in users],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit
                }
            }
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return {'success': False, 'error': str(e)}

@app.delete("/api/admin/users/{mobile}")
@handle_api_errors
async def delete_user(mobile: str, current_user: str = Depends(require_admin)):
    """Delete a user and all their data."""
    try:
        async with db.pool.acquire() as conn:
            # Check if user exists
            user = await conn.fetchrow("SELECT mobile FROM users WHERE mobile = $1", mobile)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Delete user (cascade will handle related data)
            await conn.execute("DELETE FROM users WHERE mobile = $1", mobile)
            
            return {'success': True, 'message': f'User {mobile} deleted successfully'}
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return {'success': False, 'error': str(e)}

@app.get("/api/admin/system/health")
@handle_api_errors
async def system_health_check(current_user: str = Depends(require_admin)):
    """Comprehensive system health check."""
    try:
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'database': 'unknown',
            'api_service': 'unknown',
            'cache': 'unknown',
            'disk_space': 'unknown',
            'memory_usage': 'unknown'
        }
        
        # Database health
        try:
            async with db.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            health_data['database'] = 'healthy'
        except Exception as e:
            health_data['database'] = f'unhealthy: {str(e)}'
        
        # API service health
        if api_client and config.RAPIDAPI_KEY:
            health_data['api_service'] = 'configured'
        else:
            health_data['api_service'] = 'not configured'
        
        # Cache health
        try:
            await cache_manager.set('health_check', True, ttl=60)
            health_check_value = await cache_manager.get('health_check')
            health_data['cache'] = 'healthy' if health_check_value else 'unhealthy'
        except Exception as e:
            health_data['cache'] = f'unhealthy: {str(e)}'
        
        # System resources
        try:
            import psutil
            health_data['memory_usage'] = f"{psutil.virtual_memory().percent}%"
            health_data['disk_space'] = f"{psutil.disk_usage('/').percent}%"
        except ImportError:
            health_data['memory_usage'] = 'psutil not available'
            health_data['disk_space'] = 'psutil not available'
        
        return {'success': True, 'health': health_data}
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {'success': False, 'error': str(e)}

# Bulk operations
@app.post("/api/admin/bulk/delete-old-searches")
@handle_api_errors
async def bulk_delete_old_searches(
    days_old: int = 90,
    current_user: str = Depends(require_admin)
):
    """Delete search history older than specified days."""
    try:
        async with db.pool.acquire() as conn:
            result = await conn.fetchval("""
                DELETE FROM search_history 
                WHERE searched_at < CURRENT_DATE - INTERVAL '%s days'
                RETURNING COUNT(*)
            """, days_old)
            
            return {
                'success': True,
                'deleted_count': result or 0,
                'days_old': days_old
            }
    except Exception as e:
        logger.error(f"Bulk delete error: {e}")
        return {'success': False, 'error': str(e)}    
    
@app.get("/api/admin/cache/stats")
@handle_api_errors
async def get_cache_stats(current_user: str = Depends(require_auth)):
    """Get cache statistics."""
    try:
        if cache_manager.redis_client:
            info = cache_manager.redis_client.info()
            return {
                'success': True,
                'cache_type': 'redis',
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses')
            }
        else:
            return {
                'success': True,
                'cache_type': 'memory',
                'entries': len(cache_manager.memory_cache),
                'memory_usage': f"{len(str(cache_manager.memory_cache))} bytes (approx)"
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.delete("/api/admin/cache/clear")
@handle_api_errors  
async def clear_cache(pattern: str = "*", current_user: str = Depends(require_auth)):
    """Clear cache entries by pattern."""
    try:
        count = await cache_manager.clear_pattern(pattern)
        return {
            'success': True,
            'cleared_count': count,
            'pattern': pattern
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}    

# Export and PDF Routes
@app.get("/export/history")
async def export_history(current_user: str = Depends(require_auth)):
    """Export search history as CSV."""
    try:
        history = await db.get_all_searches(current_user)
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['searched_at', 'gstin', 'company_name', 'compliance_score'])
        writer.writeheader()
        
        for item in history:
            writer.writerow({
                'searched_at': item['searched_at'].isoformat() if item['searched_at'] else '',
                'gstin': item['gstin'],
                'company_name': item['company_name'],
                'compliance_score': item['compliance_score'] if item['compliance_score'] else ''
            })
        
        content = output.getvalue()
        output.close()
        
        return StreamingResponse(
            BytesIO(content.encode()), 
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=gst_search_history_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

@app.post("/generate-pdf")
async def generate_pdf_route(request: Request, gstin: str = Form(...), current_user: str = Depends(require_auth)):
    """Generate PDF report."""
    if not HAS_WEASYPRINT:
        raise HTTPException(status_code=503, detail="PDF generation not available")
    
    try:
        if not api_client:
            raise HTTPException(status_code=503, detail="GST API service not configured")
            
        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)
        
        synopsis = None
        if config.ANTHROPIC_API_KEY:
            try:
                synopsis = await get_anthropic_synopsis(company_data)
            except:
                synopsis = "AI synopsis not available"
        
        late_filing_analysis = company_data.get('_late_filing_analysis', None)
        pdf_content = generate_pdf_report(company_data, compliance_score, synopsis, late_filing_analysis)
        
        return StreamingResponse(
            pdf_content, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=GST_Report_{gstin}.pdf"}
        )
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

# Static file routes
@app.get("/favicon.ico")
async def favicon():
    """Favicon route."""
    # Simple 1x1 PNG favicon
    favicon_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x01\x8d\xc8\x02\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(content=favicon_bytes, media_type="image/png")

@app.get("/manifest.json")
async def get_manifest():
    """PWA manifest route."""
    with open("static/manifest.json", "r") as f:
        manifest_content = f.read()
    return Response(content=manifest_content, media_type="application/json")

@app.get("/sw.js")
async def get_service_worker():
    """Service worker route."""
    with open("sw.js", "r") as f:
        sw_content = f.read()
    return Response(content=sw_content, media_type="application/javascript")

@app.post("/api/loans/apply")
@handle_api_errors
async def apply_for_loan(request: LoanApplicationRequest, current_user: str = Depends(require_auth)):
    """Apply for a business loan"""
    try:
        if not loan_manager:
            return JSONResponse(
                status_code=503,
                content={"success": False, "error": "Loan service not available"}
            )
        
        # Validate application data
        application_data = request.dict()
        is_valid, message = LoanConfig.validate_loan_application(application_data)
        
        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": message}
            )
        
        # Submit loan application
        result = await loan_manager.submit_loan_application(current_user, application_data)
        
        if result["success"]:
            return {"success": True, "data": result, "message": "Loan application submitted successfully"}
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result.get("error", "Application failed")}
            )
            
    except Exception as e:
        logger.error(f"Loan application error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to process loan application"}
        )

@app.get("/api/loans/applications")
@handle_api_errors
async def get_loan_applications(current_user: str = Depends(require_auth)):
    """Get user's loan applications"""
    try:
        if not loan_manager:
            return {"success": True, "data": []}
        
        applications = await loan_manager.get_user_loan_applications(current_user)
        return {"success": True, "data": applications}
        
    except Exception as e:
        logger.error(f"Get loan applications error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to fetch loan applications"}
        )

@app.get("/api/loans/applications/{application_id}/offers")
@handle_api_errors
async def get_loan_offers(application_id: int, current_user: str = Depends(require_auth)):
    """Get loan offers for an application"""
    try:
        if not loan_manager:
            return {"success": True, "data": []}
        
        # Verify application belongs to user
        async with db.pool.acquire() as conn:
            app_owner = await conn.fetchval(
                "SELECT user_mobile FROM loan_applications WHERE id = $1",
                application_id
            )
            
            if app_owner != current_user:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "Access denied"}
                )
            
            # Get offers from database
            offers = await conn.fetch("""
                SELECT razorpay_offer_id, loan_amount, interest_rate, 
                       tenure_months, emi_amount, processing_fee, 
                       is_accepted, created_at, offer_data
                FROM loan_offers 
                WHERE application_id = $1
                ORDER BY created_at DESC
            """, application_id)
            
            return {"success": True, "data": [dict(offer) for offer in offers]}
            
    except Exception as e:
        logger.error(f"Get loan offers error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to fetch loan offers"}
        )

@app.get("/api/loans/eligibility")
@handle_api_errors
async def check_loan_eligibility(
    gstin: str, 
    annual_turnover: float,
    compliance_score: float,
    business_vintage_months: int,
    current_user: str = Depends(require_auth)
):
    """Check loan eligibility for a business"""
    try:
        # Basic eligibility check
        eligibility = {
            "eligible": True,
            "reasons": [],
            "max_loan_amount": 0,
            "recommended_amount": 0
        }
        
        # Check compliance score
        if compliance_score < LoanConfig.MIN_COMPLIANCE_SCORE:
            eligibility["eligible"] = False
            eligibility["reasons"].append(f"Compliance score below minimum ({LoanConfig.MIN_COMPLIANCE_SCORE}%)")
        
        # Check business vintage
        if business_vintage_months < LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS:
            eligibility["eligible"] = False
            eligibility["reasons"].append(f"Business vintage below minimum ({LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS} months)")
        
        # Check annual turnover
        if annual_turnover < LoanConfig.MIN_ANNUAL_TURNOVER:
            eligibility["eligible"] = False
            eligibility["reasons"].append(f"Annual turnover below minimum (₹{LoanConfig.MIN_ANNUAL_TURNOVER:,})")
        
        if eligibility["eligible"]:
            # Calculate maximum loan amount
            max_by_turnover = annual_turnover * LoanConfig.MAX_LOAN_TO_TURNOVER_RATIO
            eligibility["max_loan_amount"] = min(max_by_turnover, LoanConfig.MAX_LOAN_AMOUNT)
            
            # Recommended amount based on compliance score
            score_multiplier = compliance_score / 100
            eligibility["recommended_amount"] = min(
                annual_turnover * 0.3 * score_multiplier,
                eligibility["max_loan_amount"]
            )
        
        return {"success": True, "data": eligibility}
        
    except Exception as e:
        logger.error(f"Eligibility check error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Failed to check eligibility"}
        )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(url=exc.headers["Location"], status_code=303)
    return JSONResponse(
        status_code=exc.status_code, 
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, 
        content={"error": "An internal error occurred"}
    )

# Startup/Shutdown eventss
def validate_environment():
    """Check for required environment variables and configuration."""
    required_env_vars = [
        "POSTGRES_DSN",
        "RAPIDAPI_KEY",
        "RAPIDAPI_HOST",
        "SESSION_DURATION"
    ]
    missing = []
    for var in required_env_vars:
        if not getattr(config, var, None):
            missing.append(var)
    if missing:
        logger.warning(f"Missing required environment variables: {', '.join(missing)}")
    else:
        logger.info("All required environment variables are set.")

@app.on_event("startup")
async def startup():
    """Enhanced application startup with validation."""
    logger.info("🚀 GST Intelligence Platform starting up...")
    
    # Add app start time for monitoring
    app.start_time = time.time()
    
    # 🟢 ADD ENVIRONMENT VALIDATION HERE
    validate_environment()
    
    # Initialize database
    await db.initialize()
    await db.cleanup_expired_sessions()
    
    # Initialize loan tables if loan manager is available
    if loan_manager:
        await loan_manager.initialize_loan_tables()
        logger.info("Loan management system initialized")
    
    # Store admin users for template access
    app.extra = {"ADMIN_USERS": os.getenv("ADMIN_USERS", "")}
    
    logger.info("✅ GST Intelligence Platform started successfully")
    
@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown."""
    logger.info("GST Intelligence Platform shutting down...")
    if db.pool:
        await db.pool.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
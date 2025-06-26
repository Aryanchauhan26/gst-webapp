#!/usr/bin/env python3
"""
Data Models and Validation for GST Intelligence Platform
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import re

# =============================================
# ENUMS
# =============================================

class UserRole(str, Enum):
    """User roles enum."""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class SearchStatus(str, Enum):
    """Search status enum."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    TIMEOUT = "timeout"

class GSTINStatus(str, Enum):
    """GSTIN status enum."""
    ACTIVE = "Active"
    CANCELLED = "Cancelled"
    SUSPENDED = "Suspended"
    UNKNOWN = "Unknown"

class ThemeMode(str, Enum):
    """Theme mode enum."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

# =============================================
# BASE MODELS
# =============================================

class BaseResponse(BaseModel):
    """Base response model."""
    success: bool
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseResponse):
    """Success response model."""
    success: bool = True
    data: Optional[Any] = None

# =============================================
# USER MODELS
# =============================================

class UserSignupRequest(BaseModel):
    """User signup request model."""
    mobile: str = Field(..., min_length=10, max_length=10, description="10-digit mobile number")
    password: str = Field(..., min_length=6, max_length=128, description="Password")
    confirm_password: str = Field(..., min_length=6, max_length=128, description="Password confirmation")
    
    @validator('mobile')
    def validate_mobile(cls, v):
        """Validate mobile number format."""
        if not re.match(r'^[6-9]\d{9}$', v):
            raise ValueError('Mobile number must be 10 digits starting with 6-9')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate password confirmation."""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserLoginRequest(BaseModel):
    """User login request model."""
    mobile: str = Field(..., min_length=10, max_length=10)
    password: str = Field(..., min_length=1, max_length=128)
    
    @validator('mobile')
    def validate_mobile(cls, v):
        """Validate mobile number format."""
        if not re.match(r'^[6-9]\d{9}$', v):
            raise ValueError('Invalid mobile number format')
        return v

class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)
    confirm_new_password: str = Field(..., min_length=6, max_length=128)
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values):
        """Validate new password confirmation."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v

class UserProfile(BaseModel):
    """User profile model."""
    mobile: str
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    member_since: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True

class UserProfileRequest(BaseModel):
    """User profile update request model."""
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    company: Optional[str] = Field(None, max_length=200)
    designation: Optional[str] = Field(None, max_length=100)
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v

# =============================================
# PREFERENCES MODELS
# =============================================

class UserPreferences(BaseModel):
    """User preferences model."""
    theme: ThemeMode = ThemeMode.DARK
    notifications: bool = True
    email_alerts: bool = False
    auto_export: bool = False
    search_history_limit: int = Field(default=100, ge=10, le=1000)
    default_export_format: str = Field(default="csv", regex="^(csv|excel|pdf)$")

class UserPreferencesRequest(BaseModel):
    """User preferences update request model."""
    theme: Optional[ThemeMode] = None
    notifications: Optional[bool] = None
    email_alerts: Optional[bool] = None
    auto_export: Optional[bool] = None
    search_history_limit: Optional[int] = Field(None, ge=10, le=1000)
    default_export_format: Optional[str] = Field(None, regex="^(csv|excel|pdf)$")

# =============================================
# SEARCH MODELS
# =============================================

class GSTINSearchRequest(BaseModel):
    """GSTIN search request model."""
    gstin: str = Field(..., min_length=15, max_length=15, description="15-character GSTIN")
    
    @validator('gstin')
    def validate_gstin(cls, v):
        """Validate GSTIN format."""
        # Remove spaces and convert to uppercase
        clean_gstin = v.replace(' ', '').upper()
        
        # Check format
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        if not re.match(pattern, clean_gstin):
            raise ValueError('Invalid GSTIN format')
        
        return clean_gstin

class CompanyInfo(BaseModel):
    """Company information model."""
    gstin: str
    company_name: str
    status: GSTINStatus = GSTINStatus.UNKNOWN
    registration_date: Optional[str] = None
    business_type: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    compliance_score: int = Field(default=0, ge=0, le=100)
    last_updated: Optional[datetime] = None

class SearchHistoryItem(BaseModel):
    """Search history item model."""
    id: Optional[int] = None
    gstin: str
    company_name: str
    status: str
    compliance_score: int = Field(ge=0, le=100)
    searched_at: datetime
    raw_data: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    """Search response model."""
    success: bool
    data: Optional[CompanyInfo] = None
    error: Optional[str] = None
    cached: bool = False
    search_time_ms: Optional[int] = None

# =============================================
# ANALYTICS MODELS
# =============================================

class UserStats(BaseModel):
    """User statistics model."""
    total_searches: int = 0
    unique_companies: int = 0
    avg_compliance_score: float = 0.0
    searches_this_month: int = 0
    member_since: Optional[str] = None

class DailySearchData(BaseModel):
    """Daily search data model."""
    date: str
    count: int

class TopCompanyData(BaseModel):
    """Top company data model."""
    name: str
    count: int

class AnalyticsData(BaseModel):
    """Analytics data model."""
    daily_searches: List[DailySearchData] = []
    top_companies: List[TopCompanyData] = []
    score_distribution: List[Dict[str, Any]] = []

# =============================================
# ADMIN MODELS
# =============================================

class AdminStats(BaseModel):
    """Admin statistics model."""
    total_users: int = 0
    active_users: int = 0
    total_searches: int = 0
    searches_today: int = 0
    system_health: Optional[Dict[str, Any]] = None

class UserListItem(BaseModel):
    """User list item for admin."""
    mobile: str
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    search_count: int = 0
    is_active: bool = True

class UserListResponse(BaseModel):
    """User list response for admin."""
    users: List[UserListItem]
    total: int
    page: int
    per_page: int
    total_pages: int

class BulkActionRequest(BaseModel):
    """Bulk action request model."""
    action: str = Field(..., regex="^(delete|activate|deactivate)$")
    user_ids: List[str] = Field(..., min_items=1, max_items=100)

# =============================================
# SYSTEM MODELS
# =============================================

class SystemHealth(BaseModel):
    """System health model."""
    status: str = Field(..., regex="^(healthy|degraded|unhealthy)$")
    timestamp: datetime
    checks: Dict[str, str]
    metrics: Optional[Dict[str, Any]] = None

class ErrorLog(BaseModel):
    """Error log model."""
    type: str
    message: str
    stack: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    context: Optional[Dict[str, Any]] = None

# =============================================
# EXPORT MODELS
# =============================================

class ExportRequest(BaseModel):
    """Export request model."""
    format: str = Field(..., regex="^(csv|excel|pdf)$")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    include_raw_data: bool = False
    
    @validator('date_from', 'date_to')
    def validate_dates(cls, v):
        """Validate date format."""
        if v:
            try:
                datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v

class ExportResponse(BaseModel):
    """Export response model."""
    success: bool
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    record_count: Optional[int] = None
    error: Optional[str] = None

# =============================================
# NOTIFICATION MODELS
# =============================================

class NotificationSettings(BaseModel):
    """Notification settings model."""
    email_enabled: bool = False
    sms_enabled: bool = False
    push_enabled: bool = True
    search_alerts: bool = True
    system_updates: bool = True
    weekly_reports: bool = False

class Notification(BaseModel):
    """Notification model."""
    id: Optional[str] = None
    title: str
    message: str
    type: str = Field(..., regex="^(info|success|warning|error)$")
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

# =============================================
# API RESPONSE MODELS
# =============================================

class PaginatedResponse(BaseModel):
    """Paginated response model."""
    success: bool = True
    data: List[Any]
    pagination: Dict[str, Any]
    total: int
    page: int
    per_page: int
    total_pages: int

class APIError(BaseModel):
    """API error model."""
    error: str
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# =============================================
# LOAN MANAGEMENT MODELS (if enabled)
# =============================================

class LoanApplicationRequest(BaseModel):
    """Loan application request model."""
    amount: float = Field(..., gt=0, le=10000000, description="Loan amount in INR")
    purpose: str = Field(..., min_length=3, max_length=200)
    tenure_months: int = Field(..., ge=3, le=60, description="Tenure in months")
    income: Optional[float] = Field(None, gt=0)
    company_gstin: Optional[str] = None
    
    @validator('company_gstin')
    def validate_company_gstin(cls, v):
        """Validate company GSTIN if provided."""
        if v:
            pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
            if not re.match(pattern, v.replace(' ', '').upper()):
                raise ValueError('Invalid GSTIN format')
        return v

class LoanApplication(BaseModel):
    """Loan application model."""
    id: Optional[str] = None
    mobile: str
    amount: float
    purpose: str
    tenure_months: int
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

# =============================================
# VALIDATION HELPERS
# =============================================

class ValidationError(Exception):
    """Custom validation error."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")

def validate_request_data(model_class: BaseModel, data: Dict[str, Any]) -> BaseModel:
    """Validate request data against model."""
    try:
        return model_class(**data)
    except Exception as e:
        raise ValidationError("validation", str(e))

# =============================================
# MODEL UTILITIES
# =============================================

def model_to_dict(model: BaseModel, exclude_none: bool = True) -> Dict[str, Any]:
    """Convert model to dictionary."""
    return model.dict(exclude_none=exclude_none)

def dict_to_model(data: Dict[str, Any], model_class: BaseModel) -> BaseModel:
    """Convert dictionary to model."""
    return model_class(**data)

# Export commonly used models
__all__ = [
    'UserSignupRequest', 'UserLoginRequest', 'ChangePasswordRequest',
    'UserProfile', 'UserProfileRequest', 'UserPreferences', 'UserPreferencesRequest',
    'GSTINSearchRequest', 'CompanyInfo', 'SearchHistoryItem', 'SearchResponse',
    'UserStats', 'AnalyticsData', 'AdminStats', 'UserListResponse',
    'SystemHealth', 'ErrorLog', 'ExportRequest', 'ExportResponse',
    'BaseResponse', 'ErrorResponse', 'SuccessResponse',
    'ValidationError', 'validate_request_data'
]
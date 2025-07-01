#!/usr/bin/env python3
"""
Razorpay Lending API Integration for GST Intelligence Platform
Complete loan application and management system with enhanced integration
"""

import os
import httpx
import hmac
import hashlib
import asyncio
import json
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoanStatus(Enum):
    """Loan application status enumeration"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    CLOSED = "closed"
    DEFAULTED = "defaulted"

class OfferStatus(Enum):
    """Loan offer status enumeration"""
    GENERATED = "generated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class LoanApplication:
    """Loan application data structure"""
    user_mobile: str
    gstin: str
    company_name: str
    loan_amount: float
    purpose: str
    tenure_months: int
    annual_turnover: float
    monthly_revenue: float
    compliance_score: float
    business_vintage_months: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API calls"""
        return {
            "user_mobile": self.user_mobile,
            "gstin": self.gstin,
            "company_name": self.company_name,
            "loan_amount": self.loan_amount,
            "purpose": self.purpose,
            "tenure_months": self.tenure_months,
            "annual_turnover": self.annual_turnover,
            "monthly_revenue": self.monthly_revenue,
            "compliance_score": self.compliance_score,
            "business_vintage_months": self.business_vintage_months
        }

class LoanConfig:
    """Loan configuration and validation"""
    
    # Configuration from environment or defaults
    MIN_LOAN_AMOUNT = int(os.getenv("MIN_LOAN_AMOUNT", "50000"))
    MAX_LOAN_AMOUNT = int(os.getenv("MAX_LOAN_AMOUNT", "5000000"))
    MIN_COMPLIANCE_SCORE = int(os.getenv("MIN_COMPLIANCE_SCORE", "60"))
    MIN_BUSINESS_VINTAGE_MONTHS = int(os.getenv("MIN_BUSINESS_VINTAGE_MONTHS", "6"))
    MIN_ANNUAL_TURNOVER = int(os.getenv("MIN_ANNUAL_TURNOVER", "1000000"))
    MAX_LOAN_TO_TURNOVER_RATIO = float(os.getenv("MAX_LOAN_TO_TURNOVER_RATIO", "0.5"))
    
    # Interest rate ranges
    MIN_INTEREST_RATE = 12.0
    MAX_INTEREST_RATE = 36.0
    
    # Tenure options (in months)
    ALLOWED_TENURES = [6, 12, 18, 24, 36, 48, 60]
    
    # Risk-based scoring
    RISK_SCORE_WEIGHTS = {
        "compliance_score": 0.40,
        "business_vintage": 0.20,
        "turnover_stability": 0.20,
        "filing_consistency": 0.20
    }
    
    @classmethod
    def validate_loan_application(cls, application_data: Dict) -> tuple[bool, str]:
        """Validate loan application data"""
        try:
            # Required fields check
            required_fields = [
                "gstin", "company_name", "loan_amount", "purpose", 
                "tenure_months", "annual_turnover", "monthly_revenue", 
                "compliance_score", "business_vintage_months"
            ]
            
            for field in required_fields:
                if field not in application_data or application_data[field] is None:
                    return False, f"Missing required field: {field}"
            
            # Amount validations
            loan_amount = float(application_data["loan_amount"])
            if loan_amount < cls.MIN_LOAN_AMOUNT:
                return False, f"Loan amount must be at least ₹{cls.MIN_LOAN_AMOUNT:,}"
            
            if loan_amount > cls.MAX_LOAN_AMOUNT:
                return False, f"Loan amount cannot exceed ₹{cls.MAX_LOAN_AMOUNT:,}"
            
            # Tenure validation
            tenure = int(application_data["tenure_months"])
            if tenure not in cls.ALLOWED_TENURES:
                return False, f"Tenure must be one of: {', '.join(map(str, cls.ALLOWED_TENURES))} months"
            
            # Compliance score validation
            compliance_score = float(application_data["compliance_score"])
            if compliance_score < cls.MIN_COMPLIANCE_SCORE:
                return False, f"Compliance score must be at least {cls.MIN_COMPLIANCE_SCORE}%"
            
            # Business vintage validation
            vintage_months = int(application_data["business_vintage_months"])
            if vintage_months < cls.MIN_BUSINESS_VINTAGE_MONTHS:
                return False, f"Business must be operational for at least {cls.MIN_BUSINESS_VINTAGE_MONTHS} months"
            
            # Turnover validation
            annual_turnover = float(application_data["annual_turnover"])
            if annual_turnover < cls.MIN_ANNUAL_TURNOVER:
                return False, f"Annual turnover must be at least ₹{cls.MIN_ANNUAL_TURNOVER:,}"
            
            # Loan-to-turnover ratio validation
            max_allowed_loan = annual_turnover * cls.MAX_LOAN_TO_TURNOVER_RATIO
            if loan_amount > max_allowed_loan:
                return False, f"Loan amount cannot exceed {cls.MAX_LOAN_TO_TURNOVER_RATIO*100}% of annual turnover (₹{max_allowed_loan:,.0f})"
            
            # GSTIN format validation
            gstin = application_data["gstin"].strip().upper()
            if not cls._validate_gstin(gstin):
                return False, "Invalid GSTIN format"
            
            return True, "Validation successful"
            
        except (ValueError, TypeError) as e:
            return False, f"Invalid data format: {str(e)}"
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, "Validation failed"
    
    @classmethod
    def _validate_gstin(cls, gstin: str) -> bool:
        """Validate GSTIN format"""
        import re
        pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
        return bool(re.match(pattern, gstin))
    
    @classmethod
    def calculate_risk_score(cls, application_data: Dict) -> float:
        """Calculate risk score based on application data"""
        try:
            # Compliance score component (0-100 -> 0-1)
            compliance_component = application_data["compliance_score"] / 100.0
            
            # Business vintage component
            vintage_months = application_data["business_vintage_months"]
            vintage_component = min(vintage_months / 60.0, 1.0)  # Max at 5 years
            
            # Turnover stability component (based on monthly vs annual)
            monthly_revenue = application_data["monthly_revenue"]
            annual_turnover = application_data["annual_turnover"]
            expected_monthly = annual_turnover / 12
            stability_ratio = min(monthly_revenue / expected_monthly, 2.0) if expected_monthly > 0 else 0
            turnover_component = min(abs(1.0 - abs(stability_ratio - 1.0)), 1.0)
            
            # Filing consistency (assumed good if compliance score is high)
            filing_component = compliance_component
            
            # Calculate weighted risk score
            risk_score = (
                compliance_component * cls.RISK_SCORE_WEIGHTS["compliance_score"] +
                vintage_component * cls.RISK_SCORE_WEIGHTS["business_vintage"] +
                turnover_component * cls.RISK_SCORE_WEIGHTS["turnover_stability"] +
                filing_component * cls.RISK_SCORE_WEIGHTS["filing_consistency"]
            ) * 100
            
            return min(max(risk_score, 0), 100)
            
        except Exception as e:
            logger.error(f"Risk score calculation error: {e}")
            return 50.0  # Default moderate risk
    
    @classmethod
    def calculate_interest_rate(cls, risk_score: float, loan_amount: float, tenure_months: int) -> float:
        """Calculate interest rate based on risk factors"""
        try:
            # Base rate calculation (inverse of risk score)
            base_rate = cls.MIN_INTEREST_RATE + (cls.MAX_INTEREST_RATE - cls.MIN_INTEREST_RATE) * (1 - risk_score/100)
            
            # Amount-based adjustment (smaller loans have slightly higher rates)
            if loan_amount < 200000:
                amount_adjustment = 2.0
            elif loan_amount < 500000:
                amount_adjustment = 1.0
            else:
                amount_adjustment = 0.0
            
            # Tenure-based adjustment (longer tenure = higher rate)
            tenure_adjustment = (tenure_months - 12) * 0.1 if tenure_months > 12 else 0
            
            final_rate = base_rate + amount_adjustment + tenure_adjustment
            
            return min(max(final_rate, cls.MIN_INTEREST_RATE), cls.MAX_INTEREST_RATE)
            
        except Exception as e:
            logger.error(f"Interest rate calculation error: {e}")
            return (cls.MIN_INTEREST_RATE + cls.MAX_INTEREST_RATE) / 2  # Default to mid-range

class RazorpayLendingClient:
    """Razorpay Capital API client for loan management."""
    
    def __init__(self, api_key: str, api_secret: str, environment: str = "test"):
        """Initialize Razorpay client with correct parameters."""
        self.api_key = api_key
        self.api_secret = api_secret
        self.environment = environment
        self.base_url = "https://api.razorpay.com/v1" if environment == "live" else "https://api.razorpay.com/v1"
        
        # Initialize Razorpay client with correct parameter names
        import razorpay
        self.client = razorpay.Client(auth=(api_key, api_secret))
        
        logger.info(f"✅ Razorpay client initialized for {environment} environment")
    
    async def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to Razorpay API with retry logic"""
        
        # Rate limiting
        current_time = datetime.now().timestamp()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        
        url = f"{self.base_url}{endpoint}"
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    auth = (self.api_key, self.api_secret)
                    
                    if method.upper() == "GET":
                        response = await client.get(url, headers=self.headers, auth=auth, params=data)
                    elif method.upper() == "POST":
                        response = await client.post(url, headers=self.headers, auth=auth, json=data)
                    elif method.upper() == "PUT":
                        response = await client.put(url, headers=self.headers, auth=auth, json=data)
                    elif method.upper() == "DELETE":
                        response = await client.delete(url, headers=self.headers, auth=auth)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    self.last_request_time = datetime.now().timestamp()
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:  # Rate limited
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(f"Rate limited, retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise httpx.HTTPStatusError(f"Rate limited after {max_retries} attempts", request=response.request, response=response)
                    else:
                        error_data = response.text
                        raise httpx.HTTPStatusError(f"API request failed: {response.status_code} - {error_data}", request=response.request, response=response)
                        
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    logger.warning(f"Request timeout, retrying (attempt {attempt + 1})")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise Exception("Request timeout after retries")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Request failed, retrying: {e}")
                    await asyncio.sleep(1)
                    continue
                else:
                    raise
    
    async def create_loan_application(self, application_data: Dict) -> Dict:
        """Create a loan application via Razorpay"""
        try:
            # Prepare application data for Razorpay
            razorpay_data = {
                "amount": int(application_data["loan_amount"] * 100),  # Amount in paise
                "currency": "INR",
                "loan_purpose": application_data["purpose"],
                "tenure": application_data["tenure_months"],
                "customer": {
                    "name": application_data["company_name"],
                    "gstin": application_data["gstin"],
                    "contact": application_data["user_mobile"]
                },
                "business_details": {
                    "annual_turnover": application_data["annual_turnover"],
                    "monthly_revenue": application_data["monthly_revenue"],
                    "compliance_score": application_data["compliance_score"],
                    "vintage_months": application_data["business_vintage_months"]
                }
            }
            
            # Note: This is a mock implementation as Razorpay's actual lending API
            # may have different endpoints and data structure
            response = await self._make_request("POST", "/loans/applications", razorpay_data)
            
            return {
                "success": True,
                "razorpay_application_id": response.get("id"),
                "status": "submitted",
                "data": response
            }
            
        except Exception as e:
            logger.error(f"Razorpay application creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_loan_offers(self, application_id: str) -> Dict:
        """Get loan offers for an application"""
        try:
            response = await self._make_request("GET", f"/loans/applications/{application_id}/offers")
            
            return {
                "success": True,
                "offers": response.get("offers", [])
            }
            
        except Exception as e:
            logger.error(f"Failed to get loan offers: {e}")
            return {
                "success": False,
                "error": str(e),
                "offers": []
            }
    
    async def accept_loan_offer(self, offer_id: str) -> Dict:
        """Accept a loan offer"""
        try:
            response = await self._make_request("POST", f"/loans/offers/{offer_id}/accept")
            
            return {
                "success": True,
                "data": response
            }
            
        except Exception as e:
            logger.error(f"Failed to accept loan offer: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def verify_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify Razorpay webhook signature"""
        try:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

class LoanManager:
    """
    Complete loan management system integrated with GST Intelligence Platform
    """
    
    def __init__(self, razorpay_client: RazorpayLendingClient, db_manager):
        self.razorpay = razorpay_client
        self.db = db_manager
        logger.info("Loan manager initialized with Razorpay integration")
    
    async def initialize_loan_tables(self):
        """Initialize database tables for loan management"""
        async with self.db.pool.acquire() as conn:
            # Loan applications table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS loan_applications (
                    id SERIAL PRIMARY KEY,
                    user_mobile VARCHAR(10) NOT NULL,
                    razorpay_application_id VARCHAR(100),
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    loan_amount DECIMAL(15,2) NOT NULL,
                    purpose TEXT NOT NULL,
                    tenure_months INTEGER NOT NULL,
                    annual_turnover DECIMAL(15,2) NOT NULL,
                    monthly_revenue DECIMAL(15,2) NOT NULL,
                    compliance_score DECIMAL(5,2) NOT NULL,
                    business_vintage_months INTEGER NOT NULL,
                    risk_score DECIMAL(5,2),
                    interest_rate DECIMAL(5,2),
                    status VARCHAR(20) DEFAULT 'pending',
                    application_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS loan_offers (
                    id SERIAL PRIMARY KEY,
                    application_id INTEGER NOT NULL,
                    razorpay_offer_id VARCHAR(100),
                    loan_amount DECIMAL(15,2) NOT NULL,
                    interest_rate DECIMAL(5,2) NOT NULL,
                    tenure_months INTEGER NOT NULL,
                    emi_amount DECIMAL(10,2) NOT NULL,
                    processing_fee DECIMAL(10,2),
                    offer_data JSONB,
                    status VARCHAR(20) DEFAULT 'generated',
                    is_accepted BOOLEAN DEFAULT FALSE,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES loan_applications(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS loan_disbursements (
                    id SERIAL PRIMARY KEY,
                    application_id INTEGER NOT NULL,
                    offer_id INTEGER NOT NULL,
                    razorpay_loan_id VARCHAR(100),
                    disbursed_amount DECIMAL(15,2) NOT NULL,
                    disbursement_date TIMESTAMP NOT NULL,
                    account_number VARCHAR(20),
                    ifsc_code VARCHAR(15),
                    utr_number VARCHAR(30),
                    status VARCHAR(20) DEFAULT 'disbursed',
                    disbursement_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES loan_applications(id) ON DELETE CASCADE,
                    FOREIGN KEY (offer_id) REFERENCES loan_offers(id) ON DELETE CASCADE
                );
                
                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_loan_applications_user ON loan_applications(user_mobile);
                CREATE INDEX IF NOT EXISTS idx_loan_applications_status ON loan_applications(status);
                CREATE INDEX IF NOT EXISTS idx_loan_applications_gstin ON loan_applications(gstin);
                CREATE INDEX IF NOT EXISTS idx_loan_offers_application ON loan_offers(application_id);
                CREATE INDEX IF NOT EXISTS idx_loan_offers_status ON loan_offers(status);
                CREATE INDEX IF NOT EXISTS idx_loan_disbursements_application ON loan_disbursements(application_id);
            """)
            
            logger.info("✅ Loan management tables initialized")
    
    async def submit_loan_application(self, user_mobile: str, application_data: Dict) -> Dict:
        """Submit a complete loan application"""
        try:
            # Validate application
            is_valid, validation_message = LoanConfig.validate_loan_application(application_data)
            if not is_valid:
                return {
                    "success": False,
                    "error": validation_message
                }
            
            # Calculate risk score and interest rate
            risk_score = LoanConfig.calculate_risk_score(application_data)
            interest_rate = LoanConfig.calculate_interest_rate(
                risk_score, 
                application_data["loan_amount"], 
                application_data["tenure_months"]
            )
            
            # Create application in Razorpay (if configured)
            razorpay_response = None
            razorpay_application_id = None
            
            try:
                razorpay_response = await self.razorpay.create_loan_application(application_data)
                if razorpay_response["success"]:
                    razorpay_application_id = razorpay_response["razorpay_application_id"]
                else:
                    logger.warning(f"Razorpay application failed: {razorpay_response.get('error')}")
            except Exception as e:
                logger.error(f"Razorpay integration error: {e}")
                # Continue with local application even if Razorpay fails
            
            # Store in local database
            async with self.db.pool.acquire() as conn:
                application_id = await conn.fetchval("""
                    INSERT INTO loan_applications (
                        user_mobile, razorpay_application_id, gstin, company_name,
                        loan_amount, purpose, tenure_months, annual_turnover,
                        monthly_revenue, compliance_score, business_vintage_months,
                        risk_score, interest_rate, status, application_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    RETURNING id
                """, 
                    user_mobile, razorpay_application_id, application_data["gstin"],
                    application_data["company_name"], application_data["loan_amount"],
                    application_data["purpose"], application_data["tenure_months"],
                    application_data["annual_turnover"], application_data["monthly_revenue"],
                    application_data["compliance_score"], application_data["business_vintage_months"],
                    risk_score, interest_rate, LoanStatus.PENDING.value,
                    json.dumps({**application_data, "razorpay_response": razorpay_response})
                )
            
            # Generate initial loan offer
            await self._generate_loan_offer(application_id, application_data, risk_score, interest_rate)
            
            logger.info(f"Loan application submitted successfully: {application_id}")
            
            return {
                "success": True,
                "application_id": application_id,
                "razorpay_application_id": razorpay_application_id,
                "risk_score": risk_score,
                "estimated_interest_rate": interest_rate,
                "status": LoanStatus.PENDING.value
            }
            
        except Exception as e:
            logger.error(f"Loan application submission failed: {e}")
            return {
                "success": False,
                "error": "Failed to submit loan application"
            }
    
    async def _generate_loan_offer(self, application_id: int, application_data: Dict, 
                                 risk_score: float, interest_rate: float) -> bool:
        """Generate a loan offer for an application"""
        try:
            loan_amount = application_data["loan_amount"]
            tenure_months = application_data["tenure_months"]
            
            # Calculate EMI using standard formula
            monthly_rate = interest_rate / (12 * 100)
            emi_amount = (loan_amount * monthly_rate * (1 + monthly_rate)**tenure_months) / \
                        ((1 + monthly_rate)**tenure_months - 1)
            
            # Calculate processing fee (1-3% based on risk)
            processing_fee_rate = 0.01 + (1 - risk_score/100) * 0.02  # 1-3%
            processing_fee = loan_amount * processing_fee_rate
            
            # Offer expires in 7 days
            expires_at = datetime.now() + timedelta(days=7)
            
            async with self.db.pool.acquire() as conn:
                offer_id = await conn.fetchval("""
                    INSERT INTO loan_offers (
                        application_id, loan_amount, interest_rate, tenure_months,
                        emi_amount, processing_fee, status, expires_at, offer_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                """, 
                    application_id, loan_amount, interest_rate, tenure_months,
                    emi_amount, processing_fee, OfferStatus.GENERATED.value, expires_at,
                    json.dumps({
                        "total_payable": emi_amount * tenure_months,
                        "total_interest": (emi_amount * tenure_months) - loan_amount,
                        "apr": interest_rate,
                        "risk_category": "Low" if risk_score > 80 else "Medium" if risk_score > 60 else "High"
                    })
                )
            
            logger.info(f"Loan offer generated: {offer_id} for application {application_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate loan offer: {e}")
            return False
    
    async def get_user_loan_applications(self, user_mobile: str) -> List[Dict]:
        """Get all loan applications for a user"""
        try:
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT la.*, 
                           array_agg(
                               json_build_object(
                                   'id', lo.id,
                                   'loan_amount', lo.loan_amount,
                                   'interest_rate', lo.interest_rate,
                                   'tenure_months', lo.tenure_months,
                                   'emi_amount', lo.emi_amount,
                                   'processing_fee', lo.processing_fee,
                                   'status', lo.status,
                                   'is_accepted', lo.is_accepted,
                                   'expires_at', lo.expires_at,
                                   'created_at', lo.created_at
                               )
                           ) FILTER (WHERE lo.id IS NOT NULL) as offers
                    FROM loan_applications la
                    LEFT JOIN loan_offers lo ON la.id = lo.application_id
                    WHERE la.user_mobile = $1
                    GROUP BY la.id
                    ORDER BY la.created_at DESC
                """, user_mobile)
                
                applications = []
                for row in rows:
                    app_dict = dict(row)
                    app_dict['offers'] = [offer for offer in (app_dict['offers'] or []) if offer]
                    applications.append(app_dict)
                
                return applications
                
        except Exception as e:
            logger.error(f"Failed to get user loan applications: {e}")
            return []
    
    async def accept_loan_offer(self, user_mobile: str, offer_id: int) -> Dict:
        """Accept a loan offer"""
        try:
            async with self.db.pool.acquire() as conn:
                # Verify offer belongs to user and is valid
                offer_row = await conn.fetchrow("""
                    SELECT lo.*, la.user_mobile, la.razorpay_application_id
                    FROM loan_offers lo
                    JOIN loan_applications la ON lo.application_id = la.id
                    WHERE lo.id = $1 AND la.user_mobile = $2
                    AND lo.status = 'generated' AND lo.expires_at > CURRENT_TIMESTAMP
                """, offer_id, user_mobile)
                
                if not offer_row:
                    return {
                        "success": False,
                        "error": "Offer not found or expired"
                    }
                
                # Accept offer in Razorpay (if configured)
                razorpay_response = None
                if offer_row['razorpay_offer_id']:
                    try:
                        razorpay_response = await self.razorpay.accept_loan_offer(offer_row['razorpay_offer_id'])
                    except Exception as e:
                        logger.error(f"Razorpay offer acceptance failed: {e}")
                
                # Update offer status
                await conn.execute("""
                    UPDATE loan_offers 
                    SET status = $1, is_accepted = true
                    WHERE id = $2
                """, OfferStatus.ACCEPTED.value, offer_id)
                
                # Update application status
                await conn.execute("""
                    UPDATE loan_applications 
                    SET status = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, LoanStatus.APPROVED.value, offer_row['application_id'])
                
                logger.info(f"Loan offer accepted: {offer_id} by user {user_mobile}")
                
                return {
                    "success": True,
                    "message": "Loan offer accepted successfully",
                    "offer_id": offer_id,
                    "next_steps": "Disbursement will be processed within 2-3 business days"
                }
                
        except Exception as e:
            logger.error(f"Failed to accept loan offer: {e}")
            return {
                "success": False,
                "error": "Failed to accept loan offer"
            }
    
    async def get_loan_eligibility(self, gstin: str, annual_turnover: float, 
                                 compliance_score: float, business_vintage_months: int) -> Dict:
        """Check loan eligibility for given parameters"""
        try:
            eligibility = {
                "eligible": True,
                "reasons": [],
                "max_loan_amount": 0,
                "recommended_amount": 0,
                "estimated_interest_rate": 0
            }
            
            # Check basic eligibility criteria
            if compliance_score < LoanConfig.MIN_COMPLIANCE_SCORE:
                eligibility["eligible"] = False
                eligibility["reasons"].append(f"Compliance score below minimum ({LoanConfig.MIN_COMPLIANCE_SCORE}%)")
            
            if business_vintage_months < LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS:
                eligibility["eligible"] = False
                eligibility["reasons"].append(f"Business vintage below minimum ({LoanConfig.MIN_BUSINESS_VINTAGE_MONTHS} months)")
            
            if annual_turnover < LoanConfig.MIN_ANNUAL_TURNOVER:
                eligibility["eligible"] = False
                eligibility["reasons"].append(f"Annual turnover below minimum (₹{LoanConfig.MIN_ANNUAL_TURNOVER:,})")
            
            if eligibility["eligible"]:
                # Calculate maximum loan amount
                max_by_turnover = annual_turnover * LoanConfig.MAX_LOAN_TO_TURNOVER_RATIO
                eligibility["max_loan_amount"] = min(max_by_turnover, LoanConfig.MAX_LOAN_AMOUNT)
                
                # Calculate recommended amount (conservative approach)
                score_multiplier = compliance_score / 100
                eligibility["recommended_amount"] = min(
                    annual_turnover * 0.3 * score_multiplier,
                    eligibility["max_loan_amount"]
                )
                
                # Estimate interest rate
                mock_application = {
                    "compliance_score": compliance_score,
                    "business_vintage_months": business_vintage_months,
                    "monthly_revenue": annual_turnover / 12,
                    "annual_turnover": annual_turnover
                }
                risk_score = LoanConfig.calculate_risk_score(mock_application)
                eligibility["estimated_interest_rate"] = LoanConfig.calculate_interest_rate(
                    risk_score, eligibility["recommended_amount"], 24
                )
                eligibility["risk_score"] = risk_score
            
            return {
                "success": True,
                "data": eligibility
            }
            
        except Exception as e:
            logger.error(f"Eligibility check failed: {e}")
            return {
                "success": False,
                "error": "Failed to check eligibility"
            }

# Export main classes
__all__ = [
    'LoanStatus',
    'OfferStatus', 
    'LoanApplication',
    'LoanConfig',
    'RazorpayLendingClient',
    'LoanManager'
]
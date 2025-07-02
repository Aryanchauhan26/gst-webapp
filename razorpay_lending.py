#!/usr/bin/env python3
"""
Razorpay Lending API Integration for GST Intelligence Platform
Complete loan application and management system
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoanStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    CLOSED = "closed"

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
    
class RazorpayLendingClient:
    """
    Razorpay Lending API Client
    Handles all loan-related operations
    """
    
    def __init__(self, api_key: str, api_secret: str, is_production: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_production = is_production
        
        # API endpoints
        if is_production:
            self.base_url = "https://api.razorpay.com/v1"
        else:
            self.base_url = "https://api.razorpay.com/v1"  # Same URL, but different keys
        
        self.headers = {
            "Content-Type": "application/json",
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    async def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated request to Razorpay API"""
        
        # Rate limiting
        current_time = datetime.now().timestamp()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    auth=(self.api_key, self.api_secret),
                    headers=self.headers,
                    json=data if data else None
                )
                
                self.last_request_time = datetime.now().timestamp()
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    error_data = response.json() if response.content else {}
                    logger.error(f"Razorpay API Error: {response.status_code} - {error_data}")
                    raise Exception(f"API Error: {response.status_code}")
                    
            except httpx.TimeoutException:
                logger.error("Razorpay API request timeout")
                raise Exception("Request timeout")
            except Exception as e:
                logger.error(f"Razorpay API request failed: {e}")
                raise
    
    async def create_loan_application(self, application: LoanApplication) -> dict:
        """
        Create a new loan application
        """
        
        # Calculate risk score based on GST compliance and business metrics
        risk_score = self._calculate_risk_score(application)
        
        # Prepare application data for Razorpay
        loan_data = {
            "loan_amount": int(application.loan_amount * 100),  # Amount in paise
            "loan_purpose": application.purpose,
            "tenure": application.tenure_months,
            "customer": {
                "name": application.company_name,
                "email": f"{application.user_mobile}@gstintelligence.com",  # You may want to collect real email
                "contact": application.user_mobile,
                "gstin": application.gstin
            },
            "business_details": {
                "name": application.company_name,
                "gstin": application.gstin,
                "annual_turnover": int(application.annual_turnover * 100),
                "monthly_revenue": int(application.monthly_revenue * 100),
                "vintage_months": application.business_vintage_months,
                "compliance_score": application.compliance_score
            },
            "risk_assessment": {
                "score": risk_score,
                "factors": self._get_risk_factors(application)
            },
            "notes": {
                "source": "GST Intelligence Platform",
                "compliance_score": application.compliance_score,
                "created_at": datetime.now().isoformat()
            }
        }
        
        try:
            # Note: The exact endpoint may vary based on Razorpay's lending API documentation
            response = await self._make_request("POST", "/loans/applications", loan_data)
            logger.info(f"Loan application created: {response.get('id')}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create loan application: {e}")
            raise
    
    async def get_loan_status(self, loan_id: str) -> dict:
        """Get loan application status"""
        try:
            response = await self._make_request("GET", f"/loans/applications/{loan_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to get loan status: {e}")
            raise
    
    async def get_loan_offers(self, application_id: str) -> List[dict]:
        """Get available loan offers for an application"""
        try:
            response = await self._make_request("GET", f"/loans/applications/{application_id}/offers")
            return response.get('offers', [])
        except Exception as e:
            logger.error(f"Failed to get loan offers: {e}")
            raise
    
    async def accept_loan_offer(self, application_id: str, offer_id: str) -> dict:
        """Accept a loan offer"""
        try:
            data = {"offer_id": offer_id}
            response = await self._make_request("POST", f"/loans/applications/{application_id}/accept", data)
            return response
        except Exception as e:
            logger.error(f"Failed to accept loan offer: {e}")
            raise
    
    def _calculate_risk_score(self, application: LoanApplication) -> float:
        """
        Calculate risk score based on various factors
        Higher score means lower risk
        """
        score = 0.0
        
        # Compliance score (40% weightage)
        compliance_weight = 0.4
        score += (application.compliance_score / 100) * compliance_weight
        
        # Business vintage (20% weightage)
        vintage_weight = 0.2
        vintage_score = min(application.business_vintage_months / 36, 1.0)  # Max score at 3 years
        score += vintage_score * vintage_weight
        
        # Revenue stability (25% weightage)
        revenue_weight = 0.25
        monthly_to_annual_ratio = (application.monthly_revenue * 12) / application.annual_turnover
        revenue_consistency = min(monthly_to_annual_ratio, 1.0)
        score += revenue_consistency * revenue_weight
        
        # Loan to revenue ratio (15% weightage)
        ltv_weight = 0.15
        loan_to_revenue = application.loan_amount / application.annual_turnover
        ltv_score = max(0, 1 - (loan_to_revenue - 0.1) / 0.4)  # Optimal at 10% of turnover
        score += max(0, ltv_score) * ltv_weight
        
        return round(score * 100, 2)  # Return as percentage
    
    def _get_risk_factors(self, application: LoanApplication) -> List[str]:
        """Get list of risk factors for the application"""
        factors = []
        
        if application.compliance_score >= 80:
            factors.append("High GST compliance")
        elif application.compliance_score >= 60:
            factors.append("Average GST compliance")
        else:
            factors.append("Low GST compliance - Higher risk")
        
        if application.business_vintage_months >= 36:
            factors.append("Established business (3+ years)")
        elif application.business_vintage_months >= 12:
            factors.append("Growing business (1-3 years)")
        else:
            factors.append("New business (<1 year) - Higher risk")
        
        loan_to_turnover = application.loan_amount / application.annual_turnover
        if loan_to_turnover <= 0.1:
            factors.append("Conservative loan amount")
        elif loan_to_turnover <= 0.3:
            factors.append("Moderate loan amount")
        else:
            factors.append("High loan amount relative to turnover")
        
        return factors
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature from Razorpay"""
        expected_signature = hmac.new(
            self.api_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)

class LoanManager:
    """
    Loan management system for the GST Intelligence Platform
    """
    
    def __init__(self, razorpay_client: RazorpayLendingClient, db_manager):
        self.razorpay = razorpay_client
        self.db = db_manager
    
    async def initialize_loan_tables(self):
        """Initialize database tables for loan management"""
        async with self.db.pool.acquire() as conn:
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
                    is_accepted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES loan_applications(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_loan_applications_user ON loan_applications(user_mobile);
                CREATE INDEX IF NOT EXISTS idx_loan_applications_status ON loan_applications(status);
                CREATE INDEX IF NOT EXISTS idx_loan_offers_application ON loan_offers(application_id);
            """)
    
    async def submit_loan_application(self, user_mobile: str, application_data: dict) -> dict:
        """Submit a new loan application"""
        try:
            # Create LoanApplication object
            application = LoanApplication(
                user_mobile=user_mobile,
                gstin=application_data['gstin'],
                company_name=application_data['company_name'],
                loan_amount=float(application_data['loan_amount']),
                purpose=application_data['purpose'],
                tenure_months=int(application_data['tenure_months']),
                annual_turnover=float(application_data['annual_turnover']),
                monthly_revenue=float(application_data['monthly_revenue']),
                compliance_score=float(application_data['compliance_score']),
                business_vintage_months=int(application_data['business_vintage_months'])
            )
            
            # Submit to Razorpay
            razorpay_response = await self.razorpay.create_loan_application(application)
            
            # Store in database
            async with self.db.pool.acquire() as conn:
                application_id = await conn.fetchval("""
                    INSERT INTO loan_applications (
                        user_mobile, razorpay_application_id, gstin, company_name,
                        loan_amount, purpose, tenure_months, annual_turnover,
                        monthly_revenue, compliance_score, business_vintage_months,
                        risk_score, status, application_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    RETURNING id
                """, 
                user_mobile, razorpay_response.get('id'), application.gstin,
                application.company_name, application.loan_amount, application.purpose,
                application.tenure_months, application.annual_turnover,
                application.monthly_revenue, application.compliance_score,
                application.business_vintage_months,
                self.razorpay._calculate_risk_score(application),
                LoanStatus.PENDING.value, json.dumps(razorpay_response)
                )
            
            logger.info(f"Loan application submitted: {application_id}")
            
            return {
                "success": True,
                "application_id": application_id,
                "razorpay_id": razorpay_response.get('id'),
                "status": LoanStatus.PENDING.value,
                "message": "Loan application submitted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to submit loan application: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_user_loan_applications(self, user_mobile: str) -> List[dict]:
        """Get all loan applications for a user"""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, razorpay_application_id, gstin, company_name,
                       loan_amount, purpose, tenure_months, status,
                       risk_score, created_at, updated_at
                FROM loan_applications
                WHERE user_mobile = $1
                ORDER BY created_at DESC
            """, user_mobile)
            
            return [dict(row) for row in rows]
    
    async def update_loan_status(self, application_id: int, status: str, additional_data: dict = None):
        """Update loan application status"""
        async with self.db.pool.acquire() as conn:
            if additional_data:
                await conn.execute("""
                    UPDATE loan_applications 
                    SET status = $1, application_data = application_data || $2, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                """, status, json.dumps(additional_data), application_id)
            else:
                await conn.execute("""
                    UPDATE loan_applications 
                    SET status = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, status, application_id)
    
    async def handle_webhook(self, payload: dict) -> bool:
        """Handle Razorpay webhook events"""
        try:
            event_type = payload.get('event')
            entity = payload.get('payload', {}).get('entity', {})
            
            if event_type == 'loan.application.status_updated':
                razorpay_id = entity.get('id')
                new_status = entity.get('status')
                
                # Update local database
                async with self.db.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE loan_applications 
                        SET status = $1, updated_at = CURRENT_TIMESTAMP
                        WHERE razorpay_application_id = $2
                    """, new_status, razorpay_id)
                
                logger.info(f"Updated loan status: {razorpay_id} -> {new_status}")
            
            elif event_type == 'loan.offer.created':
                # Handle new loan offers
                application_id = entity.get('application_id')
                offer_data = entity
                
                # Store offer in database
                async with self.db.pool.acquire() as conn:
                    local_app_id = await conn.fetchval("""
                        SELECT id FROM loan_applications 
                        WHERE razorpay_application_id = $1
                    """, application_id)
                    
                    if local_app_id:
                        await conn.execute("""
                            INSERT INTO loan_offers (
                                application_id, razorpay_offer_id, loan_amount,
                                interest_rate, tenure_months, emi_amount,
                                processing_fee, offer_data
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        local_app_id, offer_data.get('id'),
                        offer_data.get('amount', 0) / 100,  # Convert from paise
                        offer_data.get('interest_rate', 0),
                        offer_data.get('tenure', 0),
                        offer_data.get('emi_amount', 0) / 100,
                        offer_data.get('processing_fee', 0) / 100,
                        json.dumps(offer_data)
                        )
                
                logger.info(f"New loan offer received: {entity.get('id')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return False

# Configuration class
class LoanConfig:
    """Configuration for loan management"""
    
    # Loan limits
    MIN_LOAN_AMOUNT = 50000  # ₹50,000
    MAX_LOAN_AMOUNT = 5000000  # ₹50,00,000
    
    # Eligibility criteria
    MIN_COMPLIANCE_SCORE = 60
    MIN_BUSINESS_VINTAGE_MONTHS = 6
    MIN_ANNUAL_TURNOVER = 100000  # ₹1,00,000
    
    # Risk assessment
    MAX_LOAN_TO_TURNOVER_RATIO = 0.5  # 50% of annual turnover
    
    @classmethod
    def validate_loan_application(cls, application_data: dict) -> tuple[bool, str]:
        """Validate loan application data"""
        
        loan_amount = float(application_data.get('loan_amount', 0))
        annual_turnover = float(application_data.get('annual_turnover', 0))
        compliance_score = float(application_data.get('compliance_score', 0))
        vintage_months = int(application_data.get('business_vintage_months', 0))
        
        # Check loan amount limits
        if loan_amount < cls.MIN_LOAN_AMOUNT:
            return False, f"Minimum loan amount is ₹{cls.MIN_LOAN_AMOUNT:,}"
        
        if loan_amount > cls.MAX_LOAN_AMOUNT:
            return False, f"Maximum loan amount is ₹{cls.MAX_LOAN_AMOUNT:,}"
        
        # Check compliance score
        if compliance_score < cls.MIN_COMPLIANCE_SCORE:
            return False, f"Minimum compliance score required: {cls.MIN_COMPLIANCE_SCORE}%"
        
        # Check business vintage
        if vintage_months < cls.MIN_BUSINESS_VINTAGE_MONTHS:
            return False, f"Minimum business vintage: {cls.MIN_BUSINESS_VINTAGE_MONTHS} months"
        
        # Check annual turnover
        if annual_turnover < cls.MIN_ANNUAL_TURNOVER:
            return False, f"Minimum annual turnover: ₹{cls.MIN_ANNUAL_TURNOVER:,}"
        
        # Check loan-to-turnover ratio
        if loan_amount / annual_turnover > cls.MAX_LOAN_TO_TURNOVER_RATIO:
            return False, f"Loan amount cannot exceed {cls.MAX_LOAN_TO_TURNOVER_RATIO*100}% of annual turnover"
        
        return True, "Validation passed"

# Export main classes
__all__ = [
    'RazorpayLendingClient',
    'LoanManager', 
    'LoanApplication',
    'LoanStatus',
    'LoanConfig'
]
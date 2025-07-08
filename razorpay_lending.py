#!/usr/bin/env python3
"""
Razorpay Lending Integration for GST Intelligence Platform
Complete loan management system with comprehensive error handling
"""

import os
import json
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, InvalidOperation
from enum import Enum
import uuid

try:
    import razorpay
    HAS_RAZORPAY = True
except ImportError:
    HAS_RAZORPAY = False
    razorpay = None

# Configure logging
logger = logging.getLogger(__name__)


class LoanStatus(Enum):
    """Loan application status enumeration."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    CLOSED = "closed"
    DEFAULTED = "defaulted"


class LoanApplicationError(Exception):
    """Custom exception for loan application errors."""
    pass


class RazorpayLendingClient:
    """
    Enhanced Razorpay client for lending operations with comprehensive error handling.
    """

    def __init__(self,
                 key_id: str,
                 key_secret: str,
                 is_production: bool = False):
        self.key_id = key_id
        self.key_secret = key_secret
        self.is_production = is_production
        self.client = None
        self.is_available = False
        self.last_error = None

        # Rate limiting
        self.request_count = 0
        self.error_count = 0

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Razorpay client."""
        if not HAS_RAZORPAY:
            logger.warning(
                "Razorpay package not installed. Loan features disabled.")
            return

        if not self.key_id or not self.key_secret:
            logger.warning(
                "Razorpay credentials not configured. Loan features disabled.")
            return

        try:
            self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
            self.is_available = True

            # Test the connection
            self._test_connection()

            logger.info(
                f"✅ Razorpay client initialized successfully ({'Production' if self.is_production else 'Sandbox'})"
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize Razorpay client: {e}")
            self.last_error = str(e)
            self.is_available = False

    def _test_connection(self):
        """Test the Razorpay connection."""
        try:
            # Try to fetch payment methods as a connection test
            self.client.payment.all({'count': 1})
            logger.debug("Razorpay connection test successful")
        except Exception as e:
            logger.warning(f"Razorpay connection test failed: {e}")
            # Don't disable the client for connection test failures
            # as they might be due to permissions

    async def create_customer(self, customer_data: Dict) -> Optional[Dict]:
        """
        Create a customer in Razorpay.

        Args:
            customer_data: Dictionary containing customer information

        Returns:
            Customer object or None if failed
        """
        if not self.is_available:
            logger.error("Razorpay client not available")
            return None

        try:
            self.request_count += 1

            customer_payload = {
                "name": customer_data.get("name", ""),
                "email": customer_data.get("email", ""),
                "contact": customer_data.get("mobile", ""),
                "fail_existing": "0",  # Don't fail if customer exists
                "notes": {
                    "gstin": customer_data.get("gstin", ""),
                    "company_name": customer_data.get("company_name", ""),
                    "created_via": "gst_intelligence_platform"
                }
            }

            # Remove empty fields
            customer_payload = {k: v for k, v in customer_payload.items() if v}

            customer = self.client.customer.create(customer_payload)

            logger.info(
                f"✅ Customer created successfully: {customer.get('id')}")
            return customer

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"❌ Failed to create customer: {e}")
            return None

    async def create_loan_application(
            self, application_data: Dict) -> Optional[Dict]:
        """
        Create a loan application.

        Args:
            application_data: Dictionary containing loan application data

        Returns:
            Application object or None if failed
        """
        if not self.is_available:
            logger.error("Razorpay client not available")
            return None

        try:
            self.request_count += 1

            # In a real Razorpay lending integration, you would use their
            # Capital/Lending APIs. For this demo, we'll simulate the process.

            application_id = f"loan_app_{uuid.uuid4().hex[:12]}"

            # Simulate loan application creation
            loan_application = {
                "id": application_id,
                "customer_id": application_data.get("customer_id"),
                "amount": application_data.get("loan_amount"),
                "currency": "INR",
                "tenure": application_data.get("tenure_months"),
                "purpose": application_data.get("purpose"),
                "status": LoanStatus.PENDING.value,
                "created_at": int(datetime.now().timestamp()),
                "notes": {
                    "gstin": application_data.get("gstin", ""),
                    "company_name": application_data.get("company_name", ""),
                    "compliance_score":
                    application_data.get("compliance_score", 0),
                    "annual_turnover":
                    application_data.get("annual_turnover", 0),
                    "platform": "gst_intelligence"
                }
            }

            logger.info(f"✅ Loan application created: {application_id}")
            return loan_application

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"❌ Failed to create loan application: {e}")
            return None

    async def get_loan_offers(self,
                              application_id: str) -> Optional[List[Dict]]:
        """
        Get loan offers for an application.

        Args:
            application_id: The loan application ID

        Returns:
            List of loan offers or None if failed
        """
        if not self.is_available:
            return None

        try:
            self.request_count += 1

            # Simulate loan offers based on application
            # In reality, this would come from Razorpay's lending partners
            offers = [{
                "id":
                f"offer_{uuid.uuid4().hex[:8]}",
                "application_id":
                application_id,
                "lender":
                "Partner Bank A",
                "amount":
                500000,
                "interest_rate":
                12.5,
                "tenure_months":
                24,
                "emi_amount":
                23540,
                "processing_fee":
                5000,
                "valid_until":
                int((datetime.now() + timedelta(days=7)).timestamp()),
                "terms": {
                    "prepayment_charges":
                    "2% of outstanding amount",
                    "late_payment_fee":
                    "₹500 per delayed EMI",
                    "documentation_required":
                    ["Bank statements", "GST returns", "ITR"]
                }
            }, {
                "id":
                f"offer_{uuid.uuid4().hex[:8]}",
                "application_id":
                application_id,
                "lender":
                "NBFC Partner B",
                "amount":
                500000,
                "interest_rate":
                14.0,
                "tenure_months":
                36,
                "emi_amount":
                17100,
                "processing_fee":
                7500,
                "valid_until":
                int((datetime.now() + timedelta(days=5)).timestamp()),
                "terms": {
                    "prepayment_charges": "3% of outstanding amount",
                    "late_payment_fee": "₹750 per delayed EMI",
                    "documentation_required":
                    ["Bank statements", "GST returns"]
                }
            }]

            logger.info(
                f"✅ Retrieved {len(offers)} loan offers for application {application_id}"
            )
            return offers

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"❌ Failed to get loan offers: {e}")
            return None

    async def accept_loan_offer(self, offer_id: str,
                                application_id: str) -> Optional[Dict]:
        """
        Accept a loan offer.

        Args:
            offer_id: The loan offer ID
            application_id: The loan application ID

        Returns:
            Loan agreement or None if failed
        """
        if not self.is_available:
            return None

        try:
            self.request_count += 1

            # Simulate loan offer acceptance
            loan_agreement = {
                "id":
                f"loan_{uuid.uuid4().hex[:12]}",
                "application_id":
                application_id,
                "offer_id":
                offer_id,
                "status":
                LoanStatus.APPROVED.value,
                "agreement_url":
                f"https://razorpay.com/agreements/loan_{uuid.uuid4().hex[:12]}.pdf",
                "disbursement_account": {
                    "account_number": "XXXXXXXXXXXX1234",
                    "ifsc": "RZPY0000001",
                    "bank_name": "Razorpay Bank"
                },
                "repayment_schedule":
                self._generate_repayment_schedule(500000, 12.5, 24),
                "created_at":
                int(datetime.now().timestamp()),
                "terms_accepted_at":
                int(datetime.now().timestamp())
            }

            logger.info(f"✅ Loan offer accepted: {offer_id}")
            return loan_agreement

        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"❌ Failed to accept loan offer: {e}")
            return None

    def _generate_repayment_schedule(self, principal: float,
                                     interest_rate: float,
                                     tenure_months: int) -> List[Dict]:
        """Generate EMI repayment schedule."""
        monthly_rate = interest_rate / 12 / 100
        emi = principal * monthly_rate * (1 + monthly_rate)**tenure_months / (
            (1 + monthly_rate)**tenure_months - 1)

        schedule = []
        outstanding = principal

        for month in range(1, tenure_months + 1):
            interest_component = outstanding * monthly_rate
            principal_component = emi - interest_component
            outstanding -= principal_component

            schedule.append({
                "emi_number":
                month,
                "due_date": (datetime.now() +
                             timedelta(days=30 * month)).strftime("%Y-%m-%d"),
                "emi_amount":
                round(emi, 2),
                "principal_component":
                round(principal_component, 2),
                "interest_component":
                round(interest_component, 2),
                "outstanding_balance":
                round(max(0, outstanding), 2),
                "status":
                "pending"
            })

        return schedule

    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify Razorpay webhook signature.

        Args:
            payload: The webhook payload
            signature: The webhook signature

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            expected_signature = hmac.new(self.key_secret.encode('utf-8'),
                                          payload.encode('utf-8'),
                                          hashlib.sha256).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    async def handle_webhook(self, payload: Dict, signature: str) -> bool:
        """
        Handle Razorpay webhook events.

        Args:
            payload: The webhook payload
            signature: The webhook signature

        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Verify signature
            if not self.verify_webhook_signature(json.dumps(payload),
                                                 signature):
                logger.error("Invalid webhook signature")
                return False

            event_type = payload.get("event")
            entity = payload.get("payload", {}).get("payment",
                                                    {}).get("entity", {})

            logger.info(f"Processing webhook event: {event_type}")

            # Handle different event types
            if event_type == "payment.captured":
                await self._handle_payment_captured(entity)
            elif event_type == "payment.failed":
                await self._handle_payment_failed(entity)
            elif event_type == "loan.disbursed":
                await self._handle_loan_disbursed(entity)
            elif event_type == "loan.emi.due":
                await self._handle_emi_due(entity)
            else:
                logger.info(f"Unhandled webhook event: {event_type}")

            return True

        except Exception as e:
            logger.error(f"Webhook handling failed: {e}")
            return False

    async def _handle_payment_captured(self, payment_entity: Dict):
        """Handle payment captured event."""
        payment_id = payment_entity.get("id")
        amount = payment_entity.get("amount", 0) / 100  # Convert from paise

        logger.info(f"Payment captured: {payment_id}, Amount: ₹{amount}")

        # Update loan/EMI status in database
        # This would typically update the repayment schedule

    async def _handle_payment_failed(self, payment_entity: Dict):
        """Handle payment failed event."""
        payment_id = payment_entity.get("id")
        error_description = payment_entity.get("error_description",
                                               "Unknown error")

        logger.warning(
            f"Payment failed: {payment_id}, Error: {error_description}")

        # Handle failed EMI payment
        # This might trigger late payment notifications

    async def _handle_loan_disbursed(self, loan_entity: Dict):
        """Handle loan disbursed event."""
        loan_id = loan_entity.get("id")
        amount = loan_entity.get("amount", 0) / 100

        logger.info(f"Loan disbursed: {loan_id}, Amount: ₹{amount}")

        # Update loan status to disbursed/active

    async def _handle_emi_due(self, emi_entity: Dict):
        """Handle EMI due event."""
        emi_id = emi_entity.get("id")
        due_date = emi_entity.get("due_date")

        logger.info(f"EMI due: {emi_id}, Due date: {due_date}")

        # Send EMI due notifications to customer

    def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the Razorpay client."""
        return {
            'available': self.is_available,
            'has_credentials': bool(self.key_id and self.key_secret),
            'has_razorpay_package': HAS_RAZORPAY,
            'environment': 'production' if self.is_production else 'sandbox',
            'request_count': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'last_error': self.last_error
        }


class LoanManager:
    """
    Comprehensive loan management system for the GST Intelligence Platform.
    """

    def __init__(self, razorpay_client: RazorpayLendingClient, db_manager):
        self.razorpay = razorpay_client
        self.db = db_manager
        self.risk_engine = LoanRiskEngine()

    async def initialize_loan_tables(self):
        """Initialize database tables for loan management."""
        try:
            async with self.db.pool.acquire() as conn:
                # Loan applications table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS loan_applications (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(10) NOT NULL,
                        application_id VARCHAR(100) UNIQUE NOT NULL,
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
                """)

                # Loan offers table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS loan_offers (
                        id SERIAL PRIMARY KEY,
                        application_id VARCHAR(100) NOT NULL,
                        offer_id VARCHAR(100) UNIQUE NOT NULL,
                        lender_name VARCHAR(200) NOT NULL,
                        loan_amount DECIMAL(15,2) NOT NULL,
                        interest_rate DECIMAL(5,2) NOT NULL,
                        tenure_months INTEGER NOT NULL,
                        emi_amount DECIMAL(10,2) NOT NULL,
                        processing_fee DECIMAL(10,2),
                        offer_data JSONB,
                        is_accepted BOOLEAN DEFAULT FALSE,
                        valid_until TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (application_id) REFERENCES loan_applications(application_id) ON DELETE CASCADE
                    );
                """)

                # Active loans table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_loans (
                        id SERIAL PRIMARY KEY,
                        user_mobile VARCHAR(10) NOT NULL,
                        loan_id VARCHAR(100) UNIQUE NOT NULL,
                        application_id VARCHAR(100) NOT NULL,
                        offer_id VARCHAR(100) NOT NULL,
                        principal_amount DECIMAL(15,2) NOT NULL,
                        outstanding_amount DECIMAL(15,2) NOT NULL,
                        interest_rate DECIMAL(5,2) NOT NULL,
                        tenure_months INTEGER NOT NULL,
                        emis_paid INTEGER DEFAULT 0,
                        next_emi_date DATE,
                        emi_amount DECIMAL(10,2) NOT NULL,
                        status VARCHAR(20) DEFAULT 'active',
                        disbursed_at TIMESTAMP,
                        agreement_data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                        FOREIGN KEY (application_id) REFERENCES loan_applications(application_id),
                        FOREIGN KEY (offer_id) REFERENCES loan_offers(offer_id)
                    );
                """)

                # EMI schedule table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS emi_schedule (
                        id SERIAL PRIMARY KEY,
                        loan_id VARCHAR(100) NOT NULL,
                        emi_number INTEGER NOT NULL,
                        due_date DATE NOT NULL,
                        emi_amount DECIMAL(10,2) NOT NULL,
                        principal_component DECIMAL(10,2) NOT NULL,
                        interest_component DECIMAL(10,2) NOT NULL,
                        outstanding_balance DECIMAL(15,2) NOT NULL,
                        payment_date TIMESTAMP,
                        payment_id VARCHAR(100),
                        status VARCHAR(20) DEFAULT 'pending',
                        late_fee DECIMAL(10,2) DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (loan_id) REFERENCES active_loans(loan_id) ON DELETE CASCADE
                    );
                """)

                # Create indexes for performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_loan_applications_user_mobile 
                    ON loan_applications(user_mobile);
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_loan_applications_status 
                    ON loan_applications(status);
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_active_loans_user_mobile 
                    ON active_loans(user_mobile);
                """)

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_emi_schedule_loan_id_due_date 
                    ON emi_schedule(loan_id, due_date);
                """)

                logger.info(
                    "✅ Loan management tables created/verified successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize loan tables: {e}")
            raise

    async def submit_loan_application(
            self, user_mobile: str, application_data: Dict) -> Dict[str, Any]:
        """
        Submit a new loan application.

        Args:
            user_mobile: User's mobile number
            application_data: Loan application data

        Returns:
            Result dictionary with success status and data
        """
        try:
            # Validate application data
            validation_result = LoanConfig.validate_loan_application(
                application_data)
            if not validation_result[0]:
                return {
                    "success": False,
                    "error": validation_result[1],
                    "error_type": "validation"
                }

            # Calculate risk score
            risk_score = await self.risk_engine.calculate_risk_score(
                application_data)
            application_data['risk_score'] = risk_score

            # Create customer in Razorpay if needed
            customer_data = {
                "name": application_data.get("applicant_name", ""),
                "email": application_data.get("email", ""),
                "mobile": user_mobile,
                "gstin": application_data.get("gstin", ""),
                "company_name": application_data.get("company_name", "")
            }

            customer = await self.razorpay.create_customer(customer_data)
            if customer:
                application_data['customer_id'] = customer.get('id')

            # Create loan application
            loan_application = await self.razorpay.create_loan_application(
                application_data)
            if not loan_application:
                return {
                    "success": False,
                    "error": "Failed to create loan application",
                    "error_type": "api"
                }

            # Store in database
            async with self.db.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO loan_applications (
                        user_mobile, application_id, gstin, company_name, loan_amount,
                        purpose, tenure_months, annual_turnover, monthly_revenue,
                        compliance_score, business_vintage_months, risk_score,
                        status, application_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """, user_mobile, loan_application['id'],
                    application_data.get('gstin'),
                    application_data.get('company_name'),
                    application_data.get('loan_amount'),
                    application_data.get('purpose'),
                    application_data.get('tenure_months'),
                    application_data.get('annual_turnover'),
                    application_data.get('monthly_revenue'),
                    application_data.get('compliance_score'),
                    application_data.get('business_vintage_months'),
                    risk_score, LoanStatus.PENDING.value,
                    json.dumps(application_data))

            logger.info(
                f"✅ Loan application submitted successfully: {loan_application['id']}"
            )

            return {
                "success": True,
                "application_id": loan_application['id'],
                "risk_score": risk_score,
                "status": LoanStatus.PENDING.value,
                "message": "Loan application submitted successfully"
            }

        except Exception as e:
            logger.error(f"❌ Failed to submit loan application: {e}")
            return {"success": False, "error": str(e), "error_type": "system"}

    async def get_user_loan_applications(self, user_mobile: str) -> List[Dict]:
        """Get all loan applications for a user."""
        try:
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM loan_applications 
                    WHERE user_mobile = $1 
                    ORDER BY created_at DESC
                """, user_mobile)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get user loan applications: {e}")
            return []

    async def get_user_active_loans(self, user_mobile: str) -> List[Dict]:
        """Get all active loans for a user."""
        try:
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT al.*, la.company_name, la.gstin 
                    FROM active_loans al
                    JOIN loan_applications la ON al.application_id = la.application_id
                    WHERE al.user_mobile = $1 AND al.status = 'active'
                    ORDER BY al.created_at DESC
                """, user_mobile)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get user active loans: {e}")
            return []


class LoanRiskEngine:
    """Risk assessment engine for loan applications."""

    def __init__(self):
        self.risk_factors = {
            'compliance_score': {
                'weight': 0.3,
                'threshold': 70
            },
            'business_vintage': {
                'weight': 0.2,
                'threshold': 12
            },  # months
            'annual_turnover': {
                'weight': 0.25,
                'threshold': 1000000
            },  # ₹10L
            'loan_to_turnover_ratio': {
                'weight': 0.15,
                'threshold': 0.3
            },
            'filing_regularity': {
                'weight': 0.1,
                'threshold': 0.8
            }
        }

    async def calculate_risk_score(self, application_data: Dict) -> float:
        """
        Calculate risk score for a loan application.

        Args:
            application_data: Application data dictionary

        Returns:
            Risk score between 0-100 (lower is better)
        """
        try:
            total_score = 0.0

            # Compliance score factor
            compliance_score = float(
                application_data.get('compliance_score', 0))
            compliance_factor = max(0, (100 - compliance_score) / 100)
            total_score += compliance_factor * self.risk_factors[
                'compliance_score']['weight']

            # Business vintage factor
            vintage_months = int(
                application_data.get('business_vintage_months', 0))
            vintage_factor = max(0, (24 - vintage_months) /
                                 24)  # 24 months as ideal
            total_score += vintage_factor * self.risk_factors[
                'business_vintage']['weight']

            # Annual turnover factor
            annual_turnover = float(application_data.get('annual_turnover', 0))
            turnover_factor = max(0, (5000000 - annual_turnover) /
                                  5000000)  # ₹50L as ideal
            total_score += turnover_factor * self.risk_factors[
                'annual_turnover']['weight']

            # Loan to turnover ratio factor
            loan_amount = float(application_data.get('loan_amount', 0))
            loan_to_turnover = loan_amount / max(annual_turnover, 1)
            ratio_factor = min(1.0, loan_to_turnover / 0.5)  # 50% as threshold
            total_score += ratio_factor * self.risk_factors[
                'loan_to_turnover_ratio']['weight']

            # Filing regularity (simulated)
            filing_factor = 0.2  # Assume 20% risk from filing irregularities
            total_score += filing_factor * self.risk_factors[
                'filing_regularity']['weight']

            # Convert to 0-100 scale
            risk_score = min(100, total_score * 100)

            return round(risk_score, 2)

        except Exception as e:
            logger.error(f"Risk score calculation failed: {e}")
            return 75.0  # Conservative default risk score


class LoanConfig:
    """Configuration and validation for loan management."""

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
    def validate_loan_application(cls,
                                  application_data: Dict) -> Tuple[bool, str]:
        """
        Validate loan application data.

        Args:
            application_data: Application data dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Required fields
            required_fields = [
                'loan_amount', 'tenure_months', 'purpose', 'annual_turnover',
                'monthly_revenue', 'compliance_score',
                'business_vintage_months', 'gstin', 'company_name'
            ]

            for field in required_fields:
                if field not in application_data or not application_data[field]:
                    return False, f"Missing required field: {field}"

            # Validate numeric fields
            try:
                loan_amount = float(application_data['loan_amount'])
                annual_turnover = float(application_data['annual_turnover'])
                compliance_score = float(application_data['compliance_score'])
                vintage_months = int(
                    application_data['business_vintage_months'])
                tenure_months = int(application_data['tenure_months'])
            except (ValueError, TypeError):
                return False, "Invalid numeric values in application"

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
                max_loan = annual_turnover * cls.MAX_LOAN_TO_TURNOVER_RATIO
                return False, f"Maximum loan amount for your turnover: ₹{max_loan:,.0f}"

            # Check tenure
            if not (6 <= tenure_months <= 60):
                return False, "Loan tenure must be between 6 and 60 months"

            # Validate GSTIN format
            gstin = application_data.get('gstin', '').strip().upper()
            if not re.match(
                    r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$',
                    gstin):
                return False, "Invalid GSTIN format"

            return True, "Validation passed"

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation failed: {str(e)}"

    @classmethod
    def get_eligibility_criteria(cls) -> Dict[str, Any]:
        """Get eligibility criteria for display."""
        return {
            'min_loan_amount': cls.MIN_LOAN_AMOUNT,
            'max_loan_amount': cls.MAX_LOAN_AMOUNT,
            'min_compliance_score': cls.MIN_COMPLIANCE_SCORE,
            'min_business_vintage_months': cls.MIN_BUSINESS_VINTAGE_MONTHS,
            'min_annual_turnover': cls.MIN_ANNUAL_TURNOVER,
            'max_loan_to_turnover_ratio': cls.MAX_LOAN_TO_TURNOVER_RATIO,
            'tenure_range': {
                'min': 6,
                'max': 60
            }
        }


# Export main classes
__all__ = [
    'RazorpayLendingClient', 'LoanManager', 'LoanStatus', 'LoanConfig',
    'LoanRiskEngine', 'LoanApplicationError'
]

if __name__ == "__main__":
    # Test the loan functionality
    import asyncio

    async def test_loan_system():
        # Initialize with test credentials
        client = RazorpayLendingClient("test_key", "test_secret", False)

        print("Loan System Health:")
        health = client.get_health_status()
        for key, value in health.items():
            print(f"  {key}: {value}")

        # Test application validation
        test_application = {
            'loan_amount': 500000,
            'tenure_months': 24,
            'purpose': 'Business expansion',
            'annual_turnover': 2000000,
            'monthly_revenue': 200000,
            'compliance_score': 85,
            'business_vintage_months': 18,
            'gstin': '29AAAPL2356Q1ZS',
            'company_name': 'Test Company Pvt Ltd'
        }

        is_valid, message = LoanConfig.validate_loan_application(
            test_application)
        print(
            f"\nApplication Validation: {'✅ Valid' if is_valid else '❌ Invalid'}"
        )
        print(f"Message: {message}")

        # Test risk score calculation
        risk_engine = LoanRiskEngine()
        risk_score = await risk_engine.calculate_risk_score(test_application)
        print(f"\nRisk Score: {risk_score}%")

    asyncio.run(test_loan_system())

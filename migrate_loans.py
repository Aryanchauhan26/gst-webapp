#!/usr/bin/env python3
"""
Database migration script for loan functionality
Run this to add loan tables to your existing database
"""

import asyncio
import asyncpg
import logging

from config import settings
POSTGRES_DSN = settings.POSTGRES_DSN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_loan_tables():
    """Add loan-related tables to the database"""
    try:
        conn = await asyncpg.connect(dsn=POSTGRES_DSN)
        logger.info("✅ Connected to database successfully")
        
        # Create loan_applications table
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
        """)
        logger.info("✅ Loan applications table created/verified")
        
        # Create loan_offers table
        await conn.execute("""
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
        """)
        logger.info("✅ Loan offers table created/verified")
        
        # Create loan_disbursements table for tracking disbursed loans
        await conn.execute("""
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
        """)
        logger.info("✅ Loan disbursements table created/verified")
        
        # Create loan_repayments table for tracking EMI payments
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_repayments (
                id SERIAL PRIMARY KEY,
                disbursement_id INTEGER NOT NULL,
                razorpay_payment_id VARCHAR(100),
                emi_number INTEGER NOT NULL,
                due_date DATE NOT NULL,
                paid_date TIMESTAMP,
                due_amount DECIMAL(10,2) NOT NULL,
                paid_amount DECIMAL(10,2),
                principal_amount DECIMAL(10,2),
                interest_amount DECIMAL(10,2),
                late_fee DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                payment_method VARCHAR(50),
                payment_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (disbursement_id) REFERENCES loan_disbursements(id) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Loan repayments table created/verified")
        
        # Create indexes for better performance
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_applications_user ON loan_applications(user_mobile);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_applications_status ON loan_applications(status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_applications_gstin ON loan_applications(gstin);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_offers_application ON loan_offers(application_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_disbursements_application ON loan_disbursements(application_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_repayments_disbursement ON loan_repayments(disbursement_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_repayments_due_date ON loan_repayments(due_date);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_repayments_status ON loan_repayments(status);")
        logger.info("✅ Database indexes created/verified")
        
        # Add some useful views
        await conn.execute("""
            CREATE OR REPLACE VIEW loan_summary AS
            SELECT 
                la.id,
                la.user_mobile,
                la.company_name,
                la.gstin,
                la.loan_amount,
                la.status as application_status,
                la.created_at as applied_on,
                COUNT(lo.id) as offers_count,
                MAX(lo.is_accepted) as has_accepted_offer,
                ld.disbursed_amount,
                ld.disbursement_date,
                COUNT(lr.id) as total_emis,
                COUNT(CASE WHEN lr.status = 'paid' THEN 1 END) as paid_emis,
                SUM(CASE WHEN lr.status = 'pending' AND lr.due_date < CURRENT_DATE THEN lr.due_amount ELSE 0 END) as overdue_amount
            FROM loan_applications la
            LEFT JOIN loan_offers lo ON la.id = lo.application_id
            LEFT JOIN loan_disbursements ld ON la.id = ld.application_id
            LEFT JOIN loan_repayments lr ON ld.id = lr.disbursement_id
            GROUP BY la.id, ld.id;
        """)
        logger.info("✅ Loan summary view created")
        
        await conn.close()
        logger.info("🎉 Loan tables migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_loan_tables())
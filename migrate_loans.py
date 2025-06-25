#!/usr/bin/env python3
"""
Complete Database Migration Script for GST Intelligence Platform
Adds loan functionality tables to existing database with proper error handling
"""

import asyncio
import asyncpg
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('migration.log')
    ]
)
logger = logging.getLogger(__name__)

# Try to import from config, fallback to environment variable
try:
    from config import settings
    POSTGRES_DSN = settings.POSTGRES_DSN
except ImportError:
    POSTGRES_DSN = os.getenv("POSTGRES_DSN")
    if not POSTGRES_DSN:
        raise ValueError("POSTGRES_DSN not found in environment variables or config")

class DatabaseMigrator:
    """Complete database migration manager"""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn = None
        
    async def connect(self):
        """Establish database connection"""
        try:
            self.conn = await asyncpg.connect(dsn=self.dsn)
            logger.info("✅ Connected to database successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")
    
    async def check_existing_tables(self) -> dict:
        """Check which tables already exist"""
        existing_tables = {}
        
        tables_to_check = [
            'users', 'sessions', 'search_history', 'user_preferences',
            'loan_applications', 'loan_offers', 'loan_disbursements', 
            'loan_repayments', 'error_logs'
        ]
        
        for table in tables_to_check:
            try:
                result = await self.conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    );
                """, table)
                existing_tables[table] = result
                status = "✅ EXISTS" if result else "❌ MISSING"
                logger.info(f"Table '{table}': {status}")
            except Exception as e:
                logger.error(f"Error checking table {table}: {e}")
                existing_tables[table] = False
        
        return existing_tables
    
    async def create_core_tables(self):
        """Create core application tables"""
        logger.info("🔧 Creating core application tables...")
        
        try:
            # Users table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    mobile VARCHAR(10) PRIMARY KEY,
                    password_hash VARCHAR(128) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP
                );
            """)
            logger.info("✅ Users table created/verified")
            
            # Sessions table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token VARCHAR(64) PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address INET,
                    user_agent TEXT,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            logger.info("✅ Sessions table created/verified")
            
            # Search history table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    mobile VARCHAR(10) NOT NULL,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    compliance_score DECIMAL(5,2),
                    search_data JSONB,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            logger.info("✅ Search history table created/verified")
            
            # User preferences table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    mobile VARCHAR(10) PRIMARY KEY,
                    preferences JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            logger.info("✅ User preferences table created/verified")
            
            # Error logs table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id SERIAL PRIMARY KEY,
                    error_type VARCHAR(100),
                    message TEXT NOT NULL,
                    stack_trace TEXT,
                    url TEXT,
                    user_agent TEXT,
                    user_mobile VARCHAR(10),
                    ip_address INET,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    additional_data JSONB,
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE SET NULL
                );
            """)
            logger.info("✅ Error logs table created/verified")
            
        except Exception as e:
            logger.error(f"❌ Failed to create core tables: {e}")
            raise
    
    async def create_loan_tables(self):
        """Create loan management tables"""
        logger.info("🏦 Creating loan management tables...")
        
        try:
            # Loan applications table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS loan_applications (
                    id SERIAL PRIMARY KEY,
                    user_mobile VARCHAR(10) NOT NULL,
                    razorpay_application_id VARCHAR(100) UNIQUE,
                    gstin VARCHAR(15) NOT NULL,
                    company_name TEXT NOT NULL,
                    loan_amount DECIMAL(15,2) NOT NULL CHECK (loan_amount > 0),
                    purpose TEXT NOT NULL,
                    tenure_months INTEGER NOT NULL CHECK (tenure_months > 0),
                    annual_turnover DECIMAL(15,2) NOT NULL CHECK (annual_turnover > 0),
                    monthly_revenue DECIMAL(15,2) NOT NULL CHECK (monthly_revenue > 0),
                    compliance_score DECIMAL(5,2) NOT NULL CHECK (compliance_score >= 0 AND compliance_score <= 100),
                    business_vintage_months INTEGER NOT NULL CHECK (business_vintage_months > 0),
                    risk_score DECIMAL(5,2) CHECK (risk_score >= 0 AND risk_score <= 100),
                    interest_rate DECIMAL(5,2) CHECK (interest_rate >= 0),
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'under_review', 'approved', 'rejected', 'disbursed', 'closed', 'defaulted')),
                    rejection_reason TEXT,
                    application_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE
                );
            """)
            logger.info("✅ Loan applications table created/verified")
            
            # Loan offers table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS loan_offers (
                    id SERIAL PRIMARY KEY,
                    application_id INTEGER NOT NULL,
                    razorpay_offer_id VARCHAR(100) UNIQUE,
                    loan_amount DECIMAL(15,2) NOT NULL CHECK (loan_amount > 0),
                    interest_rate DECIMAL(5,2) NOT NULL CHECK (interest_rate >= 0),
                    tenure_months INTEGER NOT NULL CHECK (tenure_months > 0),
                    emi_amount DECIMAL(10,2) NOT NULL CHECK (emi_amount > 0),
                    processing_fee DECIMAL(10,2) DEFAULT 0 CHECK (processing_fee >= 0),
                    total_payable DECIMAL(15,2),
                    offer_data JSONB,
                    status VARCHAR(20) DEFAULT 'generated' CHECK (status IN ('generated', 'accepted', 'rejected', 'expired')),
                    is_accepted BOOLEAN DEFAULT FALSE,
                    accepted_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES loan_applications(id) ON DELETE CASCADE
                );
            """)
            logger.info("✅ Loan offers table created/verified")
            
            # Loan disbursements table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS loan_disbursements (
                    id SERIAL PRIMARY KEY,
                    application_id INTEGER NOT NULL,
                    offer_id INTEGER NOT NULL,
                    razorpay_loan_id VARCHAR(100) UNIQUE,
                    disbursed_amount DECIMAL(15,2) NOT NULL CHECK (disbursed_amount > 0),
                    disbursement_date TIMESTAMP NOT NULL,
                    account_number VARCHAR(20),
                    ifsc_code VARCHAR(15),
                    bank_name VARCHAR(100),
                    account_holder_name VARCHAR(100),
                    utr_number VARCHAR(30) UNIQUE,
                    status VARCHAR(20) DEFAULT 'disbursed' CHECK (status IN ('disbursed', 'failed', 'reversed')),
                    disbursement_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES loan_applications(id) ON DELETE CASCADE,
                    FOREIGN KEY (offer_id) REFERENCES loan_offers(id) ON DELETE CASCADE
                );
            """)
            logger.info("✅ Loan disbursements table created/verified")
            
            # Loan repayments table (for EMI tracking)
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS loan_repayments (
                    id SERIAL PRIMARY KEY,
                    disbursement_id INTEGER NOT NULL,
                    razorpay_payment_id VARCHAR(100) UNIQUE,
                    emi_number INTEGER NOT NULL CHECK (emi_number > 0),
                    due_date DATE NOT NULL,
                    paid_date TIMESTAMP,
                    due_amount DECIMAL(10,2) NOT NULL CHECK (due_amount > 0),
                    paid_amount DECIMAL(10,2) CHECK (paid_amount >= 0),
                    principal_amount DECIMAL(10,2) CHECK (principal_amount >= 0),
                    interest_amount DECIMAL(10,2) CHECK (interest_amount >= 0),
                    late_fee DECIMAL(10,2) DEFAULT 0 CHECK (late_fee >= 0),
                    penalty DECIMAL(10,2) DEFAULT 0 CHECK (penalty >= 0),
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'overdue', 'defaulted')),
                    payment_method VARCHAR(50),
                    payment_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (disbursement_id) REFERENCES loan_disbursements(id) ON DELETE CASCADE
                );
            """)
            logger.info("✅ Loan repayments table created/verified")
            
        except Exception as e:
            logger.error(f"❌ Failed to create loan tables: {e}")
            raise
    
    async def create_indexes(self):
        """Create database indexes for performance"""
        logger.info("⚡ Creating database indexes...")
        
        indexes = [
            # Core table indexes
            ("idx_sessions_expires", "sessions", "expires_at"),
            ("idx_sessions_mobile", "sessions", "mobile"),
            ("idx_search_history_mobile", "search_history", "mobile"),
            ("idx_search_history_searched_at", "search_history", "searched_at"),
            ("idx_search_history_gstin", "search_history", "gstin"),
            ("idx_user_preferences_mobile", "user_preferences", "mobile"),
            ("idx_error_logs_created_at", "error_logs", "created_at"),
            ("idx_error_logs_user_mobile", "error_logs", "user_mobile"),
            
            # Loan table indexes
            ("idx_loan_applications_user", "loan_applications", "user_mobile"),
            ("idx_loan_applications_status", "loan_applications", "status"),
            ("idx_loan_applications_gstin", "loan_applications", "gstin"),
            ("idx_loan_applications_created_at", "loan_applications", "created_at"),
            ("idx_loan_offers_application", "loan_offers", "application_id"),
            ("idx_loan_offers_status", "loan_offers", "status"),
            ("idx_loan_offers_expires_at", "loan_offers", "expires_at"),
            ("idx_loan_disbursements_application", "loan_disbursements", "application_id"),
            ("idx_loan_disbursements_date", "loan_disbursements", "disbursement_date"),
            ("idx_loan_repayments_disbursement", "loan_repayments", "disbursement_id"),
            ("idx_loan_repayments_due_date", "loan_repayments", "due_date"),
            ("idx_loan_repayments_status", "loan_repayments", "status"),
        ]
        
        for index_name, table_name, column_name in indexes:
            try:
                await self.conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name});
                """)
                logger.info(f"✅ Index {index_name} created/verified")
            except Exception as e:
                logger.warning(f"⚠️ Failed to create index {index_name}: {e}")
    
    async def create_triggers(self):
        """Create database triggers for automatic updates"""
        logger.info("🔄 Creating database triggers...")
        
        try:
            # Function for updating timestamps
            await self.conn.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            
            # Triggers for tables with updated_at columns
            tables_with_updated_at = [
                'user_preferences', 'loan_applications', 'loan_repayments'
            ]
            
            for table in tables_with_updated_at:
                trigger_name = f"update_{table}_updated_at"
                await self.conn.execute(f"""
                    DROP TRIGGER IF EXISTS {trigger_name} ON {table};
                    CREATE TRIGGER {trigger_name}
                        BEFORE UPDATE ON {table}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """)
                logger.info(f"✅ Trigger {trigger_name} created")
            
            # Function for calculating loan offer totals
            await self.conn.execute("""
                CREATE OR REPLACE FUNCTION calculate_loan_totals()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.total_payable = NEW.emi_amount * NEW.tenure_months;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """)
            
            # Trigger for loan offers
            await self.conn.execute("""
                DROP TRIGGER IF EXISTS calculate_offer_totals ON loan_offers;
                CREATE TRIGGER calculate_offer_totals
                    BEFORE INSERT OR UPDATE ON loan_offers
                    FOR EACH ROW
                    EXECUTE FUNCTION calculate_loan_totals();
            """)
            logger.info("✅ Loan calculation trigger created")
            
        except Exception as e:
            logger.error(f"❌ Failed to create triggers: {e}")
            raise
    
    async def insert_default_data(self):
        """Insert default/seed data"""
        logger.info("🌱 Inserting default data...")
        
        try:
            # Check if admin user exists
            admin_mobile = os.getenv("ADMIN_MOBILE", "9999999999")
            admin_exists = await self.conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM users WHERE mobile = $1)", admin_mobile
            )
            
            if not admin_exists:
                import hashlib
                import secrets
                
                # Create admin user
                admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
                salt = secrets.token_hex(16)
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256', admin_password.encode('utf-8'), 
                    salt.encode('utf-8'), 100000, dklen=64
                ).hex()
                
                await self.conn.execute("""
                    INSERT INTO users (mobile, password_hash, salt, created_at)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                """, admin_mobile, password_hash, salt)
                
                logger.info(f"✅ Admin user created with mobile: {admin_mobile}")
            else:
                logger.info("ℹ️ Admin user already exists")
            
        except Exception as e:
            logger.error(f"❌ Failed to insert default data: {e}")
            # Don't raise here as this is not critical
    
    async def verify_migration(self):
        """Verify migration was successful"""
        logger.info("🔍 Verifying migration...")
        
        try:
            # Check all tables exist
            tables_to_verify = [
                'users', 'sessions', 'search_history', 'user_preferences',
                'loan_applications', 'loan_offers', 'loan_disbursements', 
                'loan_repayments', 'error_logs'
            ]
            
            for table in tables_to_verify:
                count = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                logger.info(f"✅ Table '{table}': {count} rows")
            
            # Check constraints
            constraints = await self.conn.fetch("""
                SELECT conname, contype, pg_get_constraintdef(oid) as definition
                FROM pg_constraint 
                WHERE contype IN ('f', 'c', 'u')
                ORDER BY conname;
            """)
            
            logger.info(f"✅ {len(constraints)} constraints verified")
            
            # Check indexes
            indexes = await self.conn.fetch("""
                SELECT indexname FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname LIKE 'idx_%'
                ORDER BY indexname;
            """)
            
            logger.info(f"✅ {len(indexes)} custom indexes verified")
            
            logger.info("🎉 Migration verification completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            return False

async def main():
    """Main migration function"""
    logger.info("🚀 Starting GST Intelligence Platform Database Migration")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    migrator = DatabaseMigrator(POSTGRES_DSN)
    
    try:
        # Connect to database
        if not await migrator.connect():
            sys.exit(1)
        
        # Check existing tables
        logger.info("📋 Checking existing database structure...")
        existing_tables = await migrator.check_existing_tables()
        
        # Create tables
        await migrator.create_core_tables()
        await migrator.create_loan_tables()
        
        # Create indexes
        await migrator.create_indexes()
        
        # Create triggers
        await migrator.create_triggers()
        
        # Insert default data
        await migrator.insert_default_data()
        
        # Verify migration
        if await migrator.verify_migration():
            logger.info("✅ Migration completed successfully!")
        else:
            logger.error("❌ Migration verification failed!")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        await migrator.close()
    
    logger.info("🏁 Migration script completed")

if __name__ == "__main__":
    # Run migration
    asyncio.run(main())
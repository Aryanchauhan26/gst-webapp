#!/usr/bin/env python3
"""
Database Initialization Script for GST Intelligence Platform
Creates all required tables and indexes for optimal performance
"""

import asyncio
import asyncpg
import logging
import sys
import os
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Try to import from config
try:
    from config import settings
    POSTGRES_DSN = settings.POSTGRES_DSN
except ImportError:
    POSTGRES_DSN = os.getenv("POSTGRES_DSN")
    if not POSTGRES_DSN:
        logger.error("POSTGRES_DSN not found in environment variables")
        sys.exit(1)

class DatabaseInitializer:
    """Database initialization and setup manager."""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn = None
        
    async def connect(self):
        """Establish database connection."""
        try:
            self.conn = await asyncpg.connect(dsn=self.dsn)
            logger.info("✅ Connected to database successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    async def close(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")
    
    async def create_tables(self):
        """Create all required tables."""
        logger.info("🏗️ Creating database tables...")
        
        # Users table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                mobile VARCHAR(10) PRIMARY KEY,
                password_hash VARCHAR(128) NOT NULL,
                salt VARCHAR(32) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN DEFAULT TRUE,
                role VARCHAR(20) DEFAULT 'user',
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        logger.info("✅ Users table created")
        
        # Sessions table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                token VARCHAR(64) UNIQUE NOT NULL,
                mobile VARCHAR(10) NOT NULL,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Sessions table created")
        
        # Search history table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                mobile VARCHAR(10) NOT NULL,
                gstin VARCHAR(15) NOT NULL,
                company_name TEXT,
                compliance_score INTEGER DEFAULT 0,
                status VARCHAR(50),
                raw_data JSONB,
                searched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Search history table created")
        
        # User preferences table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                mobile VARCHAR(10) PRIMARY KEY,
                preferences JSONB DEFAULT '{}',
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ User preferences table created")
        
        # Error logs table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id SERIAL PRIMARY KEY,
                error_type VARCHAR(100),
                message TEXT,
                stack_trace TEXT,
                url VARCHAR(500),
                user_agent TEXT,
                mobile VARCHAR(10),
                context JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE SET NULL
            );
        """)
        logger.info("✅ Error logs table created")
        
        # API usage logs table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id SERIAL PRIMARY KEY,
                mobile VARCHAR(10),
                endpoint VARCHAR(200),
                method VARCHAR(10),
                status_code INTEGER,
                response_time_ms INTEGER,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE SET NULL
            );
        """)
        logger.info("✅ API usage table created")
        
        # System notifications table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                mobile VARCHAR(10),
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR(20) DEFAULT 'info',
                read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP WITH TIME ZONE,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Notifications table created")
        
        # Loan management tables (if loan management is enabled)
        await self.create_loan_tables()
        
    async def create_loan_tables(self):
        """Create loan management tables."""
        logger.info("🏦 Creating loan management tables...")
        
        # Loan applications table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_applications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                mobile VARCHAR(10) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                purpose TEXT NOT NULL,
                tenure_months INTEGER NOT NULL,
                income DECIMAL(12,2),
                company_gstin VARCHAR(15),
                status VARCHAR(20) DEFAULT 'pending',
                application_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Loan applications table created")
        
        # Loan offers table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_offers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                application_id UUID NOT NULL,
                lender_name VARCHAR(100) NOT NULL,
                offered_amount DECIMAL(12,2) NOT NULL,
                interest_rate DECIMAL(5,2) NOT NULL,
                tenure_months INTEGER NOT NULL,
                monthly_emi DECIMAL(10,2) NOT NULL,
                processing_fee DECIMAL(10,2) DEFAULT 0,
                offer_data JSONB,
                expires_at TIMESTAMP WITH TIME ZONE,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES loan_applications(id) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Loan offers table created")
        
        # Loan disbursements table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_disbursements (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                offer_id UUID NOT NULL,
                disbursed_amount DECIMAL(12,2) NOT NULL,
                disbursement_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                bank_reference VARCHAR(100),
                razorpay_order_id VARCHAR(100),
                disbursement_data JSONB,
                status VARCHAR(20) DEFAULT 'processing',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (offer_id) REFERENCES loan_offers(id) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Loan disbursements table created")
        
        # Loan repayments table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_repayments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                disbursement_id UUID NOT NULL,
                emi_number INTEGER NOT NULL,
                due_date DATE NOT NULL,
                due_amount DECIMAL(10,2) NOT NULL,
                paid_amount DECIMAL(10,2) DEFAULT 0,
                paid_date TIMESTAMP WITH TIME ZONE,
                payment_reference VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                late_fee DECIMAL(8,2) DEFAULT 0,
                payment_data JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (disbursement_id) REFERENCES loan_disbursements(id) ON DELETE CASCADE
            );
        """)
        logger.info("✅ Loan repayments table created")
    
    async def create_indexes(self):
        """Create database indexes for optimal performance."""
        logger.info("📊 Creating database indexes...")
        
        # Users indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_mobile ON users(mobile);
            CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
            CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);
            CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        """)
        
        # Sessions indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
            CREATE INDEX IF NOT EXISTS idx_sessions_mobile ON sessions(mobile);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
        """)
        
        # Search history indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);
            CREATE INDEX IF NOT EXISTS idx_search_history_gstin ON search_history(gstin);
            CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at DESC);
            CREATE INDEX IF NOT EXISTS idx_search_history_compliance_score ON search_history(compliance_score);
            CREATE INDEX IF NOT EXISTS idx_search_history_status ON search_history(status);
            CREATE INDEX IF NOT EXISTS idx_search_history_mobile_searched_at ON search_history(mobile, searched_at DESC);
        """)
        
        # User preferences indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_preferences_mobile ON user_preferences(mobile);
            CREATE INDEX IF NOT EXISTS idx_user_preferences_updated_at ON user_preferences(updated_at);
        """)
        
        # Error logs indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);
            CREATE INDEX IF NOT EXISTS idx_error_logs_mobile ON error_logs(mobile);
        """)
        
        # API usage indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_api_usage_mobile ON api_usage(mobile);
            CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint);
            CREATE INDEX IF NOT EXISTS idx_api_usage_status_code ON api_usage(status_code);
        """)
        
        # Notifications indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_mobile ON notifications(mobile);
            CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);
            CREATE INDEX IF NOT EXISTS idx_notifications_expires_at ON notifications(expires_at);
        """)
        
        # Loan management indexes
        await self.create_loan_indexes()
        
        logger.info("✅ All indexes created successfully")
    
    async def create_loan_indexes(self):
        """Create indexes for loan management tables."""
        
        # Loan applications indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_loan_applications_mobile ON loan_applications(mobile);
            CREATE INDEX IF NOT EXISTS idx_loan_applications_status ON loan_applications(status);
            CREATE INDEX IF NOT EXISTS idx_loan_applications_created_at ON loan_applications(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_loan_applications_company_gstin ON loan_applications(company_gstin);
        """)
        
        # Loan offers indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_loan_offers_application_id ON loan_offers(application_id);
            CREATE INDEX IF NOT EXISTS idx_loan_offers_status ON loan_offers(status);
            CREATE INDEX IF NOT EXISTS idx_loan_offers_created_at ON loan_offers(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_loan_offers_expires_at ON loan_offers(expires_at);
        """)
        
        # Loan disbursements indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_loan_disbursements_offer_id ON loan_disbursements(offer_id);
            CREATE INDEX IF NOT EXISTS idx_loan_disbursements_status ON loan_disbursements(status);
            CREATE INDEX IF NOT EXISTS idx_loan_disbursements_disbursement_date ON loan_disbursements(disbursement_date DESC);
            CREATE INDEX IF NOT EXISTS idx_loan_disbursements_razorpay_order_id ON loan_disbursements(razorpay_order_id);
        """)
        
        # Loan repayments indexes
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_loan_repayments_disbursement_id ON loan_repayments(disbursement_id);
            CREATE INDEX IF NOT EXISTS idx_loan_repayments_due_date ON loan_repayments(due_date);
            CREATE INDEX IF NOT EXISTS idx_loan_repayments_status ON loan_repayments(status);
            CREATE INDEX IF NOT EXISTS idx_loan_repayments_emi_number ON loan_repayments(emi_number);
        """)
    
    async def create_functions(self):
        """Create useful database functions."""
        logger.info("⚙️ Creating database functions...")
        
        # Function to update updated_at timestamp
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        # Function to calculate compliance score
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION calculate_user_compliance_avg(user_mobile VARCHAR(10))
            RETURNS DECIMAL(5,2) AS $$
            BEGIN
                RETURN (
                    SELECT COALESCE(AVG(compliance_score), 0)
                    FROM search_history
                    WHERE mobile = user_mobile
                    AND searched_at >= CURRENT_DATE - INTERVAL '30 days'
                );
            END;
            $$ language 'plpgsql';
        """)
        
        # Function to get user search count
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION get_user_search_count(user_mobile VARCHAR(10), days_back INTEGER DEFAULT 30)
            RETURNS INTEGER AS $$
            BEGIN
                RETURN (
                    SELECT COUNT(*)
                    FROM search_history
                    WHERE mobile = user_mobile
                    AND searched_at >= CURRENT_DATE - INTERVAL '1 day' * days_back
                );
            END;
            $$ language 'plpgsql';
        """)
        
        logger.info("✅ Database functions created")
    
    async def create_triggers(self):
        """Create database triggers."""
        logger.info("🔧 Creating database triggers...")
        
        # Trigger to update updated_at on users table
        await self.conn.execute("""
            DROP TRIGGER IF EXISTS update_users_updated_at ON users;
            CREATE TRIGGER update_users_updated_at
                BEFORE UPDATE ON users
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
        
        # Trigger to update updated_at on user_preferences table
        await self.conn.execute("""
            DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences;
            CREATE TRIGGER update_user_preferences_updated_at
                BEFORE UPDATE ON user_preferences
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
        
        # Trigger to update updated_at on loan_applications table
        await self.conn.execute("""
            DROP TRIGGER IF EXISTS update_loan_applications_updated_at ON loan_applications;
            CREATE TRIGGER update_loan_applications_updated_at
                BEFORE UPDATE ON loan_applications
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)
        
        logger.info("✅ Database triggers created")
    
    async def insert_sample_data(self):
        """Insert sample data for testing (optional)."""
        logger.info("📝 Inserting sample data...")
        
        # Check if running in production
        if os.getenv('ENVIRONMENT', '').lower() == 'production':
            logger.info("⚠️ Skipping sample data insertion in production")
            return
        
        # Insert sample admin user (password: admin123)
        try:
            await self.conn.execute("""
                INSERT INTO users (mobile, password_hash, salt, role, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (mobile) DO NOTHING
            """, 
            '9999999999',
            '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92',  # admin123 hash
            'sample_salt_for_admin',
            'admin',
            datetime.now(timezone.utc)
            )
            logger.info("✅ Sample admin user created (mobile: 9999999999, password: admin123)")
        except Exception as e:
            logger.warning(f"Sample data insertion failed: {e}")
    
    async def verify_installation(self):
        """Verify that all tables and indexes were created successfully."""
        logger.info("🔍 Verifying database installation...")
        
        # Check tables
        tables = await self.conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        expected_tables = [
            'users', 'sessions', 'search_history', 'user_preferences',
            'error_logs', 'api_usage', 'notifications',
            'loan_applications', 'loan_offers', 'loan_disbursements', 'loan_repayments'
        ]
        
        created_tables = [row['table_name'] for row in tables]
        
        for table in expected_tables:
            if table in created_tables:
                logger.info(f"✅ Table '{table}' verified")
            else:
                logger.warning(f"⚠️ Table '{table}' not found")
        
        # Check indexes
        indexes = await self.conn.fetch("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public'
            AND indexname LIKE 'idx_%'
        """)
        
        logger.info(f"✅ Created {len(indexes)} custom indexes")
        
        # Check functions
        functions = await self.conn.fetch("""
            SELECT proname FROM pg_proc 
            WHERE pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND proname IN ('update_updated_at_column', 'calculate_user_compliance_avg', 'get_user_search_count')
        """)
        
        logger.info(f"✅ Created {len(functions)} custom functions")
        
        logger.info("🎉 Database verification completed successfully!")
    
    async def run_full_initialization(self):
        """Run complete database initialization."""
        logger.info("🚀 Starting database initialization...")
        
        if not await self.connect():
            return False
        
        try:
            await self.create_tables()
            await self.create_indexes()
            await self.create_functions()
            await self.create_triggers()
            await self.insert_sample_data()
            await self.verify_installation()
            
            logger.info("🎉 Database initialization completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
        finally:
            await self.close()

async def main():
    """Main function to run database initialization."""
    initializer = DatabaseInitializer(POSTGRES_DSN)
    success = await initializer.run_full_initialization()
    
    if success:
        logger.info("✅ Database is ready for GST Intelligence Platform!")
        sys.exit(0)
    else:
        logger.error("❌ Database initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
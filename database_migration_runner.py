#!/usr/bin/env python3
"""
Database Migration Runner for GST Intelligence Platform
This script will run all necessary database migrations and setup
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")

class DatabaseMigrationRunner:
    """Run all database migrations and setup"""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn = None
        
    async def connect(self):
        """Connect to database"""
        try:
            self.conn = await asyncpg.connect(self.dsn)
            logger.info("✅ Connected to database successfully")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from database"""
        if self.conn:
            await self.conn.close()
            logger.info("📤 Disconnected from database")
            
    async def run_migrations(self):
        """Run all database migrations"""
        logger.info("🚀 Starting database migrations...")
        
        try:
            # Start transaction
            async with self.conn.transaction():
                
                # Create core tables
                await self._create_core_tables()
                
                # Create loan tables
                await self._create_loan_tables()
                
                # Create indexes
                await self._create_indexes()
                
                # Create triggers
                await self._create_triggers()
                
                # Verify migrations
                await self._verify_migrations()
                
            logger.info("✅ All migrations completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise
            
    async def _create_core_tables(self):
        """Create core application tables"""
        logger.info("📋 Creating core tables...")
        
        # Users table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                mobile VARCHAR(15) PRIMARY KEY,
                password_hash VARCHAR(128) NOT NULL,
                salt VARCHAR(32) NOT NULL,
                email VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                profile_data JSONB DEFAULT '{}'::jsonb,
                preferences JSONB DEFAULT '{}'::jsonb
            );
        """)
        
        # User sessions table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id VARCHAR(128) PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address INET,
                user_agent TEXT,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        
        # Search history table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                gstin VARCHAR(15) NOT NULL,
                company_name TEXT,
                search_data JSONB,
                compliance_score DECIMAL(5,2),
                ai_synopsis TEXT,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms INTEGER,
                success BOOLEAN DEFAULT TRUE
            );
        """)
        
        logger.info("✅ Core tables created")
        
    async def _create_loan_tables(self):
        """Create loan management tables"""
        logger.info("📋 Creating loan tables...")
        
        # Loan applications table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_applications (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
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
                rejection_reason TEXT,
                application_data JSONB DEFAULT '{}'::jsonb,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Loan offers table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_offers (
                id SERIAL PRIMARY KEY,
                application_id INTEGER NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
                lender_name VARCHAR(255) NOT NULL,
                offered_amount DECIMAL(15,2) NOT NULL,
                interest_rate DECIMAL(5,2) NOT NULL,
                tenure_months INTEGER NOT NULL,
                processing_fee DECIMAL(15,2) DEFAULT 0,
                emi_amount DECIMAL(15,2) NOT NULL,
                total_payable DECIMAL(15,2) NOT NULL,
                offer_valid_until TIMESTAMP NOT NULL,
                terms_conditions TEXT,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Active loans table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS active_loans (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                offer_id INTEGER NOT NULL REFERENCES loan_offers(id) ON DELETE CASCADE,
                loan_account_number VARCHAR(100) UNIQUE NOT NULL,
                disbursed_amount DECIMAL(15,2) NOT NULL,
                disbursed_at TIMESTAMP NOT NULL,
                interest_rate DECIMAL(5,2) NOT NULL,
                tenure_months INTEGER NOT NULL,
                emi_amount DECIMAL(15,2) NOT NULL,
                outstanding_amount DECIMAL(15,2) NOT NULL,
                next_emi_date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # EMI schedule table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS emi_schedule (
                id SERIAL PRIMARY KEY,
                loan_id INTEGER NOT NULL REFERENCES active_loans(id) ON DELETE CASCADE,
                emi_number INTEGER NOT NULL,
                due_date DATE NOT NULL,
                emi_amount DECIMAL(15,2) NOT NULL,
                principal_amount DECIMAL(15,2) NOT NULL,
                interest_amount DECIMAL(15,2) NOT NULL,
                outstanding_balance DECIMAL(15,2) NOT NULL,
                paid_amount DECIMAL(15,2) DEFAULT 0,
                paid_at TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Loan documents table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_documents (
                id SERIAL PRIMARY KEY,
                loan_id INTEGER REFERENCES active_loans(id) ON DELETE CASCADE,
                application_id INTEGER REFERENCES loan_applications(id) ON DELETE CASCADE,
                document_type VARCHAR(100) NOT NULL,
                document_name VARCHAR(255) NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                mime_type VARCHAR(100),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                status VARCHAR(20) DEFAULT 'active'
            );
        """)
        
        logger.info("✅ Loan tables created")
        
    async def _create_indexes(self):
        """Create database indexes for better performance"""
        logger.info("📋 Creating indexes...")
        
        # Core table indexes
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_mobile ON user_sessions(user_mobile);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_gstin ON search_history(gstin);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_search_history_date ON search_history(searched_at);")
        
        # Loan table indexes
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_applications_user ON loan_applications(user_mobile);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_applications_status ON loan_applications(status);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_applications_gstin ON loan_applications(gstin);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_offers_application ON loan_offers(application_id);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_loan_offers_status ON loan_offers(status);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_active_loans_user ON active_loans(user_mobile);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_active_loans_status ON active_loans(status);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_emi_schedule_loan ON emi_schedule(loan_id);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_emi_schedule_due_date ON emi_schedule(due_date);")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_emi_schedule_status ON emi_schedule(status);")
        
        logger.info("✅ Indexes created")
        
    async def _create_triggers(self):
        """Create database triggers"""
        logger.info("📋 Creating triggers...")
        
        # Updated at trigger function
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        # Apply updated_at trigger to tables
        tables_with_updated_at = [
            'loan_applications',
            'loan_offers', 
            'active_loans',
            'emi_schedule'
        ]
        
        for table in tables_with_updated_at:
            await self.conn.execute(f"""
                CREATE TRIGGER trigger_update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)
        
        logger.info("✅ Triggers created")
        
    async def _verify_migrations(self):
        """Verify that all migrations completed successfully"""
        logger.info("📋 Verifying migrations...")
        
        # Check core tables
        core_tables = ['users', 'user_sessions', 'search_history']
        for table in core_tables:
            count = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            logger.info(f"  ✅ Table {table}: {count} records")
            
        # Check loan tables
        loan_tables = ['loan_applications', 'loan_offers', 'active_loans', 'emi_schedule', 'loan_documents']
        for table in loan_tables:
            count = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            logger.info(f"  ✅ Table {table}: {count} records")
            
        # Check indexes
        indexes = await self.conn.fetch("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        
        logger.info(f"  ✅ Created {len(indexes)} indexes")
        
        # Check triggers
        triggers = await self.conn.fetch("""
            SELECT trigger_name, event_object_table 
            FROM information_schema.triggers 
            WHERE trigger_name LIKE 'trigger_%'
        """)
        
        logger.info(f"  ✅ Created {len(triggers)} triggers")
        
        logger.info("✅ Migration verification completed")

async def main():
    """Main migration runner function"""
    logger.info("🚀 Starting GST Intelligence Platform Database Migration")
    logger.info("=" * 60)
    
    if not POSTGRES_DSN:
        logger.error("❌ POSTGRES_DSN environment variable not set")
        return False
        
    runner = DatabaseMigrationRunner(POSTGRES_DSN)
    
    try:
        await runner.connect()
        await runner.run_migrations()
        
        logger.info("=" * 60)
        logger.info("✅ Database migration completed successfully!")
        logger.info("🎉 Your GST Intelligence Platform is ready to use!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
        
    finally:
        await runner.disconnect()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
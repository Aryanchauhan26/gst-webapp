#!/usr/bin/env python3
"""
Complete Database Setup for GST Intelligence Platform
Comprehensive database schema with all required tables for:
- User management and authentication
- GST search and compliance tracking
- Loan management and processing
- System monitoring and analytics
- Error logging and notifications
"""

import asyncio
import asyncpg
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")

class CompleteDatabaseSetup:
    """Complete database setup with all required tables and configurations"""
    
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
            
    async def setup_complete_database(self):
        """Setup complete database with all tables"""
        logger.info("🚀 Starting complete database setup...")
        
        try:
            # Create tables and basic structure in main transaction
            async with self.conn.transaction():
                
                # Create extensions
                await self._create_extensions()
                
                # Create core user tables
                await self._create_user_tables()
                
                # Create GST search and compliance tables
                await self._create_gst_tables()
                
                # Create loan management tables (without foreign keys)
                await self._create_loan_tables_base()
                
                # Create system monitoring tables
                await self._create_system_tables()
                
                # Create triggers and functions
                await self._create_triggers()
            
            # Add foreign key constraints in separate transactions
            await self._add_loan_foreign_keys()
            
            # Create indexes in separate transactions (to avoid transaction aborts)
            await self._create_indexes()
            
            # Verify setup
            await self._verify_setup()
                
            logger.info("✅ Complete database setup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            raise

    async def _create_extensions(self):
        """Create necessary PostgreSQL extensions"""
        logger.info("📋 Creating database extensions...")
        
        try:
            await self.conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
            await self.conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            logger.info("✅ Extensions created successfully")
        except Exception as e:
            logger.warning(f"⚠️ Extension creation warning: {e}")

    async def _create_user_tables(self):
        """Create user management tables"""
        logger.info("📋 Creating user management tables...")
        
        # Users table with enhanced security
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                mobile VARCHAR(15) PRIMARY KEY CHECK (mobile ~ '^[+]?[0-9]{10,15}$'),
                password_hash VARCHAR(255) NOT NULL,
                salt VARCHAR(64) NOT NULL,
                email VARCHAR(255) UNIQUE,
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                failed_login_attempts INTEGER DEFAULT 0,
                last_login_attempt TIMESTAMP,
                last_login TIMESTAMP,
                account_locked_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_password_change TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                two_factor_enabled BOOLEAN DEFAULT FALSE,
                two_factor_secret VARCHAR(32),
                backup_codes TEXT[],
                profile_data JSONB DEFAULT '{}',
                preferences JSONB DEFAULT '{}',
                metadata JSONB DEFAULT '{}'
            );
        """)

        # User profiles table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                mobile VARCHAR(15) PRIMARY KEY REFERENCES users(mobile) ON DELETE CASCADE,
                display_name VARCHAR(255),
                full_name VARCHAR(255),
                company_name VARCHAR(500),
                gstin VARCHAR(15),
                pan VARCHAR(10),
                business_type VARCHAR(100),
                annual_turnover DECIMAL(15,2),
                business_address TEXT,
                city VARCHAR(100),
                state VARCHAR(100),
                pincode VARCHAR(10),
                website VARCHAR(500),
                industry_type VARCHAR(100),
                employee_count INTEGER,
                registration_date DATE,
                compliance_score INTEGER DEFAULT 0,
                risk_category VARCHAR(20) DEFAULT 'UNKNOWN',
                kyc_status VARCHAR(20) DEFAULT 'PENDING',
                profile_completion_percent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Enhanced user sessions table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id VARCHAR(128) PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                session_data JSONB DEFAULT '{}',
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address INET,
                user_agent TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                device_fingerprint VARCHAR(128),
                location_data JSONB
            );
        """)

        logger.info("✅ User management tables created")

    async def _create_gst_tables(self):
        """Create GST search and compliance tables"""
        logger.info("📋 Creating GST search and compliance tables...")
        
        # Basic search history table (for compatibility)
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
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT
            );
        """)

        # Enhanced GST search history table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS gst_search_history (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                gstin VARCHAR(15) NOT NULL,
                company_name TEXT,
                search_type VARCHAR(50) DEFAULT 'basic',
                search_params JSONB DEFAULT '{}',
                search_data JSONB,
                response_data JSONB,
                compliance_score DECIMAL(5,2),
                ai_synopsis TEXT,
                response_time_ms INTEGER,
                api_source VARCHAR(100),
                success BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address INET,
                user_agent TEXT,
                session_id VARCHAR(128)
            );
        """)

        # Compliance tracking table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS compliance_tracking (
                id SERIAL PRIMARY KEY,
                gstin VARCHAR(15) NOT NULL,
                compliance_date DATE NOT NULL,
                overall_score DECIMAL(5,2),
                filing_score DECIMAL(5,2),
                return_score DECIMAL(5,2),
                penalty_score DECIMAL(5,2),
                trend VARCHAR(20),
                risk_level VARCHAR(20),
                compliance_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(gstin, compliance_date)
            );
        """)

        # GST return analysis table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS gst_return_analysis (
                id SERIAL PRIMARY KEY,
                gstin VARCHAR(15) NOT NULL,
                return_period VARCHAR(20) NOT NULL,
                return_type VARCHAR(20) NOT NULL,
                due_date DATE,
                filing_date DATE,
                status VARCHAR(20),
                late_days INTEGER DEFAULT 0,
                penalty_amount DECIMAL(10,2) DEFAULT 0,
                turnover_declared DECIMAL(15,2),
                tax_liability DECIMAL(12,2),
                analysis_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(gstin, return_period, return_type)
            );
        """)

        logger.info("✅ GST search and compliance tables created")

    async def _create_loan_tables_base(self):
        """Create loan management tables without foreign key constraints"""
        logger.info("📋 Creating loan management tables...")
        
        # Loan applications table (base table first)
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
                application_data JSONB DEFAULT '{}',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Loan offers table (without foreign key)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_offers (
                id SERIAL PRIMARY KEY,
                application_id VARCHAR(100) NOT NULL,
                offer_id VARCHAR(100) UNIQUE NOT NULL,
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
                offer_data JSONB DEFAULT '{}',
                is_accepted BOOLEAN DEFAULT FALSE,
                accepted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Active loans table (without foreign keys)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS active_loans (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                loan_id VARCHAR(100) UNIQUE NOT NULL,
                application_id VARCHAR(100) NOT NULL,
                offer_id VARCHAR(100) NOT NULL,
                loan_account_number VARCHAR(100) UNIQUE NOT NULL,
                disbursed_amount DECIMAL(15,2) NOT NULL,
                disbursed_at TIMESTAMP NOT NULL,
                interest_rate DECIMAL(5,2) NOT NULL,
                tenure_months INTEGER NOT NULL,
                emi_amount DECIMAL(15,2) NOT NULL,
                outstanding_amount DECIMAL(15,2) NOT NULL,
                next_emi_date DATE NOT NULL,
                emis_paid INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                agreement_data JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # EMI schedule table (without foreign key)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS emi_schedule (
                id SERIAL PRIMARY KEY,
                loan_id VARCHAR(100) NOT NULL,
                emi_number INTEGER NOT NULL,
                due_date DATE NOT NULL,
                emi_amount DECIMAL(15,2) NOT NULL,
                principal_amount DECIMAL(15,2) NOT NULL,
                interest_amount DECIMAL(15,2) NOT NULL,
                outstanding_balance DECIMAL(15,2) NOT NULL,
                paid_amount DECIMAL(15,2) DEFAULT 0,
                paid_at TIMESTAMP,
                payment_id VARCHAR(100),
                status VARCHAR(20) DEFAULT 'pending',
                late_fee DECIMAL(10,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Loan documents table (without foreign keys)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_documents (
                id SERIAL PRIMARY KEY,
                loan_id VARCHAR(100),
                application_id VARCHAR(100),
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

        logger.info("✅ Loan management tables created")

    async def _add_loan_foreign_keys(self):
        """Add foreign key constraints for loan tables in separate transactions"""
        logger.info("📋 Adding foreign key constraints for loan tables...")
        
        # Check if constraints already exist and add them one by one
        constraints_to_add = [
            {
                'name': 'fk_loan_offers_application',
                'table': 'loan_offers',
                'sql': 'ALTER TABLE loan_offers ADD CONSTRAINT fk_loan_offers_application FOREIGN KEY (application_id) REFERENCES loan_applications(application_id) ON DELETE CASCADE;'
            },
            {
                'name': 'fk_active_loans_application', 
                'table': 'active_loans',
                'sql': 'ALTER TABLE active_loans ADD CONSTRAINT fk_active_loans_application FOREIGN KEY (application_id) REFERENCES loan_applications(application_id);'
            },
            {
                'name': 'fk_active_loans_offer',
                'table': 'active_loans', 
                'sql': 'ALTER TABLE active_loans ADD CONSTRAINT fk_active_loans_offer FOREIGN KEY (offer_id) REFERENCES loan_offers(offer_id);'
            },
            {
                'name': 'fk_emi_schedule_loan',
                'table': 'emi_schedule',
                'sql': 'ALTER TABLE emi_schedule ADD CONSTRAINT fk_emi_schedule_loan FOREIGN KEY (loan_id) REFERENCES active_loans(loan_id) ON DELETE CASCADE;'
            },
            {
                'name': 'fk_loan_documents_loan',
                'table': 'loan_documents',
                'sql': 'ALTER TABLE loan_documents ADD CONSTRAINT fk_loan_documents_loan FOREIGN KEY (loan_id) REFERENCES active_loans(loan_id) ON DELETE CASCADE;'
            },
            {
                'name': 'fk_loan_documents_application',
                'table': 'loan_documents',
                'sql': 'ALTER TABLE loan_documents ADD CONSTRAINT fk_loan_documents_application FOREIGN KEY (application_id) REFERENCES loan_applications(application_id) ON DELETE CASCADE;'
            }
        ]
        
        for constraint in constraints_to_add:
            try:
                # Check if constraint already exists
                exists = await self.conn.fetchval("""
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = $1 AND table_name = $2
                """, constraint['name'], constraint['table'])
                
                if not exists:
                    async with self.conn.transaction():
                        await self.conn.execute(constraint['sql'])
                        logger.info(f"✅ Added constraint: {constraint['name']}")
                else:
                    logger.info(f"⚠️ Constraint already exists: {constraint['name']}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not add constraint {constraint['name']}: {e}")
                # Continue with other constraints
                
        logger.info("✅ Foreign key constraints processing completed")

    async def _create_system_tables(self):
        """Create system monitoring and management tables"""
        logger.info("📋 Creating system monitoring tables...")
        
        # API usage tracking
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS api_usage_logs (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) REFERENCES users(mobile) ON DELETE SET NULL,
                endpoint VARCHAR(255) NOT NULL,
                method VARCHAR(10) NOT NULL,
                request_params JSONB,
                response_status INTEGER,
                response_time_ms INTEGER,
                api_key_used VARCHAR(50),
                rate_limited BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address INET,
                user_agent TEXT,
                request_size_bytes INTEGER,
                response_size_bytes INTEGER
            );
        """)

        # Error logging table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS error_logs (
                id SERIAL PRIMARY KEY,
                error_type VARCHAR(100) NOT NULL,
                error_code VARCHAR(50),
                message TEXT NOT NULL,
                stack_trace TEXT,
                url TEXT,
                method VARCHAR(10),
                user_mobile VARCHAR(15) REFERENCES users(mobile) ON DELETE SET NULL,
                session_id VARCHAR(128),
                request_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                resolution_notes TEXT,
                severity VARCHAR(20) DEFAULT 'ERROR',
                environment VARCHAR(20),
                version VARCHAR(20),
                additional_data JSONB
            );
        """)

        # System health metrics
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id SERIAL PRIMARY KEY,
                metric_name VARCHAR(100) NOT NULL,
                metric_value DECIMAL(15,4),
                metric_unit VARCHAR(20),
                tags JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # User activity logs
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_logs (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                activity_type VARCHAR(100) NOT NULL,
                activity_data JSONB DEFAULT '{}',
                ip_address INET,
                user_agent TEXT,
                session_id VARCHAR(128),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Notification queue
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notification_queue (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) REFERENCES users(mobile) ON DELETE CASCADE,
                notification_type VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                data JSONB DEFAULT '{}',
                delivery_method VARCHAR(20) DEFAULT 'web',
                status VARCHAR(20) DEFAULT 'pending',
                scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                expires_at TIMESTAMP,
                priority INTEGER DEFAULT 5,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 3,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # File uploads tracking
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS file_uploads (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) NOT NULL REFERENCES users(mobile) ON DELETE CASCADE,
                filename VARCHAR(500) NOT NULL,
                original_filename VARCHAR(500) NOT NULL,
                file_size BIGINT NOT NULL,
                mime_type VARCHAR(100),
                file_hash VARCHAR(128),
                storage_path TEXT NOT NULL,
                upload_purpose VARCHAR(100),
                processed BOOLEAN DEFAULT FALSE,
                processing_status VARCHAR(50) DEFAULT 'pending',
                processing_result JSONB,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            );
        """)

        # Audit trail table
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(15) REFERENCES users(mobile) ON DELETE SET NULL,
                action VARCHAR(100) NOT NULL,
                table_name VARCHAR(100),
                record_id VARCHAR(100),
                old_values JSONB,
                new_values JSONB,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        logger.info("✅ System monitoring tables created")

    async def _create_indexes(self):
        """Create database indexes for performance optimization"""
        logger.info("📋 Creating performance indexes...")
        
        # Define indexes with their corresponding tables to validate columns exist
        indexes_config = [
            # User table indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);", "table": "users", "column": "email"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);", "table": "users", "column": "is_active"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);", "table": "users", "column": "created_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_attempt);", "table": "users", "column": "last_login_attempt"},

            # User profiles indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_profiles_company_name ON user_profiles(company_name);", "table": "user_profiles", "column": "company_name"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_profiles_compliance_score ON user_profiles(compliance_score);", "table": "user_profiles", "column": "compliance_score"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_profiles_business_type ON user_profiles(business_type);", "table": "user_profiles", "column": "business_type"},

            # Search history indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_search_history_mobile ON search_history(mobile);", "table": "search_history", "column": "mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_search_history_gstin ON search_history(gstin);", "table": "search_history", "column": "gstin"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);", "table": "search_history", "column": "searched_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_search_history_success ON search_history(success);", "table": "search_history", "column": "success"},

            # GST search history indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_user_mobile ON gst_search_history(user_mobile);", "table": "gst_search_history", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_mobile ON gst_search_history(mobile);", "table": "gst_search_history", "column": "mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_gstin ON gst_search_history(gstin);", "table": "gst_search_history", "column": "gstin"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_created_at ON gst_search_history(created_at);", "table": "gst_search_history", "column": "created_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_searched_at ON gst_search_history(searched_at);", "table": "gst_search_history", "column": "searched_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_success ON gst_search_history(success);", "table": "gst_search_history", "column": "success"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_type ON gst_search_history(search_type);", "table": "gst_search_history", "column": "search_type"},

            # Compliance tracking indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_compliance_gstin_date ON compliance_tracking(gstin, compliance_date);", "table": "compliance_tracking", "column": "gstin"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_compliance_score ON compliance_tracking(overall_score);", "table": "compliance_tracking", "column": "overall_score"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_compliance_risk_level ON compliance_tracking(risk_level);", "table": "compliance_tracking", "column": "risk_level"},

            # GST return analysis indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_return_gstin ON gst_return_analysis(gstin);", "table": "gst_return_analysis", "column": "gstin"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_return_period ON gst_return_analysis(return_period);", "table": "gst_return_analysis", "column": "return_period"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_return_status ON gst_return_analysis(status);", "table": "gst_return_analysis", "column": "status"},

            # Sessions indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_sessions_user_mobile ON user_sessions(user_mobile);", "table": "user_sessions", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);", "table": "user_sessions", "column": "expires_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON user_sessions(is_active);", "table": "user_sessions", "column": "is_active"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON user_sessions(last_activity);", "table": "user_sessions", "column": "last_activity"},

            # Loan table indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loan_applications_user ON loan_applications(user_mobile);", "table": "loan_applications", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loan_applications_status ON loan_applications(status);", "table": "loan_applications", "column": "status"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loan_applications_gstin ON loan_applications(gstin);", "table": "loan_applications", "column": "gstin"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loan_applications_created_at ON loan_applications(created_at);", "table": "loan_applications", "column": "created_at"},
            
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loan_offers_application ON loan_offers(application_id);", "table": "loan_offers", "column": "application_id"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loan_offers_status ON loan_offers(status);", "table": "loan_offers", "column": "status"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loan_offers_valid_until ON loan_offers(offer_valid_until);", "table": "loan_offers", "column": "offer_valid_until"},
            
            {"sql": "CREATE INDEX IF NOT EXISTS idx_active_loans_user ON active_loans(user_mobile);", "table": "active_loans", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_active_loans_status ON active_loans(status);", "table": "active_loans", "column": "status"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_active_loans_next_emi ON active_loans(next_emi_date);", "table": "active_loans", "column": "next_emi_date"},
            
            {"sql": "CREATE INDEX IF NOT EXISTS idx_emi_schedule_loan ON emi_schedule(loan_id);", "table": "emi_schedule", "column": "loan_id"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_emi_schedule_due_date ON emi_schedule(due_date);", "table": "emi_schedule", "column": "due_date"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_emi_schedule_status ON emi_schedule(status);", "table": "emi_schedule", "column": "status"},

            # API usage indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_api_usage_user_mobile ON api_usage_logs(user_mobile);", "table": "api_usage_logs", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage_logs(endpoint);", "table": "api_usage_logs", "column": "endpoint"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage_logs(created_at);", "table": "api_usage_logs", "column": "created_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_api_usage_response_status ON api_usage_logs(response_status);", "table": "api_usage_logs", "column": "response_status"},

            # Error logs indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON error_logs(error_type);", "table": "error_logs", "column": "error_type"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at);", "table": "error_logs", "column": "created_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_error_logs_user_mobile ON error_logs(user_mobile);", "table": "error_logs", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_error_logs_resolved ON error_logs(resolved);", "table": "error_logs", "column": "resolved"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity);", "table": "error_logs", "column": "severity"},

            # System metrics indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_metrics_name_created ON system_metrics(metric_name, created_at);", "table": "system_metrics", "column": "metric_name"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON system_metrics(created_at);", "table": "system_metrics", "column": "created_at"},

            # Activity logs indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_activity_user_mobile ON user_activity_logs(user_mobile);", "table": "user_activity_logs", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_activity_type ON user_activity_logs(activity_type);", "table": "user_activity_logs", "column": "activity_type"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_activity_created_at ON user_activity_logs(created_at);", "table": "user_activity_logs", "column": "created_at"},

            # Notifications indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_notifications_user_mobile ON notification_queue(user_mobile);", "table": "notification_queue", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_notifications_status ON notification_queue(status);", "table": "notification_queue", "column": "status"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notification_queue(scheduled_at);", "table": "notification_queue", "column": "scheduled_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_notifications_priority ON notification_queue(priority);", "table": "notification_queue", "column": "priority"},

            # File uploads indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_uploads_user_mobile ON file_uploads(user_mobile);", "table": "file_uploads", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_uploads_processed ON file_uploads(processed);", "table": "file_uploads", "column": "processed"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON file_uploads(created_at);", "table": "file_uploads", "column": "created_at"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_uploads_expires_at ON file_uploads(expires_at);", "table": "file_uploads", "column": "expires_at"},

            # Audit trail indexes
            {"sql": "CREATE INDEX IF NOT EXISTS idx_audit_trail_user ON audit_trail(user_mobile);", "table": "audit_trail", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_audit_trail_action ON audit_trail(action);", "table": "audit_trail", "column": "action"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at ON audit_trail(created_at);", "table": "audit_trail", "column": "created_at"},

            # Composite indexes for complex queries
            {"sql": "CREATE INDEX IF NOT EXISTS idx_search_history_user_date ON search_history(mobile, searched_at DESC);", "table": "search_history", "column": "mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_gst_search_user_date ON gst_search_history(user_mobile, created_at DESC);", "table": "gst_search_history", "column": "user_mobile"},
            {"sql": "CREATE INDEX IF NOT EXISTS idx_loans_user_status ON loan_applications(user_mobile, status);", "table": "loan_applications", "column": "user_mobile"},
        ]

        # Create indexes one by one in separate transactions
        successful_indexes = 0
        failed_indexes = 0
        
        for index_config in indexes_config:
            try:
                # Check if table and column exist before creating index
                table_exists = await self.conn.fetchval("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = $1 AND table_schema = 'public'
                """, index_config["table"])
                
                if not table_exists:
                    logger.warning(f"⚠️ Skipping index for non-existent table: {index_config['table']}")
                    failed_indexes += 1
                    continue
                
                # Create index in separate transaction
                async with self.conn.transaction():
                    await self.conn.execute(index_config["sql"])
                    successful_indexes += 1
                    
            except Exception as e:
                failed_indexes += 1
                if "already exists" in str(e).lower():
                    logger.debug(f"Index already exists: {index_config['sql']}")
                    successful_indexes += 1  # Count existing indexes as successful
                else:
                    logger.warning(f"Failed to create index: {index_config['sql']} - {e}")

        logger.info(f"✅ Performance indexes created: {successful_indexes} successful, {failed_indexes} failed/skipped")

    async def _create_triggers(self):
        """Create database triggers for automatic operations"""
        logger.info("📋 Creating database triggers...")

        # Updated_at trigger function
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
            'users', 'user_profiles', 'loan_applications', 
            'loan_offers', 'active_loans', 'emi_schedule'
        ]

        for table in tables_with_updated_at:
            await self.conn.execute(f"""
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)

        # Audit trail trigger function
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION audit_trigger_function()
            RETURNS TRIGGER AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    INSERT INTO audit_trail (action, table_name, record_id, old_values)
                    VALUES (TG_OP, TG_TABLE_NAME, OLD.id::TEXT, row_to_json(OLD));
                    RETURN OLD;
                ELSIF TG_OP = 'UPDATE' THEN
                    INSERT INTO audit_trail (action, table_name, record_id, old_values, new_values)
                    VALUES (TG_OP, TG_TABLE_NAME, NEW.id::TEXT, row_to_json(OLD), row_to_json(NEW));
                    RETURN NEW;
                ELSIF TG_OP = 'INSERT' THEN
                    INSERT INTO audit_trail (action, table_name, record_id, new_values)
                    VALUES (TG_OP, TG_TABLE_NAME, NEW.id::TEXT, row_to_json(NEW));
                    RETURN NEW;
                END IF;
                RETURN NULL;
            END;
            $$ language 'plpgsql';
        """)

        # Apply audit triggers to sensitive tables
        audit_tables = ['loan_applications', 'active_loans', 'emi_schedule']
        for table in audit_tables:
            await self.conn.execute(f"""
                DROP TRIGGER IF EXISTS audit_{table}_trigger ON {table};
                CREATE TRIGGER audit_{table}_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION audit_trigger_function();
            """)

        logger.info("✅ Database triggers created")

    async def _verify_setup(self):
        """Verify that all tables and indexes were created successfully"""
        logger.info("📋 Verifying database setup...")
        
        # Check tables
        tables = await self.conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        expected_tables = {
            'users', 'user_profiles', 'user_sessions', 'search_history', 'gst_search_history',
            'compliance_tracking', 'gst_return_analysis', 'loan_applications', 'loan_offers',
            'active_loans', 'emi_schedule', 'loan_documents', 'api_usage_logs', 'error_logs',
            'system_metrics', 'user_activity_logs', 'notification_queue', 'file_uploads', 'audit_trail'
        }
        
        created_tables = {table['table_name'] for table in tables}
        missing_tables = expected_tables - created_tables
        
        if missing_tables:
            logger.error(f"❌ Missing tables: {missing_tables}")
            raise Exception(f"Missing tables: {missing_tables}")
        
        logger.info(f"✅ Created {len(tables)} tables:")
        for table in tables:
            count = await self.conn.fetchval(f"SELECT COUNT(*) FROM {table['table_name']}")
            logger.info(f"  - {table['table_name']}: {count} records")
        
        # Check indexes
        indexes = await self.conn.fetch("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        
        logger.info(f"✅ Created {len(indexes)} indexes")
        
        # Check triggers
        triggers = await self.conn.fetch("""
            SELECT trigger_name, event_object_table 
            FROM information_schema.triggers 
            WHERE trigger_name LIKE 'update_%' OR trigger_name LIKE 'audit_%'
        """)
        
        logger.info(f"✅ Created {len(triggers)} triggers")
        
        logger.info("✅ Database setup verification completed successfully")

async def main():
    """Main setup function"""
    logger.info("🚀 Starting GST Intelligence Platform Complete Database Setup")
    logger.info("=" * 80)
    
    if not POSTGRES_DSN:
        logger.error("❌ POSTGRES_DSN environment variable not set")
        return False
        
    setup = CompleteDatabaseSetup(POSTGRES_DSN)
    
    try:
        await setup.connect()
        await setup.setup_complete_database()
        
        logger.info("=" * 80)
        logger.info("✅ Complete database setup completed successfully!")
        logger.info("🎉 Your GST Intelligence Platform database is ready!")
        logger.info("📊 Database includes:")
        logger.info("   • User management and authentication")
        logger.info("   • GST search and compliance tracking")
        logger.info("   • Loan management system")
        logger.info("   • System monitoring and analytics")
        logger.info("   • Error logging and notifications")
        logger.info("   • Audit trail and security")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        return False
        
    finally:
        await setup.disconnect()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
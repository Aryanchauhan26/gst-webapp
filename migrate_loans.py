#!/usr/bin/env python3
"""
Database migration script for loan functionality
Run this to add loan tables to your existing database
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import from config, fallback to environment variable
try:
    from config import settings
    POSTGRES_DSN = settings.POSTGRES_DSN
except ImportError:
    POSTGRES_DSN = os.getenv("POSTGRES_DSN")
    if not POSTGRES_DSN:
        raise ValueError(
            "POSTGRES_DSN not found in environment variables or config")


class LoanMigration:
    """Database migration manager for loan functionality."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn = None

    async def connect(self):
        """Connect to the database."""
        try:
            self.conn = await asyncpg.connect(dsn=self.dsn)
            logger.info("✅ Connected to database successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the database."""
        if self.conn:
            await self.conn.close()
            logger.info("📤 Disconnected from database")

    async def check_existing_tables(self) -> dict:
        """Check which loan tables already exist."""
        existing_tables = {}

        table_names = [
            'loan_applications', 'loan_offers', 'active_loans', 'emi_schedule',
            'loan_documents'
        ]

        for table_name in table_names:
            try:
                result = await self.conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table_name)
                existing_tables[table_name] = result
            except Exception as e:
                logger.error(f"Error checking table {table_name}: {e}")
                existing_tables[table_name] = False

        return existing_tables

    async def create_loan_applications_table(self):
        """Create loan_applications table."""
        logger.info("📋 Creating loan_applications table...")

        await self.conn.execute("""
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
                rejection_reason TEXT,
                application_data JSONB,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE
            );
        """)

        # Add constraints
        await self.conn.execute("""
            ALTER TABLE loan_applications 
            ADD CONSTRAINT chk_loan_amount 
            CHECK (loan_amount >= 50000 AND loan_amount <= 5000000);
        """)

        await self.conn.execute("""
            ALTER TABLE loan_applications 
            ADD CONSTRAINT chk_tenure_months 
            CHECK (tenure_months >= 6 AND tenure_months <= 60);
        """)

        await self.conn.execute("""
            ALTER TABLE loan_applications 
            ADD CONSTRAINT chk_compliance_score 
            CHECK (compliance_score >= 0 AND compliance_score <= 100);
        """)

        await self.conn.execute("""
            ALTER TABLE loan_applications 
            ADD CONSTRAINT chk_status 
            CHECK (status IN ('pending', 'under_review', 'approved', 'rejected', 'withdrawn'));
        """)

        logger.info("✅ loan_applications table created successfully")

    async def create_loan_offers_table(self):
        """Create loan_offers table."""
        logger.info("📋 Creating loan_offers table...")

        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_offers (
                id SERIAL PRIMARY KEY,
                application_id VARCHAR(100) NOT NULL,
                offer_id VARCHAR(100) UNIQUE NOT NULL,
                lender_name VARCHAR(200) NOT NULL,
                lender_type VARCHAR(50) NOT NULL DEFAULT 'bank',
                loan_amount DECIMAL(15,2) NOT NULL,
                interest_rate DECIMAL(5,2) NOT NULL,
                tenure_months INTEGER NOT NULL,
                emi_amount DECIMAL(10,2) NOT NULL,
                processing_fee DECIMAL(10,2) DEFAULT 0,
                insurance_premium DECIMAL(10,2) DEFAULT 0,
                total_payable DECIMAL(15,2) NOT NULL,
                offer_data JSONB,
                terms_and_conditions TEXT,
                is_accepted BOOLEAN DEFAULT FALSE,
                accepted_at TIMESTAMP,
                valid_until TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES loan_applications(application_id) ON DELETE CASCADE
            );
        """)

        # Add constraints
        await self.conn.execute("""
            ALTER TABLE loan_offers 
            ADD CONSTRAINT chk_interest_rate 
            CHECK (interest_rate >= 5 AND interest_rate <= 36);
        """)

        await self.conn.execute("""
            ALTER TABLE loan_offers 
            ADD CONSTRAINT chk_lender_type 
            CHECK (lender_type IN ('bank', 'nbfc', 'cooperative', 'fintech'));
        """)

        logger.info("✅ loan_offers table created successfully")

    async def create_active_loans_table(self):
        """Create active_loans table."""
        logger.info("📋 Creating active_loans table...")

        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS active_loans (
                id SERIAL PRIMARY KEY,
                user_mobile VARCHAR(10) NOT NULL,
                loan_id VARCHAR(100) UNIQUE NOT NULL,
                application_id VARCHAR(100) NOT NULL,
                offer_id VARCHAR(100) NOT NULL,
                lender_name VARCHAR(200) NOT NULL,
                principal_amount DECIMAL(15,2) NOT NULL,
                outstanding_amount DECIMAL(15,2) NOT NULL,
                interest_rate DECIMAL(5,2) NOT NULL,
                tenure_months INTEGER NOT NULL,
                emis_paid INTEGER DEFAULT 0,
                emis_remaining INTEGER NOT NULL,
                next_emi_date DATE,
                emi_amount DECIMAL(10,2) NOT NULL,
                late_fee_charged DECIMAL(10,2) DEFAULT 0,
                prepayment_charges DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                disbursed_at TIMESTAMP,
                closure_date TIMESTAMP,
                closure_reason VARCHAR(100),
                agreement_data JSONB,
                repayment_schedule JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                FOREIGN KEY (application_id) REFERENCES loan_applications(application_id),
                FOREIGN KEY (offer_id) REFERENCES loan_offers(offer_id)
            );
        """)

        # Add constraints
        await self.conn.execute("""
            ALTER TABLE active_loans 
            ADD CONSTRAINT chk_loan_status 
            CHECK (status IN ('active', 'closed', 'defaulted', 'foreclosed', 'written_off'));
        """)

        await self.conn.execute("""
            ALTER TABLE active_loans 
            ADD CONSTRAINT chk_emis_paid 
            CHECK (emis_paid >= 0 AND emis_paid <= tenure_months);
        """)

        logger.info("✅ active_loans table created successfully")

    async def create_emi_schedule_table(self):
        """Create emi_schedule table."""
        logger.info("📋 Creating emi_schedule table...")

        await self.conn.execute("""
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
                payment_method VARCHAR(50),
                amount_paid DECIMAL(10,2),
                late_fee DECIMAL(10,2) DEFAULT 0,
                penalty DECIMAL(10,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'pending',
                bounce_reason TEXT,
                reminder_sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (loan_id) REFERENCES active_loans(loan_id) ON DELETE CASCADE,
                UNIQUE(loan_id, emi_number)
            );
        """)

        # Add constraints
        await self.conn.execute("""
            ALTER TABLE emi_schedule 
            ADD CONSTRAINT chk_emi_status 
            CHECK (status IN ('pending', 'paid', 'overdue', 'bounced', 'waived', 'partial'));
        """)

        await self.conn.execute("""
            ALTER TABLE emi_schedule 
            ADD CONSTRAINT chk_emi_number 
            CHECK (emi_number > 0);
        """)

        logger.info("✅ emi_schedule table created successfully")

    async def create_loan_documents_table(self):
        """Create loan_documents table."""
        logger.info("📋 Creating loan_documents table...")

        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_documents (
                id SERIAL PRIMARY KEY,
                loan_id VARCHAR(100),
                application_id VARCHAR(100),
                document_type VARCHAR(100) NOT NULL,
                document_name VARCHAR(255) NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                mime_type VARCHAR(100),
                uploaded_by VARCHAR(10) NOT NULL,
                verification_status VARCHAR(20) DEFAULT 'pending',
                verified_by VARCHAR(10),
                verified_at TIMESTAMP,
                rejection_reason TEXT,
                document_data JSONB,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users(mobile),
                FOREIGN KEY (verified_by) REFERENCES users(mobile)
            );
        """)

        # Add constraints
        await self.conn.execute("""
            ALTER TABLE loan_documents 
            ADD CONSTRAINT chk_verification_status 
            CHECK (verification_status IN ('pending', 'verified', 'rejected', 'expired'));
        """)

        await self.conn.execute("""
            ALTER TABLE loan_documents 
            ADD CONSTRAINT chk_document_type 
            CHECK (document_type IN (
                'bank_statement', 'gst_return', 'itr', 'financial_statement', 
                'pan_card', 'aadhaar', 'address_proof', 'business_registration',
                'loan_agreement', 'promissory_note', 'security_document'
            ));
        """)

        logger.info("✅ loan_documents table created successfully")

    async def create_indexes(self):
        """Create indexes for better performance."""
        logger.info("📋 Creating database indexes...")

        indexes = [
            # loan_applications indexes
            ("idx_loan_applications_user_mobile", "loan_applications",
             "user_mobile"),
            ("idx_loan_applications_status", "loan_applications", "status"),
            ("idx_loan_applications_gstin", "loan_applications", "gstin"),
            ("idx_loan_applications_submitted_at", "loan_applications",
             "submitted_at"),

            # loan_offers indexes
            ("idx_loan_offers_application_id", "loan_offers", "application_id"
             ),
            ("idx_loan_offers_valid_until", "loan_offers", "valid_until"),
            ("idx_loan_offers_is_accepted", "loan_offers", "is_accepted"),

            # active_loans indexes
            ("idx_active_loans_user_mobile", "active_loans", "user_mobile"),
            ("idx_active_loans_status", "active_loans", "status"),
            ("idx_active_loans_next_emi_date", "active_loans",
             "next_emi_date"),
            ("idx_active_loans_disbursed_at", "active_loans", "disbursed_at"),

            # emi_schedule indexes
            ("idx_emi_schedule_loan_id", "emi_schedule", "loan_id"),
            ("idx_emi_schedule_due_date", "emi_schedule", "due_date"),
            ("idx_emi_schedule_status", "emi_schedule", "status"),
            ("idx_emi_schedule_loan_due", "emi_schedule",
             "(loan_id, due_date)"),

            # loan_documents indexes
            ("idx_loan_documents_loan_id", "loan_documents", "loan_id"),
            ("idx_loan_documents_application_id", "loan_documents",
             "application_id"),
            ("idx_loan_documents_type", "loan_documents", "document_type"),
            ("idx_loan_documents_verification", "loan_documents",
             "verification_status"),
        ]

        for index_name, table_name, columns in indexes:
            try:
                await self.conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name} {columns}
                """)
                logger.debug(f"  ✅ Created index: {index_name}")
            except Exception as e:
                logger.warning(
                    f"  ⚠️ Failed to create index {index_name}: {e}")

        logger.info("✅ Database indexes created successfully")

    async def create_triggers(self):
        """Create database triggers for automatic updates."""
        logger.info("📋 Creating database triggers...")

        # Update timestamp trigger function
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        # Triggers for updated_at columns
        tables_with_updated_at = [
            'loan_applications', 'loan_offers', 'active_loans', 'emi_schedule',
            'loan_documents'
        ]

        for table_name in tables_with_updated_at:
            try:
                await self.conn.execute(f"""
                    DROP TRIGGER IF EXISTS trigger_update_{table_name}_updated_at ON {table_name};
                    CREATE TRIGGER trigger_update_{table_name}_updated_at
                        BEFORE UPDATE ON {table_name}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """)
                logger.debug(f"  ✅ Created trigger for: {table_name}")
            except Exception as e:
                logger.warning(
                    f"  ⚠️ Failed to create trigger for {table_name}: {e}")

        # Trigger to update loan outstanding amount
        await self.conn.execute("""
            CREATE OR REPLACE FUNCTION update_loan_outstanding()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.status = 'paid' AND OLD.status != 'paid' THEN
                    UPDATE active_loans 
                    SET outstanding_amount = outstanding_amount - NEW.principal_component,
                        emis_paid = emis_paid + 1,
                        emis_remaining = emis_remaining - 1,
                        next_emi_date = (
                            SELECT due_date 
                            FROM emi_schedule 
                            WHERE loan_id = NEW.loan_id 
                            AND status = 'pending' 
                            ORDER BY due_date 
                            LIMIT 1
                        ),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE loan_id = NEW.loan_id;

                    -- Check if loan is fully paid
                    IF (SELECT emis_remaining FROM active_loans WHERE loan_id = NEW.loan_id) = 0 THEN
                        UPDATE active_loans 
                        SET status = 'closed',
                            closure_date = CURRENT_TIMESTAMP,
                            closure_reason = 'full_payment'
                        WHERE loan_id = NEW.loan_id;
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)

        await self.conn.execute("""
            DROP TRIGGER IF EXISTS trigger_update_loan_outstanding ON emi_schedule;
            CREATE TRIGGER trigger_update_loan_outstanding
                AFTER UPDATE ON emi_schedule
                FOR EACH ROW
                EXECUTE FUNCTION update_loan_outstanding();
        """)

        logger.info("✅ Database triggers created successfully")

    async def insert_sample_data(self):
        """Insert sample data for testing."""
        logger.info("📋 Inserting sample data...")

        try:
            # Check if users table exists and has sample data
            user_exists = await self.conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM users WHERE mobile = '9876543210')
            """)

            if not user_exists:
                logger.info("No sample user found, creating one...")
                # Create a sample user for testing
                import hashlib
                import secrets

                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256(
                    ("test123" + salt).encode()).hexdigest()

                await self.conn.execute(
                    """
                    INSERT INTO users (mobile, password_hash, salt, created_at) 
                    VALUES ('9876543210', $1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (mobile) DO NOTHING
                """, password_hash, salt)

                logger.info(
                    "✅ Sample user created (mobile: 9876543210, password: test123)"
                )

            # Insert sample loan application
            await self.conn.execute("""
                INSERT INTO loan_applications (
                    user_mobile, application_id, gstin, company_name, loan_amount,
                    purpose, tenure_months, annual_turnover, monthly_revenue,
                    compliance_score, business_vintage_months, risk_score,
                    status, application_data
                ) VALUES (
                    '9876543210', 'LOAN_APP_SAMPLE_001', '29AAAPL2356Q1ZS', 
                    'Sample Tech Solutions Pvt Ltd', 500000, 'Business Expansion',
                    24, 2000000, 200000, 85.5, 18, 25.3, 'approved',
                    '{"applicant_name": "John Doe", "email": "john@example.com"}'::jsonb
                ) ON CONFLICT (application_id) DO NOTHING
            """)

            # Insert sample loan offer
            await self.conn.execute("""
                INSERT INTO loan_offers (
                    application_id, offer_id, lender_name, lender_type,
                    loan_amount, interest_rate, tenure_months, emi_amount,
                    processing_fee, total_payable, valid_until
                ) VALUES (
                    'LOAN_APP_SAMPLE_001', 'OFFER_SAMPLE_001', 'Sample Bank Ltd', 'bank',
                    500000, 12.5, 24, 23540, 5000, 565000, 
                    CURRENT_TIMESTAMP + INTERVAL '7 days'
                ) ON CONFLICT (offer_id) DO NOTHING
            """)

            logger.info("✅ Sample data inserted successfully")

        except Exception as e:
            logger.warning(f"⚠️ Failed to insert sample data: {e}")

    async def verify_migration(self):
        """Verify that the migration was successful."""
        logger.info("📋 Verifying migration...")

        verification_results = {}

        # Check table existence and record counts
        tables = [
            'loan_applications', 'loan_offers', 'active_loans', 'emi_schedule',
            'loan_documents'
        ]

        for table in tables:
            try:
                count = await self.conn.fetchval(
                    f"SELECT COUNT(*) FROM {table}")
                verification_results[table] = count
                logger.info(f"  ✅ Table {table}: {count} records")
            except Exception as e:
                verification_results[table] = f"Error: {e}"
                logger.error(f"  ❌ Table {table}: {e}")

        # Check indexes
        indexes = await self.conn.fetch("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE tablename IN ('loan_applications', 'loan_offers', 'active_loans', 'emi_schedule', 'loan_documents')
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)

        logger.info(f"  ✅ Created {len(indexes)} custom indexes")

        # Check triggers
        triggers = await self.conn.fetch("""
            SELECT trigger_name, event_object_table 
            FROM information_schema.triggers 
            WHERE event_object_table IN ('loan_applications', 'loan_offers', 'active_loans', 'emi_schedule', 'loan_documents')
            AND trigger_name LIKE 'trigger_%'
        """)

        logger.info(f"  ✅ Created {len(triggers)} triggers")

        return verification_results

    async def rollback_migration(self):
        """Rollback the migration (drop all loan tables)."""
        logger.warning("🔄 Rolling back loan migration...")

        try:
            # Drop tables in reverse order to handle foreign key constraints
            tables = [
                'loan_documents', 'emi_schedule', 'active_loans',
                'loan_offers', 'loan_applications'
            ]

            for table in tables:
                await self.conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE"
                                        )
                logger.info(f"  ✅ Dropped table: {table}")

            # Drop functions
            await self.conn.execute(
                "DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
            await self.conn.execute(
                "DROP FUNCTION IF EXISTS update_loan_outstanding() CASCADE")

            logger.info("✅ Migration rollback completed successfully")

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            raise


async def run_migration(action: str = "migrate"):
    """Run the loan migration."""
    migration = LoanMigration(POSTGRES_DSN)

    try:
        await migration.connect()

        if action == "migrate":
            logger.info("🚀 Starting loan management migration...")

            # Check existing tables
            existing = await migration.check_existing_tables()
            logger.info("📊 Existing tables check:")
            for table, exists in existing.items():
                status = "✅ EXISTS" if exists else "❌ MISSING"
                logger.info(f"  {table}: {status}")

            # Create tables
            await migration.create_loan_applications_table()
            await migration.create_loan_offers_table()
            await migration.create_active_loans_table()
            await migration.create_emi_schedule_table()
            await migration.create_loan_documents_table()

            # Create indexes and triggers
            await migration.create_indexes()
            await migration.create_triggers()

            # Insert sample data
            await migration.insert_sample_data()

            # Verify migration
            results = await migration.verify_migration()

            logger.info("🎉 Loan management migration completed successfully!")
            logger.info(f"📊 Migration summary: {dict(results)}")

        elif action == "rollback":
            await migration.rollback_migration()

        elif action == "verify":
            results = await migration.verify_migration()
            logger.info(f"📊 Verification results: {dict(results)}")

        else:
            logger.error(f"❌ Unknown action: {action}")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await migration.disconnect()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GST Intelligence Platform - Loan Management Migration")
    parser.add_argument("action",
                        choices=["migrate", "rollback", "verify"],
                        default="migrate",
                        nargs="?",
                        help="Migration action to perform")
    parser.add_argument("--verbose",
                        "-v",
                        action="store_true",
                        help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 70)
    print("🏦 GST Intelligence Platform - Loan Management Migration")
    print("=" * 70)
    print(
        f"Database: {POSTGRES_DSN.split('@')[-1] if '@' in POSTGRES_DSN else 'Unknown'}"
    )
    print(f"Action: {args.action.upper()}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        asyncio.run(run_migration(args.action))
        print("\n" + "=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
    except KeyboardInterrupt:
        print("\n❌ Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

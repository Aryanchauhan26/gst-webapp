#!/usr/bin/env python3
"""
GST Intelligence Platform - Deployment & Testing Script
This script performs comprehensive testing and deployment checks
"""

import asyncio
import asyncpg
import httpx
import json
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deployment_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DeploymentTester:
    """Comprehensive deployment and testing utility"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.database_url = os.getenv("POSTGRES_DSN", "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")
        self.test_results = []
        self.start_time = None
        self.conn = None
        
    async def run_all_tests(self):
        """Run all deployment tests"""
        self.start_time = time.time()
        
        print("=" * 80)
        print("🚀 GST Intelligence Platform - Deployment & Testing")
        print("=" * 80)
        
        try:
            # 1. Database Tests
            await self.test_database_connection()
            await self.test_database_schema()
            await self.test_database_operations()
            
            # 2. Application Tests
            await self.test_application_startup()
            await self.test_static_files()
            await self.test_authentication()
            await self.test_api_endpoints()
            
            # 3. UI Tests
            await self.test_page_rendering()
            await self.test_javascript_functionality()
            await self.test_responsive_design()
            
            # 4. Performance Tests
            await self.test_performance()
            
            # 5. Security Tests
            await self.test_security()
            
            # 6. AI Integration Tests
            await self.test_ai_integration()
            
            # Generate report
            self.generate_test_report()
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            self.test_results.append(("CRITICAL", "Test Suite", "Failed", str(e)))
            
        finally:
            await self.cleanup()
            
    async def test_database_connection(self):
        """Test database connectivity"""
        logger.info("🔍 Testing database connection...")
        
        try:
            self.conn = await asyncpg.connect(self.database_url)
            await self.conn.fetchval("SELECT 1")
            
            self.test_results.append(("PASS", "Database", "Connection", "Successfully connected"))
            logger.info("✅ Database connection successful")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Database", "Connection", str(e)))
            logger.error(f"❌ Database connection failed: {e}")
            
    async def test_database_schema(self):
        """Test database schema integrity"""
        logger.info("🔍 Testing database schema...")
        
        if not self.conn:
            self.test_results.append(("SKIP", "Database", "Schema", "No connection"))
            return
            
        try:
            # Check core tables
            core_tables = ['users', 'user_sessions', 'gst_search_history']
            for table in core_tables:
                result = await self.conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                if result:
                    self.test_results.append(("PASS", "Database", f"Table {table}", "Exists"))
                else:
                    self.test_results.append(("FAIL", "Database", f"Table {table}", "Missing"))
                    
            # Check loan tables
            loan_tables = ['loan_applications', 'loan_offers', 'active_loans', 'emi_schedule']
            for table in loan_tables:
                result = await self.conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                if result:
                    self.test_results.append(("PASS", "Database", f"Loan Table {table}", "Exists"))
                else:
                    self.test_results.append(("WARN", "Database", f"Loan Table {table}", "Missing"))
                    
            # Check indexes
            indexes = await self.conn.fetch(
                "SELECT indexname FROM pg_indexes WHERE indexname LIKE 'idx_%'"
            )
            
            if len(indexes) > 0:
                self.test_results.append(("PASS", "Database", "Indexes", f"{len(indexes)} indexes found"))
            else:
                self.test_results.append(("WARN", "Database", "Indexes", "No custom indexes found"))
                
            logger.info("✅ Database schema check completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Database", "Schema", str(e)))
            logger.error(f"❌ Database schema check failed: {e}")
            
    async def test_database_operations(self):
        """Test basic database operations"""
        logger.info("🔍 Testing database operations...")
        
        if not self.conn:
            self.test_results.append(("SKIP", "Database", "Operations", "No connection"))
            return
            
        try:
            # Test user creation
            test_mobile = "9999999999"
            test_password = "test_password_hash"
            test_salt = "test_salt"
            
            # Clean up any existing test data
            await self.conn.execute("DELETE FROM users WHERE mobile = $1", test_mobile)
            
            # Insert test user
            await self.conn.execute(
                "INSERT INTO users (mobile, password_hash, salt) VALUES ($1, $2, $3)",
                test_mobile, test_password, test_salt
            )
            
            # Verify insertion
            result = await self.conn.fetchrow(
                "SELECT mobile, password_hash, salt FROM users WHERE mobile = $1",
                test_mobile
            )
            
            if result and result['mobile'] == test_mobile:
                self.test_results.append(("PASS", "Database", "User Operations", "CRUD operations working"))
            else:
                self.test_results.append(("FAIL", "Database", "User Operations", "CRUD operations failed"))
                
            # Clean up
            await self.conn.execute("DELETE FROM users WHERE mobile = $1", test_mobile)
            
            logger.info("✅ Database operations test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Database", "Operations", str(e)))
            logger.error(f"❌ Database operations test failed: {e}")
            
    async def test_application_startup(self):
        """Test application startup and health"""
        logger.info("🔍 Testing application startup...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test health endpoint
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    self.test_results.append(("PASS", "Application", "Health Check", "Application is healthy"))
                    
                    # Check database health
                    if health_data.get('database', {}).get('status') == 'healthy':
                        self.test_results.append(("PASS", "Application", "Database Health", "Database is healthy"))
                    else:
                        self.test_results.append(("WARN", "Application", "Database Health", "Database health issues"))
                        
                    # Check AI service health
                    if health_data.get('ai_service', {}).get('status') == 'healthy':
                        self.test_results.append(("PASS", "Application", "AI Service", "AI service is healthy"))
                    else:
                        self.test_results.append(("WARN", "Application", "AI Service", "AI service issues"))
                        
                else:
                    self.test_results.append(("FAIL", "Application", "Health Check", f"Status: {response.status_code}"))
                    
            logger.info("✅ Application startup test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Application", "Startup", str(e)))
            logger.error(f"❌ Application startup test failed: {e}")
            
    async def test_static_files(self):
        """Test static file serving"""
        logger.info("🔍 Testing static file serving...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                static_files = [
                    "/static/css/base.css",
                    "/static/js/app.js",
                    "/static/js/app-core.js",
                    "/static/js/dashboard.js",
                    "/static/manifest.json",
                    "/favicon.ico"
                ]
                
                for file_path in static_files:
                    try:
                        response = await client.get(f"{self.base_url}{file_path}")
                        if response.status_code == 200:
                            self.test_results.append(("PASS", "Static Files", file_path, "File served successfully"))
                        else:
                            self.test_results.append(("FAIL", "Static Files", file_path, f"Status: {response.status_code}"))
                    except Exception as e:
                        self.test_results.append(("FAIL", "Static Files", file_path, str(e)))
                        
            logger.info("✅ Static file serving test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Static Files", "General", str(e)))
            logger.error(f"❌ Static file serving test failed: {e}")
            
    async def test_authentication(self):
        """Test authentication system"""
        logger.info("🔍 Testing authentication system...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test login page
                response = await client.get(f"{self.base_url}/login")
                if response.status_code == 200:
                    self.test_results.append(("PASS", "Authentication", "Login Page", "Login page loads"))
                else:
                    self.test_results.append(("FAIL", "Authentication", "Login Page", f"Status: {response.status_code}"))
                    
                # Test signup page
                response = await client.get(f"{self.base_url}/signup")
                if response.status_code == 200:
                    self.test_results.append(("PASS", "Authentication", "Signup Page", "Signup page loads"))
                else:
                    self.test_results.append(("FAIL", "Authentication", "Signup Page", f"Status: {response.status_code}"))
                    
                # Test protected route redirect
                response = await client.get(f"{self.base_url}/", follow_redirects=False)
                if response.status_code in [302, 303]:
                    self.test_results.append(("PASS", "Authentication", "Protection", "Protected routes redirect"))
                else:
                    self.test_results.append(("WARN", "Authentication", "Protection", "Protected routes may not be working"))
                    
            logger.info("✅ Authentication test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Authentication", "General", str(e)))
            logger.error(f"❌ Authentication test failed: {e}")
            
    async def test_api_endpoints(self):
        """Test API endpoints"""
        logger.info("🔍 Testing API endpoints...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test API endpoints that should be accessible
                api_endpoints = [
                    "/api/user/profile",
                    "/api/user/stats",
                    "/api/loans/eligibility"
                ]
                
                for endpoint in api_endpoints:
                    try:
                        response = await client.get(f"{self.base_url}{endpoint}")
                        # These should return 401/403 for unauthorized access
                        if response.status_code in [401, 403]:
                            self.test_results.append(("PASS", "API", endpoint, "Endpoint exists and protected"))
                        elif response.status_code == 200:
                            self.test_results.append(("WARN", "API", endpoint, "Endpoint accessible without auth"))
                        else:
                            self.test_results.append(("FAIL", "API", endpoint, f"Status: {response.status_code}"))
                    except Exception as e:
                        self.test_results.append(("FAIL", "API", endpoint, str(e)))
                        
            logger.info("✅ API endpoints test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "API", "General", str(e)))
            logger.error(f"❌ API endpoints test failed: {e}")
            
    async def test_page_rendering(self):
        """Test page rendering"""
        logger.info("🔍 Testing page rendering...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test public pages
                public_pages = [
                    "/login",
                    "/signup"
                ]
                
                for page in public_pages:
                    try:
                        response = await client.get(f"{self.base_url}{page}")
                        if response.status_code == 200:
                            content = response.text
                            
                            # Check for basic HTML structure
                            if "<!DOCTYPE html>" in content and "<html" in content:
                                self.test_results.append(("PASS", "Page Rendering", page, "Valid HTML structure"))
                            else:
                                self.test_results.append(("FAIL", "Page Rendering", page, "Invalid HTML structure"))
                                
                            # Check for CSS inclusion
                            if "/static/css/base.css" in content:
                                self.test_results.append(("PASS", "Page Rendering", f"{page} CSS", "CSS included"))
                            else:
                                self.test_results.append(("FAIL", "Page Rendering", f"{page} CSS", "CSS not included"))
                                
                            # Check for JavaScript inclusion
                            if "/static/js/app.js" in content:
                                self.test_results.append(("PASS", "Page Rendering", f"{page} JS", "JavaScript included"))
                            else:
                                self.test_results.append(("FAIL", "Page Rendering", f"{page} JS", "JavaScript not included"))
                                
                        else:
                            self.test_results.append(("FAIL", "Page Rendering", page, f"Status: {response.status_code}"))
                            
                    except Exception as e:
                        self.test_results.append(("FAIL", "Page Rendering", page, str(e)))
                        
            logger.info("✅ Page rendering test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Page Rendering", "General", str(e)))
            logger.error(f"❌ Page rendering test failed: {e}")
            
    async def test_javascript_functionality(self):
        """Test JavaScript functionality"""
        logger.info("🔍 Testing JavaScript functionality...")
        
        try:
            # Check if JavaScript files exist and are valid
            js_files = [
                "static/js/app.js",
                "static/js/app-core.js",
                "static/js/dashboard.js",
                "static/js/missing-globals.js"
            ]
            
            for js_file in js_files:
                file_path = Path(js_file)
                if file_path.exists():
                    content = file_path.read_text()
                    
                    # Basic JavaScript validation
                    if "function" in content or "class" in content or "const" in content:
                        self.test_results.append(("PASS", "JavaScript", js_file, "Valid JavaScript content"))
                    else:
                        self.test_results.append(("WARN", "JavaScript", js_file, "May not contain valid JavaScript"))
                        
                    # Check for common issues
                    if "console.log" in content:
                        self.test_results.append(("INFO", "JavaScript", js_file, "Contains console.log statements"))
                        
                else:
                    self.test_results.append(("FAIL", "JavaScript", js_file, "File not found"))
                    
            logger.info("✅ JavaScript functionality test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "JavaScript", "General", str(e)))
            logger.error(f"❌ JavaScript functionality test failed: {e}")
            
    async def test_responsive_design(self):
        """Test responsive design elements"""
        logger.info("🔍 Testing responsive design...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/login")
                
                if response.status_code == 200:
                    content = response.text
                    
                    # Check for viewport meta tag
                    if 'name="viewport"' in content:
                        self.test_results.append(("PASS", "Responsive", "Viewport", "Viewport meta tag present"))
                    else:
                        self.test_results.append(("FAIL", "Responsive", "Viewport", "Viewport meta tag missing"))
                        
                    # Check for responsive CSS classes
                    responsive_indicators = [
                        "mobile-nav",
                        "@media",
                        "flex",
                        "grid"
                    ]
                    
                    for indicator in responsive_indicators:
                        if indicator in content:
                            self.test_results.append(("PASS", "Responsive", f"CSS {indicator}", f"{indicator} found"))
                        else:
                            self.test_results.append(("WARN", "Responsive", f"CSS {indicator}", f"{indicator} not found"))
                            
                else:
                    self.test_results.append(("SKIP", "Responsive", "Design", "Cannot access pages"))
                    
            logger.info("✅ Responsive design test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Responsive", "General", str(e)))
            logger.error(f"❌ Responsive design test failed: {e}")
            
    async def test_performance(self):
        """Test application performance"""
        logger.info("🔍 Testing application performance...")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test response times
                test_urls = [
                    "/health",
                    "/login",
                    "/signup",
                    "/static/css/base.css",
                    "/static/js/app.js"
                ]
                
                for url in test_urls:
                    try:
                        start_time = time.time()
                        response = await client.get(f"{self.base_url}{url}")
                        end_time = time.time()
                        
                        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                        
                        if response.status_code == 200:
                            if response_time < 1000:  # Less than 1 second
                                self.test_results.append(("PASS", "Performance", url, f"Response time: {response_time:.2f}ms"))
                            elif response_time < 3000:  # Less than 3 seconds
                                self.test_results.append(("WARN", "Performance", url, f"Slow response: {response_time:.2f}ms"))
                            else:
                                self.test_results.append(("FAIL", "Performance", url, f"Very slow response: {response_time:.2f}ms"))
                        else:
                            self.test_results.append(("FAIL", "Performance", url, f"Status: {response.status_code}"))
                            
                    except Exception as e:
                        self.test_results.append(("FAIL", "Performance", url, str(e)))
                        
            logger.info("✅ Performance test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Performance", "General", str(e)))
            logger.error(f"❌ Performance test failed: {e}")
            
    async def test_security(self):
        """Test security measures"""
        logger.info("🔍 Testing security measures...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test for security headers
                response = await client.get(f"{self.base_url}/login")
                
                if response.status_code == 200:
                    headers = response.headers
                    
                    # Check for security headers
                    security_headers = [
                        "X-Content-Type-Options",
                        "X-Frame-Options",
                        "X-XSS-Protection"
                    ]
                    
                    for header in security_headers:
                        if header in headers:
                            self.test_results.append(("PASS", "Security", header, "Security header present"))
                        else:
                            self.test_results.append(("WARN", "Security", header, "Security header missing"))
                            
                    # Check for HTTPS redirect in production
                    if "https://" in str(response.url):
                        self.test_results.append(("PASS", "Security", "HTTPS", "Using HTTPS"))
                    else:
                        self.test_results.append(("WARN", "Security", "HTTPS", "Not using HTTPS (OK for development)"))
                        
                else:
                    self.test_results.append(("SKIP", "Security", "Headers", "Cannot access pages"))
                    
            logger.info("✅ Security test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "Security", "General", str(e)))
            logger.error(f"❌ Security test failed: {e}")
            
    async def test_ai_integration(self):
        """Test AI integration"""
        logger.info("🔍 Testing AI integration...")
        
        try:
            # Test AI module import
            try:
                sys.path.append(str(Path(__file__).parent))
                from anthro_ai import get_ai_health, generate_fallback_synopsis
                
                self.test_results.append(("PASS", "AI Integration", "Import", "AI module imports successfully"))
                
                # Test AI health
                health = get_ai_health()
                if health.get('has_anthropic_package'):
                    self.test_results.append(("PASS", "AI Integration", "Package", "Anthropic package available"))
                else:
                    self.test_results.append(("WARN", "AI Integration", "Package", "Anthropic package not available"))
                    
                if health.get('has_api_key'):
                    self.test_results.append(("PASS", "AI Integration", "API Key", "API key configured"))
                else:
                    self.test_results.append(("WARN", "AI Integration", "API Key", "API key not configured"))
                    
                # Test fallback synopsis
                test_data = {
                    'gstin': '29AAAPL2356Q1ZS',
                    'legal_name': 'Test Company Pvt Ltd',
                    'business_status': 'Active',
                    'filing_status': 'Regular',
                    'compliance_score': 85
                }
                
                fallback_synopsis = generate_fallback_synopsis(test_data)
                if fallback_synopsis and len(fallback_synopsis) > 10:
                    self.test_results.append(("PASS", "AI Integration", "Fallback", "Fallback synopsis works"))
                else:
                    self.test_results.append(("FAIL", "AI Integration", "Fallback", "Fallback synopsis failed"))
                    
            except ImportError as e:
                self.test_results.append(("FAIL", "AI Integration", "Import", str(e)))
                
            logger.info("✅ AI integration test completed")
            
        except Exception as e:
            self.test_results.append(("FAIL", "AI Integration", "General", str(e)))
            logger.error(f"❌ AI integration test failed: {e}")
            
    def generate_test_report(self):
        """Generate comprehensive test report"""
        total_time = time.time() - self.start_time
        
        # Count results by status
        status_counts = {}
        for result in self.test_results:
            status = result[0]
            status_counts[status] = status_counts.get(status, 0) + 1
            
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("📊 GST Intelligence Platform - Test Report")
        report.append("=" * 80)
        report.append(f"🕐 Test Duration: {total_time:.2f} seconds")
        report.append(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        report.append("📈 Test Summary:")
        report.append("-" * 40)
        for status, count in sorted(status_counts.items()):
            emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'WARN': '⚠️',
                'INFO': 'ℹ️',
                'SKIP': '⏭️',
                'CRITICAL': '🚨'
            }.get(status, '❓')
            report.append(f"{emoji} {status}: {count}")
        report.append("")
        
        # Detailed results
        report.append("📋 Detailed Results:")
        report.append("-" * 40)
        
        current_category = None
        for result in self.test_results:
            status, category, test_name, message = result
            
            if category != current_category:
                report.append(f"\n🔧 {category}:")
                current_category = category
                
            emoji = {
                'PASS': '✅',
                'FAIL': '❌',
                'WARN': '⚠️',
                'INFO': 'ℹ️',
                'SKIP': '⏭️',
                'CRITICAL': '🚨'
            }.get(status, '❓')
            
            report.append(f"  {emoji} {test_name}: {message}")
            
        report.append("")
        
        # Recommendations
        report.append("💡 Recommendations:")
        report.append("-" * 40)
        
        fail_count = status_counts.get('FAIL', 0)
        warn_count = status_counts.get('WARN', 0)
        
        if fail_count == 0 and warn_count == 0:
            report.append("🎉 All tests passed! Your application is ready for deployment.")
        elif fail_count == 0:
            report.append("✅ No critical issues found. Review warnings before deployment.")
        else:
            report.append("❌ Critical issues found. Please fix failed tests before deployment.")
            
        if status_counts.get('WARN', 0) > 0:
            report.append("⚠️ Address warnings to improve application quality.")
            
        report.append("")
        report.append("=" * 80)
        
        # Print report
        report_text = "\n".join(report)
        print(report_text)
        
        # Save report to file
        with open(f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
            f.write(report_text)
            
        logger.info("📄 Test report saved to file")
        
    async def cleanup(self):
        """Clean up resources"""
        if self.conn:
            await self.conn.close()
            logger.info("🧹 Database connection closed")

async def main():
    """Main function to run deployment tests"""
    tester = DeploymentTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
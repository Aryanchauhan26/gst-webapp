#!/usr/bin/env python3
"""
Comprehensive Test Suite for GST Intelligence Platform
Tests all major functionality including API endpoints, database operations, and business logic
"""

import pytest
import asyncio
import asyncpg
import httpx
import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Test configuration
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/test_gst"
TEST_ENV = {
    "ENVIRONMENT": "testing",
    "DEBUG": "true",
    "POSTGRES_DSN": TEST_DATABASE_URL,
    "SECRET_KEY": "test-secret-key",
    "RAPIDAPI_KEY": "test-api-key",
    "RAPIDAPI_HOST": "test-host.com"
}

# Apply test environment
for key, value in TEST_ENV.items():
    os.environ[key] = value

# Import application modules after setting environment
try:
    from main import app
    from database import DatabaseManager
    from utils import validate_mobile, validate_gstin, GSTAPIClient
    from models import UserSignupRequest, GSTINSearchRequest
    from config import settings
except ImportError as e:
    pytest.skip(f"Could not import application modules: {e}", allow_module_level=True)

# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Setup test database."""
    try:
        # Create test database connection
        conn = await asyncpg.connect(TEST_DATABASE_URL)
        
        # Clean up any existing test data
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
        
        # Initialize database
        db_manager = DatabaseManager(TEST_DATABASE_URL)
        await db_manager.initialize()
        
        # Create tables
        from init_database import DatabaseInitializer
        initializer = DatabaseInitializer(TEST_DATABASE_URL)
        await initializer.create_tables()
        await initializer.create_indexes()
        await initializer.create_functions()
        
        await conn.close()
        
        yield db_manager
        
        # Cleanup
        await db_manager.close()
        
    except Exception as e:
        pytest.skip(f"Could not setup test database: {e}")

@pytest.fixture
async def client():
    """Create test client."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_user(test_db):
    """Create test user."""
    test_mobile = "9876543210"
    test_password = "testpass123"
    
    from utils import hash_password
    password_hash, salt = hash_password(test_password)
    
    await test_db.create_user(test_mobile, password_hash, salt)
    
    return {
        "mobile": test_mobile,
        "password": test_password,
        "password_hash": password_hash,
        "salt": salt
    }

@pytest.fixture
async def authenticated_client(client, test_user):
    """Create authenticated test client."""
    # Login
    login_response = await client.post("/login", data={
        "mobile": test_user["mobile"],
        "password": test_user["password"]
    })
    
    assert login_response.status_code == 302  # Redirect after login
    
    return client

# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_validate_mobile(self):
        """Test mobile number validation."""
        # Valid cases
        assert validate_mobile("9876543210") == (True, "9876543210")
        assert validate_mobile("8765432109") == (True, "8765432109")
        assert validate_mobile("7654321098") == (True, "7654321098")
        assert validate_mobile("6543210987") == (True, "6543210987")
        
        # Invalid cases
        assert validate_mobile("")[0] == False
        assert validate_mobile("123456789")[0] == False  # Too short
        assert validate_mobile("12345678901")[0] == False  # Too long
        assert validate_mobile("5876543210")[0] == False  # Invalid first digit
        assert validate_mobile("abcdefghij")[0] == False  # Non-numeric
        
    def test_validate_gstin(self):
        """Test GSTIN validation."""
        # Valid GSTIN
        valid_gstin = "07AABCU9603R1ZX"
        assert validate_gstin(valid_gstin) == (True, valid_gstin)
        
        # Invalid cases
        assert validate_gstin("")[0] == False
        assert validate_gstin("07AABCU9603R1Z")[0] == False  # Too short
        assert validate_gstin("07AABCU9603R1ZXY")[0] == False  # Too long
        assert validate_gstin("07aabcu9603r1zx")[0] == False  # Lowercase
        assert validate_gstin("07AABCU9603R1Z0")[0] == False  # Invalid format

# =============================================================================
# DATABASE TESTS
# =============================================================================

class TestDatabase:
    """Test database operations."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_db):
        """Test user creation."""
        mobile = "9876543211"
        password_hash = "test_hash"
        salt = "test_salt"
        
        # Create user
        result = await test_db.create_user(mobile, password_hash, salt)
        assert result == True
        
        # Try to create same user again (should fail)
        result = await test_db.create_user(mobile, password_hash, salt)
        assert result == False
        
    @pytest.mark.asyncio
    async def test_verify_user(self, test_db, test_user):
        """Test user verification."""
        # Valid credentials
        result = await test_db.verify_user(test_user["mobile"], test_user["password"])
        assert result == True
        
        # Invalid password
        result = await test_db.verify_user(test_user["mobile"], "wrongpassword")
        assert result == False
        
        # Non-existent user
        result = await test_db.verify_user("9999999999", "anypassword")
        assert result == False
        
    @pytest.mark.asyncio
    async def test_session_management(self, test_db, test_user):
        """Test session creation and validation."""
        mobile = test_user["mobile"]
        
        # Create session
        token = await test_db.create_session(mobile)
        assert token is not None
        assert len(token) > 20
        
        # Validate session
        user_from_session = await test_db.get_user_from_session(token)
        assert user_from_session == mobile
        
        # Delete session
        await test_db.delete_session(token)
        
        # Validate deleted session
        user_from_session = await test_db.get_user_from_session(token)
        assert user_from_session is None
        
    @pytest.mark.asyncio
    async def test_search_history(self, test_db, test_user):
        """Test search history operations."""
        mobile = test_user["mobile"]
        gstin = "07AABCU9603R1ZX"
        company_data = {
            "company_name": "Test Company",
            "status": "Active",
            "compliance_score": 85
        }
        
        # Save search
        await test_db.save_search(mobile, gstin, company_data)
        
        # Get search history
        history = await test_db.get_search_history(mobile)
        assert len(history) >= 1
        assert history[0]["gstin"] == gstin
        assert history[0]["company_name"] == company_data["company_name"]

# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class TestAPIEndpoints:
    """Test API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "checks" in data
        
    @pytest.mark.asyncio
    async def test_home_page_redirect(self, client):
        """Test home page redirects to login for unauthenticated users."""
        response = await client.get("/")
        assert response.status_code == 302  # Redirect to login
        
    @pytest.mark.asyncio
    async def test_login_page(self, client):
        """Test login page access."""
        response = await client.get("/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()
        
    @pytest.mark.asyncio
    async def test_signup_page(self, client):
        """Test signup page access."""
        response = await client.get("/signup")
        assert response.status_code == 200
        assert "signup" in response.text.lower()
        
    @pytest.mark.asyncio
    async def test_user_signup(self, client):
        """Test user signup process."""
        signup_data = {
            "mobile": "9876543212",
            "password": "testpass123",
            "confirm_password": "testpass123"
        }
        
        response = await client.post("/signup", data=signup_data)
        assert response.status_code == 302  # Redirect after successful signup
        
    @pytest.mark.asyncio
    async def test_user_login(self, client, test_user):
        """Test user login process."""
        login_data = {
            "mobile": test_user["mobile"],
            "password": test_user["password"]
        }
        
        response = await client.post("/login", data=login_data)
        assert response.status_code == 302  # Redirect after successful login
        
    @pytest.mark.asyncio
    async def test_authenticated_home_page(self, authenticated_client):
        """Test home page access for authenticated users."""
        response = await authenticated_client.get("/")
        assert response.status_code == 200
        assert "dashboard" in response.text.lower()
        
    @pytest.mark.asyncio
    async def test_user_stats_api(self, authenticated_client):
        """Test user statistics API."""
        response = await authenticated_client.get("/api/user/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        assert "total_searches" in data["data"]

# =============================================================================
# BUSINESS LOGIC TESTS
# =============================================================================

class TestBusinessLogic:
    """Test business logic and workflows."""
    
    @pytest.mark.asyncio
    async def test_gstin_search_workflow(self, authenticated_client):
        """Test complete GSTIN search workflow."""
        # Mock the API response
        with patch('utils.GSTAPIClient.search_gstin') as mock_search:
            mock_search.return_value = {
                "gstin": "07AABCU9603R1ZX",
                "company_name": "Test Company Ltd",
                "status": "Active",
                "compliance_score": 85
            }
            
            # Perform search
            search_data = {"gstin": "07AABCU9603R1ZX"}
            response = await authenticated_client.post("/search", data=search_data)
            
            # Should redirect to results page or show results
            assert response.status_code in [200, 302]
            
    @pytest.mark.asyncio
    async def test_search_history_workflow(self, authenticated_client, test_db, test_user):
        """Test search history workflow."""
        # Add some search history
        await test_db.save_search(
            test_user["mobile"],
            "07AABCU9603R1ZX",
            {
                "company_name": "Test Company",
                "status": "Active",
                "compliance_score": 75
            }
        )
        
        # Access history page
        response = await authenticated_client.get("/history")
        assert response.status_code == 200
        assert "history" in response.text.lower()
        
    @pytest.mark.asyncio
    async def test_analytics_workflow(self, authenticated_client):
        """Test analytics workflow."""
        response = await authenticated_client.get("/analytics")
        assert response.status_code == 200
        assert "analytics" in response.text.lower()

# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurity:
    """Test security features."""
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client):
        """Test that protected routes require authentication."""
        protected_routes = ["/", "/search", "/history", "/analytics", "/admin"]
        
        for route in protected_routes:
            response = await client.get(route)
            assert response.status_code in [302, 401, 403]  # Redirect or unauthorized
            
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, authenticated_client):
        """Test SQL injection protection."""
        # Try SQL injection in search
        malicious_data = {"gstin": "'; DROP TABLE users; --"}
        response = await authenticated_client.post("/search", data=malicious_data)
        
        # Should not cause server error
        assert response.status_code != 500
        
    @pytest.mark.asyncio
    async def test_input_validation(self, client):
        """Test input validation."""
        # Invalid signup data
        invalid_signup = {
            "mobile": "invalid",
            "password": "123",  # Too short
            "confirm_password": "456"  # Doesn't match
        }
        
        response = await client.post("/signup", data=invalid_signup)
        # Should show validation errors, not crash
        assert response.status_code in [200, 400]

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_database_connection_pool(self, test_db):
        """Test database connection pooling."""
        # Create multiple concurrent connections
        tasks = []
        for i in range(10):
            task = test_db.get_user_profile(f"test_user_{i}")
            tasks.append(task)
        
        # All should complete without errors
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that no exceptions occurred
        for result in results:
            assert not isinstance(result, Exception)
            
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, authenticated_client):
        """Test handling concurrent requests."""
        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            task = authenticated_client.get("/api/user/stats")
            tasks.append(task)
        
        # All should complete successfully
        responses = await asyncio.gather(*tasks)
        
        for response in responses:
            assert response.status_code == 200

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Test integration with external services."""
    
    @pytest.mark.asyncio
    async def test_gst_api_integration(self):
        """Test GST API integration (mocked)."""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "gstin": "07AABCU9603R1ZX",
                "tradeNam": "Test Company",
                "sts": "Active"
            }
            mock_get.return_value = mock_response
            
            # Test API client
            api_client = GSTAPIClient("test-key", "test-host")
            result = await api_client.search_gstin("07AABCU9603R1ZX")
            
            assert result["gstin"] == "07AABCU9603R1ZX"
            assert result["company_name"] == "Test Company"
            assert result["status"] == "Active"

# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test handling of database connection failures."""
        # Create database manager with invalid DSN
        invalid_db = DatabaseManager("postgresql://invalid:invalid@localhost:9999/invalid")
        
        # Should handle connection failure gracefully
        with pytest.raises(Exception):
            await invalid_db.initialize()
            
    @pytest.mark.asyncio
    async def test_api_timeout_handling(self, authenticated_client):
        """Test API timeout handling."""
        with patch('httpx.AsyncClient.get') as mock_get:
            # Mock timeout
            import httpx
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            # Search should handle timeout gracefully
            response = await authenticated_client.post("/search", data={"gstin": "07AABCU9603R1ZX"})
            
            # Should not crash the application
            assert response.status_code != 500

# =============================================================================
# TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    # Run tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "--cov=.",
        "--cov-report=html",
        "--cov-report=term-missing"
    ])

# =============================================================================
# ADDITIONAL TEST FILES
# =============================================================================

# Create test configuration file
test_config_content = '''
"""
Test configuration for GST Intelligence Platform
"""

import os

# Test database
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/test_gst"

# Test user credentials
TEST_USER_MOBILE = "9876543210"
TEST_USER_PASSWORD = "testpass123"

# Mock API responses
MOCK_GST_RESPONSE = {
    "gstin": "07AABCU9603R1ZX",
    "tradeNam": "Test Company Ltd",
    "sts": "Active",
    "rgdt": "2020-01-01",
    "ctb": "Private Limited Company"
}

# Test timeouts
API_TIMEOUT = 30
DB_TIMEOUT = 10
'''

# Create pytest configuration
pytest_ini_content = '''
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --asyncio-mode=auto
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    security: marks tests as security tests
asyncio_mode = auto
'''

# Save additional test files
def create_test_files():
    """Create additional test files."""
    import pathlib
    
    test_dir = pathlib.Path("tests")
    test_dir.mkdir(exist_ok=True)
    
    # Test configuration
    (test_dir / "conftest.py").write_text(test_config_content)
    
    # Pytest configuration
    pathlib.Path("pytest.ini").write_text(pytest_ini_content)
    
    print("✅ Test files created successfully!")
    print("Run tests with: pytest tests/ -v")

if __name__ == "__main__":
    create_test_files()
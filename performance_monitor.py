# performance_monitor.py - Add this to your project
import time
import asyncio
from functools import wraps
from datetime import datetime
import logging
from typing import Dict, List
import json

# Performance monitoring decorator
def monitor_performance(operation_name: str):
    """Decorator to monitor API endpoint performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            operation_id = f"{operation_name}_{int(time.time())}"
            
            try:
                result = await func(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                
                # Log performance metrics
                await PerformanceMonitor.log_metric(
                    operation=operation_name,
                    duration=duration,
                    status="success",
                    operation_id=operation_id
                )
                
                return result
                
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                
                await PerformanceMonitor.log_metric(
                    operation=operation_name,
                    duration=duration,
                    status="error",
                    error=str(e),
                    operation_id=operation_id
                )
                raise
                
        return wrapper
    return decorator

class PerformanceMonitor:
    """Free performance monitoring system"""
    
    def __init__(self):
        self.metrics = []
        self.alerts = []
        self.thresholds = {
            'search_gstin': 5.0,  # 5 seconds max
            'generate_pdf': 10.0,  # 10 seconds max
            'database_query': 2.0,  # 2 seconds max
        }
    
    @staticmethod
    async def log_metric(operation: str, duration: float, status: str, 
                        error: str = None, operation_id: str = None):
        """Log performance metric to database"""
        metric_data = {
            'operation': operation,
            'duration': duration,
            'status': status,
            'timestamp': datetime.now(),
            'error': error,
            'operation_id': operation_id
        }
        
        # Store in database (extend your existing PostgresDB class)
        # await db.store_performance_metric(metric_data)
        
        # Console logging for development
        logging.info(f"PERF: {operation} took {duration:.2f}s - {status}")
        
        # Check for alerts
        await PerformanceMonitor.check_alerts(operation, duration)
    
    @staticmethod
    async def check_alerts(operation: str, duration: float):
        """Check if performance thresholds are exceeded"""
        monitor = PerformanceMonitor()
        threshold = monitor.thresholds.get(operation, 30.0)
        
        if duration > threshold:
            alert = {
                'type': 'performance_degradation',
                'operation': operation,
                'duration': duration,
                'threshold': threshold,
                'timestamp': datetime.now(),
                'severity': 'high' if duration > threshold * 2 else 'medium'
            }
            
            # Log alert
            logging.warning(f"ALERT: {operation} exceeded threshold: {duration:.2f}s > {threshold}s")
            
            # Store alert in database
            # await db.store_alert(alert)

# Add to your main.py - Enhanced routes with monitoring

@monitor_performance('search_gstin')
@app.post("/search")
async def search_gstin_monitored(request: Request, gstin: str = Form(...), 
                                current_user: str = Depends(require_auth)):
    """Enhanced search with performance monitoring"""
    start_time = time.time()
    
    try:
        # Your existing search logic
        company_data = await api_client.fetch_gstin_data(gstin)
        compliance_score = calculate_compliance_score(company_data)
        
        # Log successful search metrics
        search_duration = time.time() - start_time
        await log_user_activity(current_user, 'search', {
            'gstin': gstin,
            'duration': search_duration,
            'compliance_score': compliance_score
        })
        
        return templates.TemplateResponse("results.html", {
            "request": request,
            "mobile": current_user,
            "company_data": company_data,
            "compliance_score": int(compliance_score),
            "performance_metrics": {
                'search_time': f"{search_duration:.2f}s",
                'cache_hit': False  # Implement caching
            }
        })
        
    except Exception as e:
        # Log error metrics
        error_duration = time.time() - start_time
        await log_user_activity(current_user, 'search_error', {
            'gstin': gstin,
            'error': str(e),
            'duration': error_duration
        })
        raise

# User Activity Tracking
async def log_user_activity(user_id: str, activity_type: str, metadata: dict):
    """Log user activity for analytics"""
    activity_data = {
        'user_id': user_id,
        'activity_type': activity_type,
        'metadata': json.dumps(metadata),
        'timestamp': datetime.now(),
        'ip_address': '127.0.0.1',  # Get from request in real implementation
        'user_agent': 'GST-Intelligence-App'  # Get from request
    }
    
    # Store in database
    try:
        await db.connect()
        async with db.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_activities (user_id, activity_type, metadata, timestamp, ip_address, user_agent)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, *activity_data.values())
    except Exception as e:
        logging.error(f"Failed to log user activity: {e}")

# Real-time Performance Dashboard API
@app.get("/api/performance-metrics")
async def get_performance_metrics(current_user: str = Depends(require_auth)):
    """Get real-time performance metrics"""
    await db.connect()
    async with db.pool.acquire() as conn:
        # Get recent performance data
        recent_searches = await conn.fetch("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as search_count,
                AVG(CAST(metadata->>'duration' AS FLOAT)) as avg_duration
            FROM user_activities 
            WHERE activity_type = 'search' 
            AND timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour
        """)
        
        # Get error rates
        error_rates = await conn.fetch("""
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as error_count
            FROM user_activities 
            WHERE activity_type = 'search_error' 
            AND timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour
        """)
        
        # Get top slow queries
        slow_queries = await conn.fetch("""
            SELECT 
                metadata->>'gstin' as gstin,
                CAST(metadata->>'duration' AS FLOAT) as duration
            FROM user_activities 
            WHERE activity_type = 'search' 
            AND CAST(metadata->>'duration' AS FLOAT) > 3.0
            AND timestamp >= NOW() - INTERVAL '24 hours'
            ORDER BY duration DESC
            LIMIT 10
        """)
    
    return {
        "search_trends": [dict(row) for row in recent_searches],
        "error_rates": [dict(row) for row in error_rates],
        "slow_queries": [dict(row) for row in slow_queries],
        "current_load": await get_current_system_load()
    }

async def get_current_system_load():
    """Get current system performance metrics"""
    import psutil
    
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'active_connections': await get_active_connections_count()
    }

async def get_active_connections_count():
    """Get count of active database connections"""
    try:
        await db.connect()
        async with db.pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COUNT(*) FROM pg_stat_activity 
                WHERE state = 'active' AND datname = current_database()
            """)
            return result
    except:
        return 0

# Caching Layer for Performance
import redis
from typing import Optional

class CacheManager:
    """Simple Redis-like caching (use in-memory dict if Redis not available)"""
    
    def __init__(self):
        try:
            # Try Redis first
            self.redis = redis.Redis(host='localhost', port=6379, db=0)
            self.redis.ping()
            self.use_redis = True
        except:
            # Fallback to in-memory cache
            self.cache = {}
            self.use_redis = False
            logging.info("Using in-memory cache (Redis not available)")
    
    async def get(self, key: str) -> Optional[str]:
        """Get cached value"""
        try:
            if self.use_redis:
                return self.redis.get(key)
            else:
                return self.cache.get(key)
        except:
            return None
    
    async def set(self, key: str, value: str, expire_seconds: int = 3600):
        """Set cached value with expiration"""
        try:
            if self.use_redis:
                self.redis.setex(key, expire_seconds, value)
            else:
                # Simple in-memory cache with expiration
                import time
                self.cache[key] = {
                    'value': value,
                    'expires': time.time() + expire_seconds
                }
                # Clean expired entries
                self._clean_expired()
        except Exception as e:
            logging.error(f"Cache set error: {e}")
    
    def _clean_expired(self):
        """Clean expired cache entries"""
        import time
        current_time = time.time()
        expired_keys = [
            k for k, v in self.cache.items() 
            if isinstance(v, dict) and v.get('expires', 0) < current_time
        ]
        for key in expired_keys:
            del self.cache[key]

# Initialize cache manager
cache_manager = CacheManager()

# Enhanced search with caching
@monitor_performance('search_gstin_cached')
async def search_gstin_with_cache(gstin: str):
    """Search with caching for performance"""
    cache_key = f"gstin:{gstin}"
    
    # Try cache first
    cached_result = await cache_manager.get(cache_key)
    if cached_result:
        logging.info(f"Cache hit for GSTIN: {gstin}")
        return json.loads(cached_result)
    
    # Cache miss - fetch from API
    logging.info(f"Cache miss for GSTIN: {gstin}")
    company_data = await api_client.fetch_gstin_data(gstin)
    
    # Cache the result for 1 hour
    await cache_manager.set(
        cache_key, 
        json.dumps(company_data, default=str), 
        expire_seconds=3600
    )
    
    return company_data

# Database Performance Monitoring
CREATE_PERFORMANCE_TABLES = """
-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    operation VARCHAR(100) NOT NULL,
    duration FLOAT NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    operation_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- User activities table for analytics
CREATE TABLE IF NOT EXISTS user_activities (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- System alerts table
CREATE TABLE IF NOT EXISTS system_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation ON performance_metrics(operation, timestamp);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_user_activities_type ON user_activities(activity_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_system_alerts_unack ON system_alerts(acknowledged, severity, timestamp);
"""

# Add rate limiting for API protection
from collections import defaultdict
import asyncio

class RateLimiter:
    """Enhanced rate limiter with different tiers"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            'search': {'requests': 100, 'window': 3600},  # 100 searches per hour
            'export': {'requests': 10, 'window': 3600},   # 10 exports per hour
            'api': {'requests': 1000, 'window': 3600}     # 1000 API calls per hour
        }
    
    async def is_allowed(self, user_id: str, operation_type: str = 'api') -> bool:
        """Check if request is allowed based on rate limits"""
        now = time.time()
        limit_config = self.limits.get(operation_type, self.limits['api'])
        window = limit_config['window']
        max_requests = limit_config['requests']
        
        # Clean old requests
        user_requests = self.requests[f"{user_id}:{operation_type}"]
        self.requests[f"{user_id}:{operation_type}"] = [
            req_time for req_time in user_requests 
            if now - req_time < window
        ]
        
        # Check if under limit
        if len(self.requests[f"{user_id}:{operation_type}"]) < max_requests:
            self.requests[f"{user_id}:{operation_type}"].append(now)
            return True
        
        return False
    
    async def get_reset_time(self, user_id: str, operation_type: str = 'api') -> int:
        """Get seconds until rate limit resets"""
        user_requests = self.requests[f"{user_id}:{operation_type}"]
        if not user_requests:
            return 0
        
        oldest_request = min(user_requests)
        window = self.limits.get(operation_type, self.limits['api'])['window']
        reset_time = oldest_request + window - time.time()
        
        return max(0, int(reset_time))

# Initialize rate limiter
rate_limiter = RateLimiter()

# Middleware for rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests"""
    
    # Skip rate limiting for static files and health checks
    if request.url.path.startswith('/static/') or request.url.path == '/health':
        return await call_next(request)
    
    # Get user ID from session
    user_id = 'anonymous'
    session_token = request.cookies.get('session_token')
    if session_token:
        user_id = await db.get_session(session_token) or 'anonymous'
    
    # Determine operation type
    operation_type = 'api'
    if 'search' in request.url.path:
        operation_type = 'search'
    elif 'export' in request.url.path:
        operation_type = 'export'
    
    # Check rate limit
    if not await rate_limiter.is_allowed(user_id, operation_type):
        reset_time = await rate_limiter.get_reset_time(user_id, operation_type)
        
        return JSONResponse(
            status_code=429,
            content={
                'error': 'Rate limit exceeded',
                'retry_after': reset_time,
                'limit_type': operation_type
            },
            headers={'Retry-After': str(reset_time)}
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = rate_limiter.limits[operation_type]['requests'] - len(
        rate_limiter.requests[f"{user_id}:{operation_type}"]
    )
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Limit'] = str(rate_limiter.limits[operation_type]['requests'])
    
    return response

# Health check with detailed metrics
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with performance metrics"""
    
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now(),
        'version': '2.0.0',
        'uptime': time.time() - start_time,  # Define start_time when app starts
        'checks': {}
    }
    
    # Database health
    try:
        start = time.time()
        await db.connect()
        async with db.pool.acquire() as conn:
            await conn.execute('SELECT 1')
        db_time = time.time() - start
        health_data['checks']['database'] = {
            'status': 'healthy',
            'response_time': f"{db_time:.3f}s"
        }
    except Exception as e:
        health_data['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_data['status'] = 'degraded'
    
    # API health
    try:
        start = time.time()
        # Test API with a known GSTIN
        test_data = await api_client.fetch_gstin_data("27AABCT1332L1ZN")
        api_time = time.time() - start
        health_data['checks']['gst_api'] = {
            'status': 'healthy',
            'response_time': f"{api_time:.3f}s"
        }
    except Exception as e:
        health_data['checks']['gst_api'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_data['status'] = 'degraded'
    
    # System metrics
    try:
        import psutil
        health_data['checks']['system'] = {
            'status': 'healthy',
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
    except ImportError:
        health_data['checks']['system'] = {
            'status': 'unknown',
            'error': 'psutil not available'
        }
    
    # Cache health
    try:
        await cache_manager.set('health_check', 'ok', 60)
        cached = await cache_manager.get('health_check')
        health_data['checks']['cache'] = {
            'status': 'healthy' if cached else 'degraded',
            'type': 'redis' if cache_manager.use_redis else 'memory'
        }
    except Exception as e:
        health_data['checks']['cache'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    return health_data

# Error tracking and alerting
class ErrorTracker:
    """Simple error tracking system"""
    
    @staticmethod
    async def track_error(error: Exception, context: dict):
        """Track application errors"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': json.dumps(context),
            'timestamp': datetime.now(),
            'severity': 'high' if isinstance(error, (ConnectionError, TimeoutError)) else 'medium'
        }
        
        # Log to database
        try:
            await db.connect()
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO system_alerts (alert_type, severity, message, metadata)
                    VALUES ($1, $2, $3, $4)
                """, 'application_error', error_data['severity'], 
                error_data['error_message'], json.dumps(error_data))
        except Exception as db_error:
            logging.error(f"Failed to log error to database: {db_error}")
        
        # Log to console
        logging.error(f"ERROR: {error_data['error_type']}: {error_data['error_message']}")
        
        # Send alert for critical errors
        if error_data['severity'] == 'high':
            await ErrorTracker.send_alert(error_data)
    
    @staticmethod
    async def send_alert(error_data: dict):
        """Send alert for critical errors (implement email/webhook)"""
        # For now, just log
        logging.critical(f"CRITICAL ERROR ALERT: {error_data}")
        
        # TODO: Implement email notifications
        # TODO: Implement webhook notifications to Discord/Slack

# Global error handler with tracking
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with error tracking"""
    
    context = {
        'url': str(request.url),
        'method': request.method,
        'user_agent': request.headers.get('user-agent'),
        'ip': request.client.host if request.client else 'unknown'
    }
    
    await ErrorTracker.track_error(exc, context)
    
    return JSONResponse(
        status_code=500,
        content={
            'error': 'An internal error occurred',
            'error_id': int(time.time()),  # Simple error ID
            'message': 'Please try again later or contact support'
        }
    )
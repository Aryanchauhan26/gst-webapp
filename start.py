#!/usr/bin/env python3
"""
Enhanced GST Intelligence Platform Launcher
Comprehensive startup script with health checks, configuration validation, and graceful shutdown
"""

import os
import sys
import signal
import asyncio
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import time
import socket
import json
from contextlib import asynccontextmanager

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import uvicorn
    import asyncpg
    from fastapi import FastAPI
    import httpx
except ImportError as e:
    print(f"❌ Missing required dependencies: {e}")
    print("💡 Please run: pip install -r requirements.txt")
    sys.exit(1)

# Configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_WORKERS = 1
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', mode='a') if os.path.exists('logs') else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

class ApplicationLauncher:
    """Enhanced application launcher with comprehensive startup checks"""
    
    def __init__(self):
        self.app_process: Optional[subprocess.Popen] = None
        self.shutdown_event = asyncio.Event()
        self.health_check_url = None
        self.startup_timeout = 60  # seconds
        
    async def pre_startup_checks(self, skip_checks: bool = False) -> bool:
        """Perform comprehensive pre-startup validation"""
        if skip_checks:
            logger.info("⚠️ Skipping startup checks as requested")
            return True
            
        logger.info("🔍 Performing pre-startup checks...")
        
        checks = [
            ("Environment Variables", self._check_environment),
            ("Required Files", self._check_required_files),
            ("Database Connection", self._check_database_connection),
            ("Port Availability", self._check_port_availability),
            ("Dependencies", self._check_dependencies),
            ("Directory Structure", self._check_directories),
            ("Configuration Files", self._check_configuration),
        ]
        
        failed_checks = []
        
        for check_name, check_func in checks:
            try:
                logger.info(f"  ✓ Checking {check_name}...")
                result = await check_func()
                if not result:
                    failed_checks.append(check_name)
                    logger.error(f"  ❌ {check_name} check failed")
                else:
                    logger.info(f"  ✅ {check_name} check passed")
            except Exception as e:
                failed_checks.append(check_name)
                logger.error(f"  ❌ {check_name} check failed with error: {e}")
        
        if failed_checks:
            logger.error(f"❌ Startup checks failed: {', '.join(failed_checks)}")
            return False
        
        logger.info("✅ All pre-startup checks passed!")
        return True
    
    async def _check_environment(self) -> bool:
        """Check required environment variables"""
        required_vars = ["DATABASE_URL"]
        optional_vars = ["RAPIDAPI_KEY", "ANTHROPIC_API_KEY", "SECRET_KEY"]
        
        missing_required = [var for var in required_vars if not os.getenv(var)]
        missing_optional = [var for var in optional_vars if not os.getenv(var)]
        
        if missing_required:
            logger.error(f"Missing required environment variables: {missing_required}")
            return False
        
        if missing_optional:
            logger.warning(f"Missing optional environment variables: {missing_optional}")
        
        return True
    
    async def _check_required_files(self) -> bool:
        """Check if all required files exist"""
        required_files = [
            "main.py",
            "requirements.txt",
            "templates/base.html",
            "static/css/base.css",
            "static/js/app.js"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"Missing required files: {missing_files}")
            return False
        
        return True
    
    async def _check_database_connection(self) -> bool:
        """Test database connectivity"""
        try:
            conn = await asyncpg.connect(DATABASE_URL, timeout=10)
            await conn.fetchval("SELECT 1")
            await conn.close()
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    async def _check_port_availability(self) -> bool:
        """Check if the port is available"""
        host = os.getenv("UVICORN_HOST", DEFAULT_HOST)
        port = int(os.getenv("PORT", DEFAULT_PORT))
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host if host != "0.0.0.0" else "127.0.0.1", port))
            sock.close()
            
            if result == 0:
                logger.error(f"Port {port} is already in use")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Port availability check failed: {e}")
            return False
    
    async def _check_dependencies(self) -> bool:
        """Verify critical dependencies are installed"""
        critical_modules = [
            "fastapi", "uvicorn", "asyncpg", "jinja2", 
            "pandas", "httpx", "pydantic"
        ]
        
        missing_modules = []
        for module in critical_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            logger.error(f"Missing critical modules: {missing_modules}")
            return False
        
        return True
    
    async def _check_directories(self) -> bool:
        """Ensure required directories exist"""
        required_dirs = ["logs", "temp", "static/uploads"]
        
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        return True
    
    async def _check_configuration(self) -> bool:
        """Validate configuration files"""
        try:
            # Check if main.py can be imported
            import main
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    async def start_application(self, **kwargs) -> bool:
        """Start the FastAPI application with Uvicorn"""
        host = kwargs.get('host', os.getenv("UVICORN_HOST", DEFAULT_HOST))
        port = kwargs.get('port', int(os.getenv("PORT", DEFAULT_PORT)))
        workers = kwargs.get('workers', int(os.getenv("UVICORN_WORKERS", DEFAULT_WORKERS)))
        reload = kwargs.get('reload', kwargs.get('dev', False))
        log_level = kwargs.get('log_level', os.getenv("LOG_LEVEL", "info"))
        
        self.health_check_url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}/health"
        
        logger.info("🚀 Starting GST Intelligence Platform...")
        logger.info(f"📡 Server: {host}:{port}")
        logger.info(f"👥 Workers: {workers}")
        logger.info(f"🔄 Reload: {reload}")
        logger.info(f"📝 Log Level: {log_level}")
        
        try:
            # Configure Uvicorn
            config = uvicorn.Config(
                app="main:app",
                host=host,
                port=port,
                workers=workers if not reload else 1,
                reload=reload,
                log_level=log_level,
                access_log=True,
                use_colors=True,
                reload_dirs=[".", "templates", "static"] if reload else None,
                proxy_headers=True,
                forwarded_allow_ips="*"
            )
            
            server = uvicorn.Server(config)
            
            # Start server
            logger.info("✅ Application started successfully!")
            await server.serve()
            
        except Exception as e:
            logger.error(f"❌ Failed to start application: {e}")
            return False
        
        return True
    
    async def health_check(self, max_attempts: int = 30) -> bool:
        """Wait for application to be healthy"""
        if not self.health_check_url:
            return True
        
        logger.info("🔍 Waiting for application to be healthy...")
        
        async with httpx.AsyncClient() as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(
                        self.health_check_url,
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        logger.info("✅ Application is healthy!")
                        return True
                except Exception:
                    pass
                
                logger.info(f"⏳ Health check attempt {attempt + 1}/{max_attempts}...")
                await asyncio.sleep(2)
        
        logger.error("❌ Application failed to become healthy")
        return False
    
    async def shutdown(self):
        """Graceful shutdown procedure"""
        logger.info("🛑 Initiating graceful shutdown...")
        
        if self.app_process:
            try:
                self.app_process.terminate()
                self.app_process.wait(timeout=10)
                logger.info("✅ Application process terminated gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Forcing application shutdown...")
                self.app_process.kill()
                self.app_process.wait()
            except Exception as e:
                logger.error(f"❌ Error during shutdown: {e}")
        
        self.shutdown_event.set()
        logger.info("🏁 Shutdown complete")

def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="GST Intelligence Platform Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py                          # Start with defaults
  python start.py --dev                    # Development mode with reload
  python start.py --port 8080              # Custom port
  python start.py --workers 4              # Multiple workers
  python start.py --skip-checks            # Skip startup checks
  python start.py --log-level debug        # Debug logging
        """
    )
    
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host to bind (default: {DEFAULT_HOST})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to bind (default: {DEFAULT_PORT})"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of worker processes (default: {DEFAULT_WORKERS})"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Development mode with auto-reload"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on file changes"
    )
    
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip pre-startup validation checks"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level (default: info)"
    )
    
    parser.add_argument(
        "--health-check-only",
        action="store_true",
        help="Only perform health check and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="GST Intelligence Platform v1.0.0"
    )
    
    return parser

async def main():
    """Main application entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Print banner
    print("=" * 60)
    print("🏢 GST Intelligence Platform")
    print("📊 Complete Business Intelligence Solution")
    print("=" * 60)
    
    launcher = ApplicationLauncher()
    launcher.setup_signal_handlers()
    
    try:
        # Health check only mode
        if args.health_check_only:
            launcher.health_check_url = f"http://{args.host}:{args.port}/health"
            is_healthy = await launcher.health_check()
            sys.exit(0 if is_healthy else 1)
        
        # Pre-startup checks
        if not await launcher.pre_startup_checks(args.skip_checks):
            logger.error("❌ Startup checks failed. Use --skip-checks to bypass.")
            sys.exit(1)
        
        # Start application
        start_args = {
            'host': args.host,
            'port': args.port,
            'workers': args.workers,
            'reload': args.reload or args.dev,
            'dev': args.dev,
            'log_level': args.log_level
        }
        
        success = await launcher.start_application(**start_args)
        
        if not success:
            logger.error("❌ Failed to start application")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        sys.exit(1)
    finally:
        await launcher.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)
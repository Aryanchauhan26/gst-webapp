#!/usr/bin/env python3
"""
GST Intelligence Platform - Automated Debugging & Fix Script
This script performs comprehensive debugging and fixes common issues
"""

import os
import sys
import re
import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('debug_report.log'),
                        logging.StreamHandler(sys.stdout)
                    ])
logger = logging.getLogger(__name__)


class PlatformDebugger:
    """Comprehensive debugging and fixing tool for GST Intelligence Platform."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues_found = []
        self.fixes_applied = []
        self.warnings = []

    def run_full_debug(self) -> Dict:
        """Run complete debugging suite."""
        logger.info("🔍 Starting comprehensive debugging...")

        # Check project structure
        self.check_project_structure()

        # Check dependencies
        self.check_dependencies()

        # Check Python code
        self.check_python_code()

        # Check JavaScript/CSS
        self.check_frontend_code()

        # Check configuration
        self.check_configuration()

        # Check database setup
        self.check_database_setup()

        # Generate report
        return self.generate_report()

    def check_project_structure(self):
        """Check if all required files and directories exist."""
        logger.info("📁 Checking project structure...")

        required_files = [
            "main.py", "config.py", "requirements.txt", "static/css/base.css",
            "static/js/missing-globals.js", "templates/base.html"
        ]

        required_dirs = [
            "static", "static/css", "static/js", "static/icons", "templates"
        ]

        # Check directories
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                self.issues_found.append(f"Missing directory: {dir_path}")
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.fixes_applied.append(f"Created directory: {dir_path}")
                except Exception as e:
                    logger.error(f"Failed to create directory {dir_path}: {e}")

        # Check files
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.issues_found.append(f"Missing file: {file_path}")
                # Don't auto-create files, just report

        logger.info(f"✅ Project structure check complete")

    def check_dependencies(self):
        """Check and fix dependency issues."""
        logger.info("📦 Checking dependencies...")

        requirements_files = list(self.project_root.glob("requirements*.txt"))

        if not requirements_files:
            self.issues_found.append("No requirements.txt file found")
            return

        # Check for multiple requirements files
        if len(requirements_files) > 1:
            self.warnings.append(
                f"Multiple requirements files found: {[f.name for f in requirements_files]}"
            )

        # Analyze main requirements.txt
        main_req = self.project_root / "requirements.txt"
        if main_req.exists():
            self.analyze_requirements_file(main_req)

        # Check for pip-compile or poetry files
        if (self.project_root / "pyproject.toml").exists():
            logger.info("📝 Found pyproject.toml - Poetry project detected")

        logger.info("✅ Dependencies check complete")

    def analyze_requirements_file(self, req_file: Path):
        """Analyze requirements.txt for issues."""
        logger.info(f"🔍 Analyzing {req_file.name}...")

        try:
            with open(req_file, 'r') as f:
                lines = f.readlines()

            packages = {}
            issues = []
            duplicates = []

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Extract package name
                match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                if match:
                    package_name = match.group(1).lower()

                    if package_name in packages:
                        duplicates.append(
                            f"Line {line_num}: Duplicate package '{package_name}'"
                        )
                    else:
                        packages[package_name] = line_num

                # Check for problematic packages
                if "http-status==0.2.1" in line:
                    issues.append(
                        f"Line {line_num}: http-status==0.2.1 does not exist. Use http-status==1.0.0"
                    )

                # Check for invalid version specifiers
                if "==" in line and not re.match(
                        r'^[a-zA-Z0-9_-]+==[\d\w\.-]+', line):
                    issues.append(
                        f"Line {line_num}: Invalid version specifier in '{line}'"
                    )

            # Report findings
            if duplicates:
                self.issues_found.extend(duplicates)

            if issues:
                self.issues_found.extend(issues)

            if "http-status==0.2.1" in req_file.read_text():
                self.fix_http_status_version(req_file)

        except Exception as e:
            self.issues_found.append(f"Error reading {req_file}: {e}")

    def fix_http_status_version(self, req_file: Path):
        """Fix the http-status version issue."""
        try:
            content = req_file.read_text()
            fixed_content = content.replace("http-status==0.2.1",
                                            "http-status==1.0.0")

            if content != fixed_content:
                # Create backup
                backup_file = req_file.with_suffix('.txt.backup')
                req_file.rename(backup_file)

                # Write fixed content
                req_file.write_text(fixed_content)

                self.fixes_applied.append(
                    f"Fixed http-status version in {req_file.name}")
                logger.info(f"✅ Fixed http-status version in {req_file.name}")

        except Exception as e:
            logger.error(f"Failed to fix http-status version: {e}")

    def check_python_code(self):
        """Check Python code for common issues."""
        logger.info("🐍 Checking Python code...")

        python_files = list(self.project_root.glob("*.py"))

        for py_file in python_files:
            self.analyze_python_file(py_file)

        logger.info("✅ Python code check complete")

    def analyze_python_file(self, py_file: Path):
        """Analyze individual Python file."""
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for syntax errors
            try:
                compile(content, str(py_file), 'exec')
            except SyntaxError as e:
                self.issues_found.append(f"Syntax error in {py_file}: {e}")
                return

            # Check for common issues
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                # Check for incomplete imports
                if line.strip().startswith('from') and line.strip().endswith(
                        ','):
                    self.issues_found.append(
                        f"{py_file}:{line_num} - Incomplete import statement")

                # Check for TODO/FIXME comments
                if 'TODO' in line or 'FIXME' in line:
                    self.warnings.append(
                        f"{py_file}:{line_num} - {line.strip()}")

                # Check for print statements (should use logging)
                if re.search(r'\bprint\s*\(',
                             line) and 'logger' not in content:
                    self.warnings.append(
                        f"{py_file}:{line_num} - Using print() instead of logging"
                    )

            # Check for missing docstrings in functions/classes
            if 'def ' in content or 'class ' in content:
                if '"""' not in content and "'''" not in content:
                    self.warnings.append(f"{py_file} - Missing docstrings")

        except Exception as e:
            self.issues_found.append(f"Error analyzing {py_file}: {e}")

    def check_frontend_code(self):
        """Check JavaScript and CSS files."""
        logger.info("🌐 Checking frontend code...")

        # Check JavaScript files
        js_files = list(self.project_root.glob("static/js/*.js"))
        for js_file in js_files:
            self.analyze_js_file(js_file)

        # Check CSS files
        css_files = list(self.project_root.glob("static/css/*.css"))
        for css_file in css_files:
            self.analyze_css_file(css_file)

        # Check for missing files
        critical_js = self.project_root / "static/js/missing-globals.js"
        if not critical_js.exists():
            self.issues_found.append(
                "Missing critical file: static/js/missing-globals.js")

        logger.info("✅ Frontend code check complete")

    def analyze_js_file(self, js_file: Path):
        """Analyze JavaScript file."""
        try:
            content = js_file.read_text(encoding='utf-8')

            # Check for incomplete files (truncated)
            if content.endswith('ation'):  # Likely truncated
                self.issues_found.append(
                    f"{js_file.name} appears to be truncated")

            # Check for console.log statements
            if 'console.log(' in content:
                self.warnings.append(
                    f"{js_file.name} contains console.log statements")

            # Check for undefined variables (basic check)
            if 'undefined' in content:
                self.warnings.append(
                    f"{js_file.name} may have undefined variable issues")

            # Check for missing semicolons (basic check)
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.endswith(
                    (';', '{', '}', ')', ',')) and not line.startswith('//'):
                    if any(keyword in line for keyword in
                           ['var ', 'let ', 'const ', 'function ', 'return ']):
                        self.warnings.append(
                            f"{js_file.name}:{line_num} - Possible missing semicolon"
                        )
                        break  # Only report first occurrence

        except Exception as e:
            self.issues_found.append(f"Error analyzing {js_file}: {e}")

    def analyze_css_file(self, css_file: Path):
        """Analyze CSS file."""
        try:
            content = css_file.read_text(encoding='utf-8')

            # Check for unclosed braces
            open_braces = content.count('{')
            close_braces = content.count('}')

            if open_braces != close_braces:
                self.issues_found.append(
                    f"{css_file.name} has mismatched braces ({open_braces} open, {close_braces} close)"
                )

            # Check for invalid CSS properties (basic check)
            if 'undefined' in content:
                self.warnings.append(
                    f"{css_file.name} may contain invalid properties")

        except Exception as e:
            self.issues_found.append(f"Error analyzing {css_file}: {e}")

    def check_configuration(self):
        """Check configuration files."""
        logger.info("⚙️ Checking configuration...")

        config_file = self.project_root / "config.py"
        if config_file.exists():
            self.analyze_config_file(config_file)
        else:
            self.issues_found.append("Missing config.py file")

        # Check environment file
        env_file = self.project_root / ".env"
        if not env_file.exists():
            self.warnings.append(
                "No .env file found - using default configuration")

        logger.info("✅ Configuration check complete")

    def analyze_config_file(self, config_file: Path):
        """Analyze configuration file."""
        try:
            content = config_file.read_text()

            # Check for default/insecure values
            security_checks = [("SECRET_KEY", "your-super-secret-key"),
                               ("POSTGRES_DSN",
                                "postgresql://user:pass@localhost"),
                               ("RAPIDAPI_KEY", "your-rapidapi-key"),
                               ("DEBUG", "True")]

            for setting, insecure_value in security_checks:
                if insecure_value in content:
                    self.issues_found.append(
                        f"Insecure default value for {setting} in config.py")

        except Exception as e:
            self.issues_found.append(f"Error analyzing config.py: {e}")

    def check_database_setup(self):
        """Check database configuration and setup."""
        logger.info("🗄️ Checking database setup...")

        try:
            # Try to import database modules
            import asyncpg
            logger.info("✅ asyncpg available")
        except ImportError:
            self.issues_found.append(
                "Missing asyncpg dependency for PostgreSQL")

        try:
            import redis
            logger.info("✅ redis available")
        except ImportError:
            self.warnings.append(
                "Redis not available - caching will use memory")

        logger.info("✅ Database check complete")

    def generate_report(self) -> Dict:
        """Generate comprehensive debugging report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "issues_found": len(self.issues_found),
            "fixes_applied": len(self.fixes_applied),
            "warnings": len(self.warnings),
            "status": "PASS" if len(self.issues_found) == 0 else "FAIL",
            "details": {
                "issues": self.issues_found,
                "fixes": self.fixes_applied,
                "warnings": self.warnings
            }
        }

        # Save report to file
        report_file = self.project_root / "debug_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        self.print_summary(report)

        return report

    def print_summary(self, report: Dict):
        """Print debugging summary."""
        print("\n" + "=" * 60)
        print("🔍 GST INTELLIGENCE PLATFORM DEBUG REPORT")
        print("=" * 60)
        print(f"📅 Timestamp: {report['timestamp']}")
        print(
            f"📊 Status: {'✅ PASS' if report['status'] == 'PASS' else '❌ FAIL'}"
        )
        print(f"🐛 Issues Found: {report['issues_found']}")
        print(f"🔧 Fixes Applied: {report['fixes_applied']}")
        print(f"⚠️ Warnings: {report['warnings']}")

        if report['details']['issues']:
            print("\n🐛 CRITICAL ISSUES:")
            for i, issue in enumerate(report['details']['issues'], 1):
                print(f"  {i}. {issue}")

        if report['details']['fixes']:
            print("\n🔧 FIXES APPLIED:")
            for i, fix in enumerate(report['details']['fixes'], 1):
                print(f"  {i}. {fix}")

        if report['details']['warnings']:
            print("\n⚠️ WARNINGS:")
            for i, warning in enumerate(report['details']['warnings'], 1):
                print(f"  {i}. {warning}")

        print("\n💡 NEXT STEPS:")
        if report['issues_found'] > 0:
            print("  1. Review and fix the critical issues listed above")
            print("  2. Test the application after fixes")
            print("  3. Run this script again to verify fixes")
        else:
            print("  1. Address any warnings if needed")
            print("  2. Run application tests")
            print("  3. Deploy with confidence!")

        print(f"\n📝 Full report saved to: debug_report.json")
        print("=" * 60 + "\n")


def main():
    """Main debugging function."""
    print("🚀 GST Intelligence Platform Debugger")
    print("=====================================\n")

    # Get project root from command line or use current directory
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."

    # Create debugger instance
    debugger = PlatformDebugger(project_root)

    # Run full debugging suite
    report = debugger.run_full_debug()

    # Exit with appropriate code
    sys.exit(0 if report['status'] == 'PASS' else 1)


if __name__ == "__main__":
    main()

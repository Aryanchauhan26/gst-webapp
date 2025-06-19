#!/usr/bin/env python3
"""
User Preferences Management System for GST Intelligence Platform
Handles user settings, themes, notifications, and customizations
"""

import os
import sys
import asyncio
import asyncpg
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
)

class Theme(Enum):
    """Available themes"""
    DARK = "dark"
    LIGHT = "light"
    AUTO = "auto"
    HIGH_CONTRAST = "high_contrast"

class NotificationLevel(Enum):
    """Notification levels"""
    ALL = "all"
    IMPORTANT = "important"
    CRITICAL = "critical"
    NONE = "none"

class DashboardLayout(Enum):
    """Dashboard layout options"""
    COMPACT = "compact"
    STANDARD = "standard"
    DETAILED = "detailed"
    CUSTOM = "custom"

@dataclass
class UserPreferences:
    """User preferences data structure"""
    # UI Preferences
    theme: str = Theme.DARK.value
    language: str = "en"
    timezone: str = "Asia/Kolkata"
    dashboard_layout: str = DashboardLayout.STANDARD.value
    items_per_page: int = 25
    
    # Notification Preferences
    email_notifications: bool = True
    push_notifications: bool = True
    notification_level: str = NotificationLevel.IMPORTANT.value
    daily_digest: bool = True
    weekly_report: bool = True
    
    # Search Preferences
    default_search_filters: Dict = None
    save_search_history: bool = True
    auto_suggestions: bool = True
    search_result_format: str = "detailed"  # compact, standard, detailed
    
    # Analytics Preferences
    default_date_range: str = "30d"  # 7d, 30d, 90d, 1y
    show_trends: bool = True
    show_comparisons: bool = True
    export_format: str = "pdf"  # pdf, excel, csv
    
    # Privacy & Security
    data_retention_days: int = 365
    share_analytics: bool = False
    two_factor_auth: bool = False
    session_timeout_minutes: int = 30
    
    # Custom Settings
    favorite_companies: List[str] = None
    custom_alerts: List[Dict] = None
    quick_actions: List[str] = None
    custom_dashboard_widgets: List[Dict] = None
    
    # API Preferences
    api_rate_limit_alerts: bool = True
    preferred_api_source: str = "rapidapi"
    cache_results: bool = True
    
    def __post_init__(self):
        """Initialize default values for mutable fields"""
        if self.default_search_filters is None:
            self.default_search_filters = {}
        if self.favorite_companies is None:
            self.favorite_companies = []
        if self.custom_alerts is None:
            self.custom_alerts = []
        if self.quick_actions is None:
            self.quick_actions = ["search", "history", "analytics", "export"]
        if self.custom_dashboard_widgets is None:
            self.custom_dashboard_widgets = [
                {"type": "recent_searches", "position": 1, "size": "medium"},
                {"type": "compliance_chart", "position": 2, "size": "large"},
                {"type": "quick_stats", "position": 3, "size": "small"}
            ]

class UserPreferencesManager:
    """Manages user preferences in the database"""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.pool = None
    
    async def connect(self):
        """Initialize database connection pool"""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.database_url,
                    min_size=1,
                    max_size=5,
                    command_timeout=30
                )
                logger.info("✅ Database pool created for preferences")
            except Exception as e:
                logger.error(f"❌ Database connection failed: {e}")
                raise
    
    async def ensure_preferences_table(self):
        """Ensure user preferences table exists"""
        await self.connect()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    mobile VARCHAR(10) PRIMARY KEY,
                    preferences JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    
                    FOREIGN KEY (mobile) REFERENCES users(mobile) ON DELETE CASCADE,
                    
                    -- Indexes for better performance
                    INDEX idx_user_prefs_mobile (mobile),
                    INDEX idx_user_prefs_updated (updated_at)
                );
            """)
            
            # Create trigger to update timestamp
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_preferences_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    NEW.version = OLD.version + 1;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS trigger_update_preferences_timestamp ON user_preferences;
                CREATE TRIGGER trigger_update_preferences_timestamp
                    BEFORE UPDATE ON user_preferences
                    FOR EACH ROW
                    EXECUTE FUNCTION update_preferences_timestamp();
            """)
            
            logger.info("✅ User preferences table ensured")
    
    async def get_user_preferences(self, mobile: str) -> UserPreferences:
        """Get user preferences, return defaults if not found"""
        await self.connect()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT preferences FROM user_preferences WHERE mobile = $1",
                mobile
            )
            
            if row and row['preferences']:
                try:
                    prefs_dict = dict(row['preferences'])
                    # Merge with defaults to handle new fields
                    default_prefs = asdict(UserPreferences())
                    default_prefs.update(prefs_dict)
                    return UserPreferences(**default_prefs)
                except Exception as e:
                    logger.warning(f"Error parsing preferences for {mobile}: {e}")
                    return UserPreferences()
            else:
                # Return defaults for new user
                return UserPreferences()
    
    async def save_user_preferences(self, mobile: str, preferences: UserPreferences) -> bool:
        """Save user preferences to database"""
        await self.connect()
        async with self.pool.acquire() as conn:
            try:
                prefs_dict = asdict(preferences)
                
                # Upsert preferences
                await conn.execute("""
                    INSERT INTO user_preferences (mobile, preferences) 
                    VALUES ($1, $2)
                    ON CONFLICT (mobile) 
                    DO UPDATE SET preferences = $2
                """, mobile, json.dumps(prefs_dict))
                
                logger.info(f"✅ Preferences saved for user {mobile}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Error saving preferences for {mobile}: {e}")
                return False
    
    async def update_preference(self, mobile: str, key: str, value: Any) -> bool:
        """Update a single preference value"""
        try:
            preferences = await self.get_user_preferences(mobile)
            
            # Use setattr to update the preference
            if hasattr(preferences, key):
                setattr(preferences, key, value)
                return await self.save_user_preferences(mobile, preferences)
            else:
                logger.error(f"Invalid preference key: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating preference {key} for {mobile}: {e}")
            return False
    
    async def get_preference(self, mobile: str, key: str, default: Any = None) -> Any:
        """Get a single preference value"""
        try:
            preferences = await self.get_user_preferences(mobile)
            return getattr(preferences, key, default)
        except Exception as e:
            logger.error(f"Error getting preference {key} for {mobile}: {e}")
            return default
    
    async def reset_preferences(self, mobile: str) -> bool:
        """Reset user preferences to defaults"""
        try:
            default_preferences = UserPreferences()
            return await self.save_user_preferences(mobile, default_preferences)
        except Exception as e:
            logger.error(f"Error resetting preferences for {mobile}: {e}")
            return False
    
    async def export_preferences(self, mobile: str) -> Optional[Dict]:
        """Export user preferences as dictionary"""
        try:
            preferences = await self.get_user_preferences(mobile)
            return asdict(preferences)
        except Exception as e:
            logger.error(f"Error exporting preferences for {mobile}: {e}")
            return None
    
    async def import_preferences(self, mobile: str, preferences_dict: Dict) -> bool:
        """Import preferences from dictionary"""
        try:
            # Validate and create preferences object
            preferences = UserPreferences(**preferences_dict)
            return await self.save_user_preferences(mobile, preferences)
        except Exception as e:
            logger.error(f"Error importing preferences for {mobile}: {e}")
            return False
    
    async def get_users_with_preference(self, key: str, value: Any) -> List[str]:
        """Get list of users with specific preference value"""
        await self.connect()
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch("""
                    SELECT mobile FROM user_preferences 
                    WHERE preferences->$1 = $2
                """, key, json.dumps(value))
                
                return [row['mobile'] for row in rows]
                
            except Exception as e:
                logger.error(f"Error querying users with preference {key}={value}: {e}")
                return []
    
    async def get_preference_statistics(self) -> Dict:
        """Get statistics about user preferences"""
        await self.connect()
        async with self.pool.acquire() as conn:
            try:
                # Total users with preferences
                total_users = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_preferences"
                )
                
                # Theme distribution
                theme_stats = await conn.fetch("""
                    SELECT 
                        preferences->>'theme' as theme,
                        COUNT(*) as count
                    FROM user_preferences 
                    WHERE preferences->>'theme' IS NOT NULL
                    GROUP BY preferences->>'theme'
                """)
                
                # Dashboard layout distribution
                layout_stats = await conn.fetch("""
                    SELECT 
                        preferences->>'dashboard_layout' as layout,
                        COUNT(*) as count
                    FROM user_preferences 
                    WHERE preferences->>'dashboard_layout' IS NOT NULL
                    GROUP BY preferences->>'dashboard_layout'
                """)
                
                # Notification preferences
                notification_stats = await conn.fetch("""
                    SELECT 
                        preferences->>'notification_level' as level,
                        COUNT(*) as count
                    FROM user_preferences 
                    WHERE preferences->>'notification_level' IS NOT NULL
                    GROUP BY preferences->>'notification_level'
                """)
                
                return {
                    "total_users": total_users,
                    "themes": {row['theme']: row['count'] for row in theme_stats},
                    "layouts": {row['layout']: row['count'] for row in layout_stats},
                    "notifications": {row['level']: row['count'] for row in notification_stats},
                    "generated_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting preference statistics: {e}")
                return {"error": str(e)}

class PreferencesValidator:
    """Validates user preference values"""
    
    @staticmethod
    def validate_theme(theme: str) -> bool:
        """Validate theme value"""
        return theme in [t.value for t in Theme]
    
    @staticmethod
    def validate_notification_level(level: str) -> bool:
        """Validate notification level"""
        return level in [n.value for n in NotificationLevel]
    
    @staticmethod
    def validate_dashboard_layout(layout: str) -> bool:
        """Validate dashboard layout"""
        return layout in [l.value for l in DashboardLayout]
    
    @staticmethod
    def validate_items_per_page(items: int) -> bool:
        """Validate items per page"""
        return 10 <= items <= 100
    
    @staticmethod
    def validate_session_timeout(minutes: int) -> bool:
        """Validate session timeout"""
        return 5 <= minutes <= 480  # 5 minutes to 8 hours
    
    @staticmethod
    def validate_data_retention(days: int) -> bool:
        """Validate data retention period"""
        return 30 <= days <= 2555  # 30 days to 7 years
    
    @classmethod
    def validate_preferences(cls, preferences: UserPreferences) -> List[str]:
        """Validate all preferences and return list of errors"""
        errors = []
        
        if not cls.validate_theme(preferences.theme):
            errors.append(f"Invalid theme: {preferences.theme}")
        
        if not cls.validate_notification_level(preferences.notification_level):
            errors.append(f"Invalid notification level: {preferences.notification_level}")
        
        if not cls.validate_dashboard_layout(preferences.dashboard_layout):
            errors.append(f"Invalid dashboard layout: {preferences.dashboard_layout}")
        
        if not cls.validate_items_per_page(preferences.items_per_page):
            errors.append("Items per page must be between 10 and 100")
        
        if not cls.validate_session_timeout(preferences.session_timeout_minutes):
            errors.append("Session timeout must be between 5 and 480 minutes")
        
        if not cls.validate_data_retention(preferences.data_retention_days):
            errors.append("Data retention must be between 30 and 2555 days")
        
        return errors

class PreferencesAPI:
    """API interface for preference management"""
    
    def __init__(self, manager: UserPreferencesManager):
        self.manager = manager
        self.validator = PreferencesValidator()
    
    async def get_preferences_json(self, mobile: str) -> Dict:
        """Get preferences as JSON-serializable dictionary"""
        try:
            preferences = await self.manager.get_user_preferences(mobile)
            return {
                "success": True,
                "preferences": asdict(preferences),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def update_preferences_json(self, mobile: str, preferences_data: Dict) -> Dict:
        """Update preferences from JSON data"""
        try:
            # Create preferences object
            preferences = UserPreferences(**preferences_data)
            
            # Validate preferences
            errors = self.validator.validate_preferences(preferences)
            if errors:
                return {
                    "success": False,
                    "errors": errors,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Save preferences
            success = await self.manager.save_user_preferences(mobile, preferences)
            
            return {
                "success": success,
                "message": "Preferences updated successfully" if success else "Failed to update preferences",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_preference_options(self) -> Dict:
        """Get available preference options"""
        return {
            "themes": [{"value": t.value, "label": t.value.replace("_", " ").title()} for t in Theme],
            "notification_levels": [{"value": n.value, "label": n.value.replace("_", " ").title()} for n in NotificationLevel],
            "dashboard_layouts": [{"value": l.value, "label": l.value.replace("_", " ").title()} for l in DashboardLayout],
            "languages": [
                {"value": "en", "label": "English"},
                {"value": "hi", "label": "हिन्दी"},
                {"value": "mr", "label": "मराठी"},
                {"value": "gu", "label": "ગુજરાતી"},
                {"value": "ta", "label": "தமிழ்"},
                {"value": "te", "label": "తెలుగు"}
            ],
            "timezones": [
                {"value": "Asia/Kolkata", "label": "India Standard Time"},
                {"value": "Asia/Dubai", "label": "UAE Time"},
                {"value": "UTC", "label": "UTC"},
                {"value": "America/New_York", "label": "Eastern Time"},
                {"value": "Europe/London", "label": "GMT"}
            ],
            "date_ranges": [
                {"value": "7d", "label": "Last 7 Days"},
                {"value": "30d", "label": "Last 30 Days"},
                {"value": "90d", "label": "Last 3 Months"},
                {"value": "1y", "label": "Last Year"}
            ],
            "export_formats": [
                {"value": "pdf", "label": "PDF Document"},
                {"value": "excel", "label": "Excel Spreadsheet"},
                {"value": "csv", "label": "CSV File"}
            ]
        }

# Global instances
preferences_manager = UserPreferencesManager()
preferences_api = PreferencesAPI(preferences_manager)

async def initialize_preferences_system():
    """Initialize the preferences system"""
    try:
        logger.info("🔧 Initializing user preferences system...")
        
        # Ensure database table exists
        await preferences_manager.ensure_preferences_table()
        
        # Test the system
        test_mobile = "0000000000"
        default_prefs = await preferences_manager.get_user_preferences(test_mobile)
        logger.info(f"✅ Default preferences loaded: {default_prefs.theme}")
        
        logger.info("✅ User preferences system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize preferences system: {e}")
        return False

async def migrate_existing_preferences():
    """Migrate existing user preferences to new format"""
    logger.info("🔄 Checking for preference migrations...")
    
    try:
        await preferences_manager.connect()
        async with preferences_manager.pool.acquire() as conn:
            # Check if old preference format exists
            old_prefs = await conn.fetch("""
                SELECT mobile, preferences 
                FROM user_preferences 
                WHERE preferences IS NOT NULL
            """)
            
            migrated_count = 0
            
            for row in old_prefs:
                mobile = row['mobile']
                old_data = dict(row['preferences'])
                
                try:
                    # Create new preferences object with defaults
                    new_prefs = UserPreferences()
                    
                    # Map old fields to new structure
                    field_mapping = {
                        'theme': 'theme',
                        'language': 'language',
                        'notifications': 'email_notifications',
                        'items_per_page': 'items_per_page'
                    }
                    
                    # Update with existing values
                    for old_key, new_key in field_mapping.items():
                        if old_key in old_data:
                            setattr(new_prefs, new_key, old_data[old_key])
                    
                    # Save migrated preferences
                    await preferences_manager.save_user_preferences(mobile, new_prefs)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate preferences for {mobile}: {e}")
            
            if migrated_count > 0:
                logger.info(f"✅ Migrated preferences for {migrated_count} users")
            else:
                logger.info("ℹ️  No preferences to migrate")
                
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")

async def main():
    """Main function for testing and setup"""
    print("🔧 GST Platform - User Preferences Management")
    print("=" * 60)
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        print("""
Usage:
    python create_user_prefs.py [options]

Options:
    --init          Initialize preferences system
    --migrate       Migrate existing preferences
    --test          Run test operations
    --stats         Show preference statistics
    --help          Show this help

Examples:
    python create_user_prefs.py --init
    python create_user_prefs.py --test
    python create_user_prefs.py --stats
        """)
        return
    
    try:
        if '--init' in args:
            success = await initialize_preferences_system()
            if success:
                print("✅ Preferences system initialized successfully!")
            else:
                print("❌ Failed to initialize preferences system")
                sys.exit(1)
        
        if '--migrate' in args:
            await migrate_existing_preferences()
            print("✅ Migration completed")
        
        if '--test' in args:
            print("🧪 Running preference tests...")
            
            # Test user
            test_mobile = "9999999999"
            
            # Test getting default preferences
            prefs = await preferences_manager.get_user_preferences(test_mobile)
            print(f"✅ Default preferences: Theme={prefs.theme}, Layout={prefs.dashboard_layout}")
            
            # Test updating a preference
            success = await preferences_manager.update_preference(test_mobile, "theme", "light")
            print(f"✅ Theme update: {'Success' if success else 'Failed'}")
            
            # Test getting updated preferences
            updated_prefs = await preferences_manager.get_user_preferences(test_mobile)
            print(f"✅ Updated theme: {updated_prefs.theme}")
            
            # Test validation
            invalid_prefs = UserPreferences(theme="invalid_theme")
            errors = PreferencesValidator.validate_preferences(invalid_prefs)
            print(f"✅ Validation test: {len(errors)} errors found (expected)")
            
            print("✅ All tests completed!")
        
        if '--stats' in args:
            print("📊 Getting preference statistics...")
            stats = await preferences_manager.get_preference_statistics()
            print(f"📈 Statistics:")
            print(f"   Total users: {stats.get('total_users', 0)}")
            print(f"   Themes: {stats.get('themes', {})}")
            print(f"   Layouts: {stats.get('layouts', {})}")
            print(f"   Notifications: {stats.get('notifications', {})}")
        
    except Exception as e:
        logger.error(f"💥 Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
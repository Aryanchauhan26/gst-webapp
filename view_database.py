#!/usr/bin/env python3
"""
Database viewer script for GST Intelligence Platform
Run this to view your database contents
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import sys

def format_table(data, headers):
    """Format data as a nice table"""
    if not data:
        return "No data found"
    
    # Calculate column widths
    widths = [len(str(header)) for header in headers]
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell) if cell is not None else 'NULL'))
    
    # Create format string
    format_str = "| " + " | ".join(f"{{:<{w}}}" for w in widths) + " |"
    separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    
    # Build table
    lines = [separator]
    lines.append(format_str.format(*headers))
    lines.append(separator)
    
    for row in data:
        formatted_row = []
        for cell in row:
            if cell is None:
                formatted_row.append('NULL')
            elif isinstance(cell, str) and len(cell) > 50:
                formatted_row.append(cell[:47] + '...')
            else:
                formatted_row.append(str(cell))
        lines.append(format_str.format(*formatted_row))
    
    lines.append(separator)
    return "\n".join(lines)

def view_database():
    """View all database contents"""
    db_path = Path("database") / "gst_platform.db"
    
    if not db_path.exists():
        print("❌ Database not found at:", db_path)
        print("Make sure you're running this from the project root directory")
        return
    
    print("📊 GST Intelligence Platform Database Contents")
    print("=" * 60)
    print(f"📁 Database file: {db_path}")
    print(f"📅 Last modified: {datetime.fromtimestamp(db_path.stat().st_mtime)}")
    print("=" * 60)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get database info
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"\n📋 Tables found: {len(tables)}")
            for table in tables:
                print(f"   - {table[0]}")
            
            print("\n" + "=" * 60)
            
            # View Users table
            print("\n👥 USERS TABLE")
            print("-" * 30)
            cursor.execute("SELECT mobile, created_at, last_login FROM users ORDER BY created_at DESC")
            users_data = cursor.fetchall()
            users_headers = ["Mobile", "Created At", "Last Login"]
            print(format_table(users_data, users_headers))
            print(f"Total users: {len(users_data)}")
            
            # View Sessions table
            print("\n🔐 ACTIVE SESSIONS")
            print("-" * 30)
            cursor.execute("""
                SELECT session_token, mobile, created_at, expires_at 
                FROM sessions 
                WHERE expires_at > datetime('now')
                ORDER BY created_at DESC
            """)
            sessions_data = cursor.fetchall()
            sessions_headers = ["Session Token", "Mobile", "Created At", "Expires At"]
            if sessions_data:
                # Truncate session tokens for display
                display_sessions = []
                for row in sessions_data:
                    token = row[0][:12] + "..." if len(row[0]) > 12 else row[0]
                    display_sessions.append((token, row[1], row[2], row[3]))
                print(format_table(display_sessions, sessions_headers))
            else:
                print("No active sessions found")
            print(f"Active sessions: {len(sessions_data)}")
            
            # View Search History
            print("\n🔍 SEARCH HISTORY (Last 10)")
            print("-" * 30)
            cursor.execute("""
                SELECT mobile, gstin, company_name, searched_at, compliance_score 
                FROM search_history 
                ORDER BY searched_at DESC 
                LIMIT 10
            """)
            history_data = cursor.fetchall()
            history_headers = ["Mobile", "GSTIN", "Company Name", "Searched At", "Compliance Score"]
            print(format_table(history_data, history_headers))
            
            # Get total history count
            cursor.execute("SELECT COUNT(*) FROM search_history")
            total_history = cursor.fetchone()[0]
            print(f"Total search history entries: {total_history}")
            
            # Database statistics
            print("\n📈 DATABASE STATISTICS")
            print("-" * 30)
            
            # Most searched companies
            cursor.execute("""
                SELECT company_name, COUNT(*) as search_count
                FROM search_history 
                GROUP BY company_name 
                ORDER BY search_count DESC 
                LIMIT 5
            """)
            popular_companies = cursor.fetchall()
            if popular_companies:
                print("\nMost searched companies:")
                for company, count in popular_companies:
                    print(f"   {count:2d}x - {company}")
            
            # Average compliance scores
            cursor.execute("""
                SELECT AVG(compliance_score) as avg_score, 
                       MIN(compliance_score) as min_score, 
                       MAX(compliance_score) as max_score
                FROM search_history 
                WHERE compliance_score IS NOT NULL
            """)
            score_stats = cursor.fetchone()
            if score_stats[0] is not None:
                print(f"\nCompliance Score Statistics:")
                print(f"   Average: {score_stats[0]:.1f}%")
                print(f"   Minimum: {score_stats[1]:.1f}%")
                print(f"   Maximum: {score_stats[2]:.1f}%")
            
            # Recent activity
            cursor.execute("""
                SELECT DATE(searched_at) as date, COUNT(*) as searches
                FROM search_history 
                WHERE searched_at >= date('now', '-7 days')
                GROUP BY DATE(searched_at)
                ORDER BY date DESC
            """)
            recent_activity = cursor.fetchall()
            if recent_activity:
                print(f"\nSearches in last 7 days:")
                for date, count in recent_activity:
                    print(f"   {date}: {count} searches")
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def export_data():
    """Export database data to JSON"""
    db_path = Path("database") / "gst_platform.db"
    
    if not db_path.exists():
        print("❌ Database not found")
        return
    
    export_data = {}
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Export users (excluding sensitive data)
            cursor.execute("SELECT mobile, created_at, last_login FROM users")
            export_data['users'] = [dict(row) for row in cursor.fetchall()]
            
            # Export search history
            cursor.execute("SELECT * FROM search_history")
            export_data['search_history'] = [dict(row) for row in cursor.fetchall()]
            
            # Export sessions count only (not the actual tokens)
            cursor.execute("SELECT COUNT(*) as active_sessions FROM sessions WHERE expires_at > datetime('now')")
            export_data['active_sessions_count'] = cursor.fetchone()[0]
        
        # Save to file
        export_file = Path("database_export.json")
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"✅ Data exported to: {export_file}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--export":
            export_data()
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python view_database.py        - View database contents")
            print("  python view_database.py --export - Export data to JSON")
            print("  python view_database.py --help   - Show this help")
        else:
            print("Unknown option. Use --help for usage information.")
    else:
        view_database()

if __name__ == "__main__":
    main()
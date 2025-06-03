#!/usr/bin/env python3
"""
Simple web-based database viewer
Run this and go to http://localhost:8001 to view your database
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from pathlib import Path
import uvicorn

app = FastAPI(title="Database Viewer")

def get_db_data():
    """Get all database data"""
    db_path = Path("database") / "gst_platform.db"
    
    if not db_path.exists():
        return {"error": "Database not found"}
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get users (hide sensitive data)
            cursor.execute("SELECT mobile, created_at, last_login FROM users ORDER BY created_at DESC")
            users = [dict(row) for row in cursor.fetchall()]
            
            # Get search history
            cursor.execute("""
                SELECT mobile, gstin, company_name, searched_at, compliance_score 
                FROM search_history 
                ORDER BY searched_at DESC 
                LIMIT 50
            """)
            history = [dict(row) for row in cursor.fetchall()]
            
            # Get active sessions count
            cursor.execute("SELECT COUNT(*) as count FROM sessions WHERE expires_at > datetime('now')")
            active_sessions = cursor.fetchone()['count']
            
            return {
                "users": users,
                "history": history,
                "active_sessions": active_sessions,
                "total_users": len(users),
                "total_history": len(history)
            }
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def view_database(request: Request):
    """Database viewer page"""
    data = get_db_data()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GST Platform Database Viewer</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
            h2 {{ color: #007bff; margin-top: 30px; }}
            .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
            .stat-box {{ background: #007bff; color: white; padding: 15px; border-radius: 5px; text-align: center; flex: 1; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .error {{ color: red; background: #ffe6e6; padding: 15px; border-radius: 5px; }}
            .mobile {{ font-family: monospace; }}
            .gstin {{ font-family: monospace; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🗄️ GST Intelligence Platform Database</h1>
            
            {"<div class='error'>❌ " + data['error'] + "</div>" if 'error' in data else ""}
            
            {f'''
            <div class="stats">
                <div class="stat-box">
                    <div style="font-size: 24px; font-weight: bold;">{data['total_users']}</div>
                    <div>Total Users</div>
                </div>
                <div class="stat-box">
                    <div style="font-size: 24px; font-weight: bold;">{data['total_history']}</div>
                    <div>Search Records</div>
                </div>
                <div class="stat-box">
                    <div style="font-size: 24px; font-weight: bold;">{data['active_sessions']}</div>
                    <div>Active Sessions</div>
                </div>
            </div>
            
            <h2>👥 Users</h2>
            <table>
                <tr>
                    <th>Mobile</th>
                    <th>Created At</th>
                    <th>Last Login</th>
                </tr>
                {"".join(f'''
                <tr>
                    <td class="mobile">{user['mobile']}</td>
                    <td>{user['created_at'] or 'Never'}</td>
                    <td>{user['last_login'] or 'Never'}</td>
                </tr>
                ''' for user in data['users'])}
            </table>
            
            <h2>🔍 Recent Search History</h2>
            <table>
                <tr>
                    <th>Mobile</th>
                    <th>GSTIN</th>
                    <th>Company</th>
                    <th>Searched At</th>
                    <th>Compliance Score</th>
                </tr>
                {"".join(f'''
                <tr>
                    <td class="mobile">{search['mobile']}</td>
                    <td class="gstin">{search['gstin']}</td>
                    <td>{search['company_name']}</td>
                    <td>{search['searched_at']}</td>
                    <td>{search['compliance_score'] or 'N/A'}</td>
                </tr>
                ''' for search in data['history'])}
            </table>
            ''' if 'error' not in data else ''}
            
            <p style="margin-top: 40px; color: #666; text-align: center;">
                🔄 Refresh the page to update data | 
                <a href="javascript:location.reload()">Refresh Now</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    return html_content

if __name__ == "__main__":
    print("🌐 Starting Database Viewer at http://localhost:8001")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="localhost", port=8001)
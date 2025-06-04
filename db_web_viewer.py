#!/usr/bin/env python3
"""
Simple web-based database viewer
Run this and go to http://localhost:8001 to view your database
"""

import sqlite3
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

DB_PATH = "database/gst_platform.db"

def get_users():
    if not os.path.exists(DB_PATH):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT mobile, created_at, last_login FROM users").fetchall()

def get_history():
    if not os.path.exists(DB_PATH):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT mobile, gstin, company_name, searched_at, compliance_score FROM search_history ORDER BY searched_at DESC LIMIT 50"
        ).fetchall()

@app.get("/", response_class=HTMLResponse)
def index():
    users = get_users()
    history = get_history()
    html = "<h2>Users</h2><table border=1><tr><th>Mobile</th><th>Created At</th><th>Last Login</th></tr>"
    for u in users:
        html += f"<tr><td>{u[0]}</td><td>{u[1]}</td><td>{u[2]}</td></tr>"
    html += "</table><h2>Recent Search History</h2><table border=1><tr><th>Mobile</th><th>GSTIN</th><th>Company</th><th>Searched At</th><th>Score</th></tr>"
    for h in history:
        html += f"<tr><td>{h[0]}</td><td>{h[1]}</td><td>{h[2]}</td><td>{h[3]}</td><td>{h[4]}</td></tr>"
    html += '</table><p style="margin-top: 40px; color: #666; text-align: center;">🔄 Refresh the page to update data | <a href="javascript:location.reload()">Refresh Now</a></p>'
    return html

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
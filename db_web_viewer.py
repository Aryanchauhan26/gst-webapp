#!/usr/bin/env python3
"""
Simple web-based database viewer for PostgreSQL/Neon
Run this and go to http://localhost:8001 to view your database
"""

import asyncpg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio

POSTGRES_DSN = "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

app = FastAPI()

async def get_users():
    conn = await asyncpg.connect(dsn=POSTGRES_DSN)
    rows = await conn.fetch("SELECT mobile, created_at, last_login FROM users")
    await conn.close()
    return rows

async def get_history():
    conn = await asyncpg.connect(dsn=POSTGRES_DSN)
    rows = await conn.fetch(
        "SELECT mobile, gstin, company_name, searched_at, compliance_score FROM search_history ORDER BY searched_at DESC LIMIT 50"
    )
    await conn.close()
    return rows

@app.get("/", response_class=HTMLResponse)
async def index():
    users = await get_users()
    history = await get_history()
    html = "<h2>Users</h2><table border=1><tr><th>Mobile</th><th>Created At</th><th>Last Login</th></tr>"
    for u in users:
        html += f"<tr><td>{u['mobile']}</td><td>{u['created_at']}</td><td>{u['last_login']}</td></tr>"
    html += "</table><h2>Recent Search History</h2><table border=1><tr><th>Mobile</th><th>GSTIN</th><th>Company</th><th>Searched At</th><th>Score</th></tr>"
    for h in history:
        html += f"<tr><td>{h['mobile']}</td><td>{h['gstin']}</td><td>{h['company_name']}</td><td>{h['searched_at']}</td><td>{h['compliance_score']}</td></tr>"
    html += '</table><p style="margin-top: 40px; color: #666; text-align: center;">🔄 Refresh the page to update data | <a href="javascript:location.reload()">Refresh Now</a></p>'
    return html

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
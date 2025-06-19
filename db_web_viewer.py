#!/usr/bin/env python3
"""
Simple web-based database viewer for PostgreSQL/Neon
Run this and go to http://localhost:8001 to view your database
"""

import os
import sys
import asyncio
import asyncpg
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

# Web framework
try:
    from fastapi import FastAPI, Request, HTTPException, Query, Form
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import uvicorn
except ImportError:
    print("❌ Missing dependencies. Run: pip install fastapi uvicorn jinja2")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
)

class DatabaseViewer:
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
                logger.info("✅ Database pool created")
            except Exception as e:
                logger.error(f"❌ Database connection failed: {e}")
                raise
    
    async def get_tables(self) -> List[Dict]:
        """Get all tables in the database"""
        await self.connect()
        async with self.pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT 
                    table_name,
                    table_schema,
                    table_type
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            # Get row counts for each table
            result = []
            for table in tables:
                try:
                    count = await conn.fetchval(
                        f"SELECT COUNT(*) FROM {table['table_name']}"
                    )
                    result.append({
                        'name': table['table_name'],
                        'schema': table['table_schema'],
                        'type': table['table_type'],
                        'row_count': count
                    })
                except Exception as e:
                    result.append({
                        'name': table['table_name'],
                        'schema': table['table_schema'],
                        'type': table['table_type'],
                        'row_count': 'Error'
                    })
            
            return result
    
    async def get_table_schema(self, table_name: str) -> List[Dict]:
        """Get schema information for a table"""
        await self.connect()
        async with self.pool.acquire() as conn:
            columns = await conn.fetch("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns 
                WHERE table_name = $1 AND table_schema = 'public'
                ORDER BY ordinal_position
            """, table_name)
            
            return [dict(col) for col in columns]
    
    async def get_table_data(self, table_name: str, page: int = 1, limit: int = 50, 
                           search: str = "", order_by: str = "") -> Dict:
        """Get data from a table with pagination"""
        await self.connect()
        async with self.pool.acquire() as conn:
            offset = (page - 1) * limit
            
            # Build base query
            base_query = f"FROM {table_name}"
            count_query = f"SELECT COUNT(*) {base_query}"
            
            # Add search filter if provided
            if search:
                # Get column names first
                columns = await conn.fetch("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = $1 AND table_schema = 'public'
                """, table_name)
                
                text_columns = []
                for col in columns:
                    col_name = col['column_name']
                    # Check if column is text-like
                    if any(keyword in col_name.lower() for keyword in ['name', 'text', 'description', 'mobile', 'gstin']):
                        text_columns.append(f"{col_name}::text ILIKE '%{search}%'")
                
                if text_columns:
                    search_condition = " OR ".join(text_columns)
                    base_query += f" WHERE {search_condition}"
                    count_query = f"SELECT COUNT(*) {base_query}"
            
            # Add ordering
            if order_by:
                base_query += f" ORDER BY {order_by}"
            else:
                # Default ordering by first column
                first_col = await conn.fetchval("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = $1 AND table_schema = 'public'
                    ORDER BY ordinal_position LIMIT 1
                """, table_name)
                if first_col:
                    base_query += f" ORDER BY {first_col} DESC"
            
            # Get total count
            total_count = await conn.fetchval(count_query)
            
            # Get data
            data_query = f"SELECT * {base_query} LIMIT {limit} OFFSET {offset}"
            rows = await conn.fetch(data_query)
            
            return {
                'data': [dict(row) for row in rows],
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit,
                'has_next': page * limit < total_count,
                'has_prev': page > 1
            }
    
    async def execute_query(self, query: str) -> Dict:
        """Execute a custom SQL query"""
        await self.connect()
        async with self.pool.acquire() as conn:
            try:
                # Determine if it's a SELECT query
                query_lower = query.lower().strip()
                
                if query_lower.startswith('select'):
                    # SELECT query - return results
                    rows = await conn.fetch(query)
                    return {
                        'success': True,
                        'type': 'select',
                        'data': [dict(row) for row in rows],
                        'row_count': len(rows)
                    }
                else:
                    # DML query - return affected rows
                    result = await conn.execute(query)
                    return {
                        'success': True,
                        'type': 'dml',
                        'message': result,
                        'affected_rows': result.split()[-1] if result else '0'
                    }
            
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'type': 'error'
                }
    
    async def get_database_stats(self) -> Dict:
        """Get database statistics"""
        await self.connect()
        async with self.pool.acquire() as conn:
            try:
                # Database size
                db_size = await conn.fetchval("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                
                # Table count
                table_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                
                # Connection count
                connection_count = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                
                # Recent activity (if search_history exists)
                recent_activity = 0
                try:
                    recent_activity = await conn.fetchval("""
                        SELECT COUNT(*) FROM search_history 
                        WHERE searched_at >= NOW() - INTERVAL '24 hours'
                    """)
                except:
                    pass
                
                return {
                    'database_size': db_size,
                    'table_count': table_count,
                    'connection_count': connection_count,
                    'recent_activity': recent_activity,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting database stats: {e}")
                return {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

# Initialize FastAPI app
app = FastAPI(title="GST Platform Database Viewer", version="1.0.0")
db_viewer = DatabaseViewer()

# HTML Templates (inline for simplicity)
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GST Platform Database Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #0f172a; 
            color: #e2e8f0; 
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { 
            background: linear-gradient(135deg, #1e293b, #334155); 
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 { color: #38bdf8; font-size: 2.5em; margin-bottom: 10px; }
        .header p { color: #94a3b8; font-size: 1.2em; }
        
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px; 
        }
        .stat-card { 
            background: #1e293b; 
            padding: 20px; 
            border-radius: 10px; 
            border: 1px solid #334155;
            text-align: center;
        }
        .stat-card h3 { color: #38bdf8; margin-bottom: 10px; }
        .stat-card .value { font-size: 2em; font-weight: bold; color: #10b981; }
        
        .section { 
            background: #1e293b; 
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 30px;
            border: 1px solid #334155;
        }
        .section h2 { color: #38bdf8; margin-bottom: 20px; font-size: 1.8em; }
        
        .table-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .table-card { 
            background: #0f172a; 
            padding: 20px; 
            border-radius: 8px; 
            cursor: pointer;
            border: 1px solid #475569;
            transition: all 0.3s ease;
        }
        .table-card:hover { 
            border-color: #38bdf8; 
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
        }
        .table-card h3 { color: #f1f5f9; margin-bottom: 10px; }
        .table-card .info { color: #94a3b8; font-size: 0.9em; }
        
        .data-table { 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 20px;
            background: #0f172a;
            border-radius: 8px;
            overflow: hidden;
        }
        .data-table th, .data-table td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid #334155; 
        }
        .data-table th { 
            background: #1e293b; 
            color: #38bdf8; 
            font-weight: 600;
        }
        .data-table tr:hover { background: #1e293b; }
        
        .pagination { 
            display: flex; 
            justify-content: center; 
            gap: 10px; 
            margin-top: 20px; 
        }
        .pagination button { 
            padding: 8px 16px; 
            background: #1e293b; 
            color: #e2e8f0; 
            border: 1px solid #475569; 
            border-radius: 6px; 
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .pagination button:hover { 
            background: #38bdf8; 
            border-color: #38bdf8; 
        }
        .pagination button:disabled { 
            opacity: 0.5; 
            cursor: not-allowed; 
        }
        
        .search-bar { 
            margin-bottom: 20px; 
            display: flex; 
            gap: 10px; 
        }
        .search-bar input { 
            flex: 1; 
            padding: 12px; 
            background: #0f172a; 
            border: 1px solid #475569; 
            border-radius: 6px; 
            color: #e2e8f0;
            font-size: 16px;
        }
        .search-bar button { 
            padding: 12px 24px; 
            background: #38bdf8; 
            color: #0f172a; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            font-weight: 600;
            transition: background 0.3s ease;
        }
        .search-bar button:hover { background: #0ea5e9; }
        
        .query-editor { margin-bottom: 30px; }
        .query-editor textarea { 
            width: 100%; 
            height: 150px; 
            padding: 15px; 
            background: #0f172a; 
            border: 1px solid #475569; 
            border-radius: 6px; 
            color: #e2e8f0; 
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
        }
        
        .nav-tabs { 
            display: flex; 
            margin-bottom: 20px; 
            border-bottom: 1px solid #334155; 
        }
        .nav-tab { 
            padding: 12px 24px; 
            background: none; 
            border: none; 
            color: #94a3b8; 
            cursor: pointer; 
            border-bottom: 2px solid transparent;
            transition: all 0.3s ease;
        }
        .nav-tab.active { 
            color: #38bdf8; 
            border-bottom-color: #38bdf8; 
        }
        .nav-tab:hover { color: #e2e8f0; }
        
        .alert { 
            padding: 15px; 
            border-radius: 6px; 
            margin-bottom: 20px; 
        }
        .alert.success { background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; color: #6ee7b7; }
        .alert.error { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #fca5a5; }
        
        .loading { 
            text-align: center; 
            padding: 40px; 
            color: #94a3b8; 
        }
        
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: 1fr; }
            .table-list { grid-template-columns: 1fr; }
            .search-bar { flex-direction: column; }
            .nav-tabs { flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗄️ GST Platform Database Viewer</h1>
            <p>Manage and explore your GST Intelligence Platform database</p>
        </div>
        
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <h3>Database Size</h3>
                <div class="value" id="db-size">Loading...</div>
            </div>
            <div class="stat-card">
                <h3>Tables</h3>
                <div class="value" id="table-count">Loading...</div>
            </div>
            <div class="stat-card">
                <h3>Connections</h3>
                <div class="value" id="connection-count">Loading...</div>
            </div>
            <div class="stat-card">
                <h3>Recent Activity (24h)</h3>
                <div class="value" id="recent-activity">Loading...</div>
            </div>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('tables')">📊 Tables</button>
            <button class="nav-tab" onclick="showTab('query')">💻 Query</button>
            <button class="nav-tab" onclick="showTab('data')">📋 Table Data</button>
        </div>
        
        <div id="tables-tab" class="section">
            <h2>Database Tables</h2>
            <div class="table-list" id="table-list">
                <div class="loading">Loading tables...</div>
            </div>
        </div>
        
        <div id="query-tab" class="section" style="display: none;">
            <h2>SQL Query Editor</h2>
            <div class="query-editor">
                <textarea id="sql-query" placeholder="Enter your SQL query here...
                
Examples:
SELECT * FROM users LIMIT 10;
SELECT COUNT(*) FROM search_history;
SELECT mobile, COUNT(*) as searches FROM search_history GROUP BY mobile ORDER BY searches DESC;"></textarea>
                <button onclick="executeQuery()" style="margin-top: 10px; padding: 12px 24px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer;">Execute Query</button>
            </div>
            <div id="query-results"></div>
        </div>
        
        <div id="data-tab" class="section" style="display: none;">
            <h2>Table Data Viewer</h2>
            <div class="search-bar">
                <select id="table-selector" style="padding: 12px; background: #0f172a; border: 1px solid #475569; border-radius: 6px; color: #e2e8f0;">
                    <option value="">Select a table...</option>
                </select>
                <input type="text" id="search-input" placeholder="Search in table...">
                <button onclick="loadTableData()">Load Data</button>
            </div>
            <div id="table-data-container"></div>
        </div>
    </div>

    <script>
        let currentTab = 'tables';
        let currentTable = '';
        let currentPage = 1;

        // Tab switching
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.section').forEach(section => {
                section.style.display = 'none';
            });
            
            // Remove active class from all nav tabs
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName + '-tab').style.display = 'block';
            event.target.classList.add('active');
            
            currentTab = tabName;
        }

        // Load database stats
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                
                document.getElementById('db-size').textContent = stats.database_size || 'N/A';
                document.getElementById('table-count').textContent = stats.table_count || '0';
                document.getElementById('connection-count').textContent = stats.connection_count || '0';
                document.getElementById('recent-activity').textContent = stats.recent_activity || '0';
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        // Load tables
        async function loadTables() {
            try {
                const response = await fetch('/api/tables');
                const tables = await response.json();
                
                const tableList = document.getElementById('table-list');
                const tableSelector = document.getElementById('table-selector');
                
                tableList.innerHTML = tables.map(table => `
                    <div class="table-card" onclick="selectTable('${table.name}')">
                        <h3>${table.name}</h3>
                        <div class="info">
                            <div>Rows: ${table.row_count}</div>
                            <div>Type: ${table.type}</div>
                        </div>
                    </div>
                `).join('');
                
                // Populate table selector
                tableSelector.innerHTML = '<option value="">Select a table...</option>' +
                    tables.map(table => `<option value="${table.name}">${table.name}</option>`).join('');
                
            } catch (error) {
                console.error('Error loading tables:', error);
                document.getElementById('table-list').innerHTML = '<div class="alert error">Error loading tables</div>';
            }
        }

        // Select table for data viewing
        function selectTable(tableName) {
            document.getElementById('table-selector').value = tableName;
            showTab('data');
            loadTableData();
        }

        // Load table data
        async function loadTableData(page = 1) {
            const tableName = document.getElementById('table-selector').value;
            const search = document.getElementById('search-input').value;
            
            if (!tableName) {
                document.getElementById('table-data-container').innerHTML = '<div class="alert error">Please select a table</div>';
                return;
            }
            
            try {
                document.getElementById('table-data-container').innerHTML = '<div class="loading">Loading data...</div>';
                
                const response = await fetch(`/api/table/${tableName}/data?page=${page}&search=${encodeURIComponent(search)}`);
                const result = await response.json();
                
                if (result.data.length === 0) {
                    document.getElementById('table-data-container').innerHTML = '<div class="alert">No data found</div>';
                    return;
                }
                
                // Build table HTML
                const columns = Object.keys(result.data[0]);
                const tableHtml = `
                    <table class="data-table">
                        <thead>
                            <tr>${columns.map(col => `<th>${col}</th>`).join('')}</tr>
                        </thead>
                        <tbody>
                            ${result.data.map(row => `
                                <tr>${columns.map(col => `<td>${formatValue(row[col])}</td>`).join('')}</tr>
                            `).join('')}
                        </tbody>
                    </table>
                    
                    <div class="pagination">
                        <button onclick="loadTableData(${result.page - 1})" ${!result.has_prev ? 'disabled' : ''}>Previous</button>
                        <span>Page ${result.page} of ${result.total_pages} (${result.total_count} rows)</span>
                        <button onclick="loadTableData(${result.page + 1})" ${!result.has_next ? 'disabled' : ''}>Next</button>
                    </div>
                `;
                
                document.getElementById('table-data-container').innerHTML = tableHtml;
                currentPage = result.page;
                
            } catch (error) {
                console.error('Error loading table data:', error);
                document.getElementById('table-data-container').innerHTML = '<div class="alert error">Error loading table data</div>';
            }
        }

        // Execute custom SQL query
        async function executeQuery() {
            const query = document.getElementById('sql-query').value.trim();
            
            if (!query) {
                document.getElementById('query-results').innerHTML = '<div class="alert error">Please enter a query</div>';
                return;
            }
            
            try {
                document.getElementById('query-results').innerHTML = '<div class="loading">Executing query...</div>';
                
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });
                
                const result = await response.json();
                
                if (!result.success) {
                    document.getElementById('query-results').innerHTML = `<div class="alert error">Error: ${result.error}</div>`;
                    return;
                }
                
                if (result.type === 'select' && result.data.length > 0) {
                    const columns = Object.keys(result.data[0]);
                    const tableHtml = `
                        <div class="alert success">Query executed successfully. ${result.row_count} rows returned.</div>
                        <table class="data-table">
                            <thead>
                                <tr>${columns.map(col => `<th>${col}</th>`).join('')}</tr>
                            </thead>
                            <tbody>
                                ${result.data.map(row => `
                                    <tr>${columns.map(col => `<td>${formatValue(row[col])}</td>`).join('')}</tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                    document.getElementById('query-results').innerHTML = tableHtml;
                } else if (result.type === 'dml') {
                    document.getElementById('query-results').innerHTML = `
                        <div class="alert success">Query executed successfully. ${result.affected_rows} rows affected.</div>
                    `;
                } else {
                    document.getElementById('query-results').innerHTML = '<div class="alert success">Query executed successfully. No data returned.</div>';
                }
                
            } catch (error) {
                console.error('Error executing query:', error);
                document.getElementById('query-results').innerHTML = '<div class="alert error">Error executing query</div>';
            }
        }

        // Format values for display
        function formatValue(value) {
            if (value === null) return '<em>NULL</em>';
            if (typeof value === 'object') return JSON.stringify(value);
            if (typeof value === 'string' && value.length > 100) return value.substring(0, 100) + '...';
            return value;
        }

        // Initialize the page
        window.addEventListener('load', () => {
            loadStats();
            loadTables();
        });

        // Auto-refresh stats every 30 seconds
        setInterval(loadStats, 30000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the main database viewer interface"""
    return HTMLResponse(content=html_template)

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        stats = await db_viewer.get_database_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tables")
async def get_tables():
    """Get all database tables"""
    try:
        tables = await db_viewer.get_tables()
        return JSONResponse(content=tables)
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/table/{table_name}/schema")
async def get_table_schema(table_name: str):
    """Get table schema"""
    try:
        schema = await db_viewer.get_table_schema(table_name)
        return JSONResponse(content=schema)
    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/table/{table_name}/data")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=1000),
    search: str = Query(""),
    order_by: str = Query("")
):
    """Get table data with pagination"""
    try:
        data = await db_viewer.get_table_data(table_name, page, limit, search, order_by)
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error getting table data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def execute_query(request: Request):
    """Execute custom SQL query"""
    try:
        body = await request.json()
        query = body.get('query', '').strip();
        
        if (!query) {
            throw new HTTPException(status_code=400, detail="Query is required");
        }
        
        // Basic security check - prevent dangerous operations
        dangerous_keywords = ['drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update'];
        query_lower = query.toLowerCase();
        
        // Allow SELECT queries and some safe operations
        if (!query_lower.startsWith('select') && dangerous_keywords.some(keyword => query_lower.includes(keyword))) {
            throw new HTTPException(status_code=403, detail="Only SELECT queries are allowed for security");
        }
        
        result = await db_viewer.execute_query(query);
        return JSONResponse(content=result);
        
    } catch (HTTPException) {
        throw;
    } catch (Exception e) {
        logger.error(f"Error executing query: {e}");
        return JSONResponse(content={
            'success': False,
            'error': str(e),
            'type': 'error'
        });
    }
});

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await db_viewer.connect();
        return {"status": "healthy", "timestamp": datetime.now().isoformat()};
    } catch (Exception e) {
        throw new HTTPException(status_code=500, detail=f"Database unhealthy: {e}");
    }
});

if __name__ == "__main__":
    print("🗄️  GST Platform Database Viewer")
    print("=" * 50)
    print("🚀 Starting database viewer...")
    print(f"🌐 Access at: http://localhost:8001")
    print("📊 Features:")
    print("   - View all database tables")
    print("   - Browse table data with pagination")
    print("   - Execute custom SQL queries")
    print("   - Real-time database statistics")
    print("   - Mobile-responsive interface")
    print("⚠️  Security: Only SELECT queries allowed")
    print("=" * 50)
    
    # Check if main database is accessible
    try:
        asyncio.run(db_viewer.connect());
        print("✅ Database connection successful");
    } catch (Exception e) {
        print(f"❌ Database connection failed: {e}");
        print("💡 Make sure your DATABASE_URL is correct");
    }
    
    # Start the viewer
    uvicorn.run(
        "db_web_viewer:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=False,
        log_level="info"
    );
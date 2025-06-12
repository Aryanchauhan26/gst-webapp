# debug_compliance_scores.py
import asyncio
import asyncpg

async def check_compliance_scores():
    try:
        conn = await asyncpg.connect("postgresql://neondb_owner:npg_i3m7wqMeHXaW@ep-fragrant-cell-a10j16o4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")
        
        # Check search_history table structure
        print("🔍 Checking search_history table structure...")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'search_history'
            ORDER BY ordinal_position
        """)
        
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Check actual data
        print("\n📊 Checking compliance score data...")
        scores = await conn.fetch("""
            SELECT id, gstin, company_name, compliance_score, searched_at
            FROM search_history 
            ORDER BY searched_at DESC 
            LIMIT 10
        """)
        
        for score in scores:
            print(f"  - {score['company_name']}: {score['compliance_score']}% (GSTIN: {score['gstin']})")
        
        # Check for NULL scores
        null_count = await conn.fetchval("SELECT COUNT(*) FROM search_history WHERE compliance_score IS NULL")
        total_count = await conn.fetchval("SELECT COUNT(*) FROM search_history")
        
        print(f"\n📈 Summary: {null_count}/{total_count} records have NULL compliance scores")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_compliance_scores())
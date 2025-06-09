async def seed_achievements():
    achievements_data = [
        {
            'id': 'first_search',
            'title': 'First Timer',
            'description': 'Complete your first GSTIN search',
            'icon': 'fas fa-baby',
            'xp_reward': 100,
            'requirement_type': 'search_count',
            'requirement_value': 1,
            'rarity': 'common'
        },
        {
            'id': 'search_master',
            'title': 'Search Master',
            'description': 'Perform 100 GSTIN searches',
            'icon': 'fas fa-search',
            'xp_reward': 500,
            'requirement_type': 'search_count',
            'requirement_value': 100,
            'rarity': 'rare'
        },
        {
            'id': 'streak_warrior',
            'title': 'Streak Warrior',
            'description': 'Maintain a 7-day search streak',
            'icon': 'fas fa-fire',
            'xp_reward': 300,
            'requirement_type': 'streak',
            'requirement_value': 7,
            'rarity': 'epic'
        },
        {
            'id': 'compliance_expert',
            'title': 'Compliance Expert',
            'description': 'Reach Level 10',
            'icon': 'fas fa-crown',
            'xp_reward': 1000,
            'requirement_type': 'level',
            'requirement_value': 10,
            'rarity': 'legendary'
        }
    ]
    await db.connect()
    async with db.pool.acquire() as conn:
        for achievement in achievements_data:
            await conn.execute("""
                INSERT INTO achievements (id, title, description, icon, xp_reward, 
                                        requirement_type, requirement_value, rarity)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
            """, *achievement.values())
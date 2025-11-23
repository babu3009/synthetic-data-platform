"""Check if entity rules are saved in database."""
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models import WizardEntity
from sqlalchemy import select


async def check_rules():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(WizardEntity))
        entities = result.scalars().all()
        
        print(f"Total entities in database: {len(entities)}\n")
        
        for entity in entities:
            print(f"Entity: {entity.name}")
            print(f"  ID: {entity.id}")
            print(f"  Version: {entity.version}")
            print(f"  Rules Format: {entity.rules_format}")
            print(f"  Has Rules Config: {bool(entity.rules_config)}")
            if entity.rules_config:
                preview = entity.rules_config[:200] if len(entity.rules_config) > 200 else entity.rules_config
                print(f"  Rules Preview: {preview}...")
            print()


if __name__ == "__main__":
    asyncio.run(check_rules())

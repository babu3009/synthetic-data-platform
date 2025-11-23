"""Clean up duplicate wizard entities, keeping only the latest version of each unique name per project."""
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.models import WizardEntity
from sqlalchemy import select, func, and_
from sqlalchemy.orm import aliased


async def cleanup_duplicates():
    async with AsyncSessionLocal() as db:
        # Get all entities
        result = await db.execute(select(WizardEntity).order_by(WizardEntity.project_id, WizardEntity.name, WizardEntity.version.desc()))
        all_entities = result.scalars().all()
        
        print(f"Total entities in database: {len(all_entities)}\n")
        
        # Group by project_id + name, keep highest version
        seen = {}  # (project_id, name) -> entity to keep
        to_delete = []
        
        for entity in all_entities:
            key = (str(entity.project_id), entity.name.lower().strip())
            
            if key not in seen:
                # First occurrence (highest version due to ordering)
                seen[key] = entity
                print(f"KEEP: {entity.name} (v{entity.version}, ID: {entity.id})")
            else:
                # Duplicate - mark for deletion
                to_delete.append(entity)
                print(f"DELETE: {entity.name} (v{entity.version}, ID: {entity.id})")
        
        print(f"\n\nSummary:")
        print(f"  Total entities: {len(all_entities)}")
        print(f"  Unique entities to keep: {len(seen)}")
        print(f"  Duplicates to delete: {len(to_delete)}")
        
        if to_delete:
            confirm = input(f"\n\nDelete {len(to_delete)} duplicate entities? (yes/no): ")
            if confirm.lower() == 'yes':
                for entity in to_delete:
                    await db.delete(entity)
                await db.commit()
                print(f"\n✅ Deleted {len(to_delete)} duplicate entities!")
            else:
                print("\n❌ Cancelled - no entities deleted")
        else:
            print("\n✅ No duplicates found!")


if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())

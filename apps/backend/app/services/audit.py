from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.db.models import AuditEvent

async def audit(db: AsyncSession, action: str, actor_user_id: Optional[str] = None, payload: Optional[dict[str, Any]] = None) -> None:
    stmt = (
        insert(AuditEvent.__table__)
        .values(
            actor_user_id=actor_user_id,
            actor=action,  # keep legacy actor column populated with action for compatibility
            action=action,
            payload_json=payload or {},
        )
    )
    await db.execute(stmt)
    await db.commit()

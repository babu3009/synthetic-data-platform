from typing import Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.db.models import AuditEvent
from uuid import UUID

async def audit(
    db: AsyncSession,
    action: str,
    actor_user_id: Optional[Union[str, UUID]] = None,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    # Normalize UUID types for drivers/dialects that expect Python UUID objects
    if isinstance(actor_user_id, str):
        try:
            actor_user_id = UUID(actor_user_id)
        except Exception:
            # leave as-is if invalid; DB may accept null or raise appropriately
            pass
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

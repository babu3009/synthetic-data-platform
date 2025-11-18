"""WebSocket endpoint for real-time project request list updates."""
from typing import Dict, Set
from uuid import UUID
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Request, RequestStatus
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()

# Track active WebSocket connections per project
_project_connections: Dict[str, Set[WebSocket]] = {}


@router.websocket("/ws/projects/{project_id}/requests")
async def websocket_project_requests(
    websocket: WebSocket,
    project_id: str,
):
    """
    WebSocket endpoint for real-time updates of all requests in a project.
    
    More efficient than per-request WebSockets - single connection streams
    updates for all active requests in a project.
    """
    await websocket.accept()
    
    # Register this connection
    if project_id not in _project_connections:
        _project_connections[project_id] = set()
    _project_connections[project_id].add(websocket)
    
    logger.info(f"WebSocket connected for project {project_id} requests")
    
    try:
        async with AsyncSessionLocal() as db:
            # Track last known state to send only changes
            last_states: Dict[str, dict] = {}
            
            while True:
                try:
                    # Fetch all active requests (pending/running) for this project
                    # Note: status column is VARCHAR in DB, not enum, so we use string comparison
                    stmt = select(Request).where(
                        Request.project_id == UUID(project_id)
                    ).where(
                        Request.status.in_(['pending', 'running'])
                    )
                    result = await db.execute(stmt)
                    active_requests = result.scalars().all()
                    
                    # Check for status changes and send updates
                    for req in active_requests:
                        current_state = {
                            "id": str(req.id),
                            "alias": req.alias,
                            "status": req.status,
                            "error_message": req.error_message,
                            "started_at": req.started_at.isoformat() if req.started_at is not None else None,
                            "finished_at": req.finished_at.isoformat() if req.finished_at is not None else None,
                        }
                        
                        # Send update if state changed or new request
                        if str(req.id) not in last_states or last_states[str(req.id)] != current_state:
                            await websocket.send_json({
                                "type": "status",
                                "request": current_state
                            })
                            last_states[str(req.id)] = current_state
                    
                    # Check for requests that completed (no longer in active list)
                    active_ids = {str(req.id) for req in active_requests}
                    completed_ids = set(last_states.keys()) - active_ids
                    
                    if completed_ids:
                        # Fetch final state of completed requests
                        stmt = select(Request).where(
                            Request.id.in_([UUID(rid) for rid in completed_ids])
                        )
                        result = await db.execute(stmt)
                        completed_requests = result.scalars().all()
                        
                        for req in completed_requests:
                            final_state = {
                                "id": str(req.id),
                                "alias": req.alias,
                                "status": req.status,
                                "error_message": req.error_message,
                                "started_at": req.started_at.isoformat() if req.started_at is not None else None,
                                "finished_at": req.finished_at.isoformat() if req.finished_at is not None else None,
                            }
                            await websocket.send_json({
                                "type": "status",
                                "request": final_state
                            })
                            # Remove from tracking
                            last_states.pop(str(req.id), None)
                    
                    # If no active requests, send heartbeat
                    if not active_requests:
                        await websocket.send_json({
                            "type": "heartbeat",
                            "active_count": 0
                        })
                    
                    # Wait before next poll (3 seconds for project-level updates)
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error fetching project requests: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for project {project_id} requests")
    except Exception as e:
        logger.error(f"WebSocket error for project {project_id}: {e}", exc_info=True)
    finally:
        # Clean up connection
        if project_id in _project_connections:
            _project_connections[project_id].discard(websocket)
            if not _project_connections[project_id]:
                del _project_connections[project_id]


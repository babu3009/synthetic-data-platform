"""WebSocket endpoint for real-time request status updates."""
from typing import Dict, Set
from uuid import UUID
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter()

# Track active WebSocket connections per request
_active_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast_request_update(request_id: str, data: dict):
    """Broadcast update to all WebSocket clients watching a specific request."""
    if request_id in _active_connections:
        dead_connections = set()
        for ws in _active_connections[request_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead_connections.add(ws)
        
        # Clean up dead connections
        _active_connections[request_id] -= dead_connections
        if not _active_connections[request_id]:
            del _active_connections[request_id]


@router.websocket("/ws/requests/{request_id}")
async def websocket_request_status(
    websocket: WebSocket,
    request_id: str,
):
    """
    WebSocket endpoint for real-time request status updates.
    
    Clients connect and receive periodic updates about request status and artifacts.
    Connection stays open until request is completed/failed/cancelled or client disconnects.
    """
    await websocket.accept()
    
    # Register this connection
    if request_id not in _active_connections:
        _active_connections[request_id] = set()
    _active_connections[request_id].add(websocket)
    
    logger.info(f"WebSocket connected for request {request_id}")
    
    try:
        # Get DB session from dependency injection context
        # Note: We need to manage our own session for WebSocket lifecycle
        from app.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            while True:
                # Fetch current request status
                try:
                    req = await crud.request.get(db=db, id=UUID(request_id))
                    if not req:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Request not found"
                        })
                        break
                    
                    # Send status update
                    # Include progress from params_json if available
                    progress = None
                    if req.params_json and isinstance(req.params_json, dict):
                        progress = req.params_json.get("progress")
                    
                    status_data = {
                        "type": "status",
                        "request_id": str(req.id),
                        "alias": req.alias,
                        "status": req.status,
                        "error_message": req.error_message,
                        "progress": progress,  # Include progress for real-time updates
                        "created_at": req.created_at.isoformat() if req.created_at else None,
                        "started_at": req.started_at.isoformat() if req.started_at else None,
                        "finished_at": req.finished_at.isoformat() if req.finished_at else None,
                    }
                    await websocket.send_json(status_data)
                    
                    # If request is terminal, send artifacts and close
                    if req.status in ["completed", "failed", "cancelled"]:
                        artifacts = await crud.artifact.get_by_request(db=db, request_id=UUID(request_id))
                        artifacts_data = {
                            "type": "artifacts",
                            "artifacts": [
                                {
                                    "id": str(a.id),
                                    "format": a.format,
                                    "size_bytes": a.size_bytes,
                                    "storage_uri": a.storage_uri,
                                    "created_at": a.created_at.isoformat() if a.created_at else None,
                                }
                                for a in artifacts
                            ]
                        }
                        await websocket.send_json(artifacts_data)
                        
                        # Send completion message
                        await websocket.send_json({
                            "type": "complete",
                            "status": req.status
                        })
                        break
                    
                    # Wait before next poll (2 seconds)
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error fetching request status: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for request {request_id}")
    except Exception as e:
        logger.error(f"WebSocket error for request {request_id}: {e}", exc_info=True)
    finally:
        # Clean up connection
        if request_id in _active_connections:
            _active_connections[request_id].discard(websocket)
            if not _active_connections[request_id]:
                del _active_connections[request_id]

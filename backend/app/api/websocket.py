from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
from ..api.auth import get_current_user
from ..models import User
from ..database import get_db
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}  # user_id -> list of websockets
        self.active_device_connections: Dict[str, WebSocket] = {} # device_id (str/UUID) -> websocket

    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect a WebSocket for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
    
    async def connect_device(self, websocket: WebSocket, device_id: str):
        """Connect a WebSocket for a device."""
        await websocket.accept()
        # Ensure only one connection per device? Or kick old one?
        # For now, overwrite
        self.active_device_connections[device_id] = websocket
        if device_id:
             print(f"Device {device_id[:8]}... connected via WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Disconnect a WebSocket."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
    def disconnect_device(self, device_id: str):
        """Disconnect a device."""
        if device_id in self.active_device_connections:
            del self.active_device_connections[device_id]
            print(f"Device {device_id[:8]}... disconnected")

    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to all connections of a user."""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect(conn, user_id)
                
    async def send_to_device(self, message: dict, device_id: str) -> bool:
        """Send message to a specific device. Returns True if sent."""
        # Ensure device_id is treated as string if passed as int (though mostly string now)
        did = str(device_id) 
        if did in self.active_device_connections:
            try:
                await self.active_device_connections[did].send_json(message)
                return True
            except:
                self.disconnect_device(did)
                return False
        return False
    
    async def broadcast_to_user(self, message: dict, user_id: int):
        """Broadcast message to all connections of a user."""
        await self.send_personal_message(message, user_id)


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for User (Parent) real-time updates."""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # Echo back or handle message
                await websocket.send_json({"type": "ack", "message": "received"})
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.websocket("/ws/device/{device_id}")
async def websocket_device_endpoint(
    websocket: WebSocket, 
    device_id: str, 
    api_key: str = None,
    db: Session = Depends(get_db)  # Depends is tricky in WS, but FastAPI supports it in path
):
    """WebSocket endpoint for Device Agent."""
    # Authenticate
    # Note: Dependencies in WebSocket are supported but `get_db` usually yields. 
    # We might need to manually handle session if Depends doesn't work well here for connection phase.
    # But FastAPI allows `websocket: WebSocket` + Depends.
    
    logger.info(f"WS Attempt: device_id={device_id}, api_key={api_key}")
    
    # 1. Verify Device
    from ..models import Device
    
    # Debug checks removed, standard flow restored
    device = db.query(Device).filter(
        Device.device_id == device_id,
        Device.api_key == api_key
    ).first()
    
    if not device:
        logger.warning(f"WS Auth Failed: Invalid credentials for {device_id}")
        await websocket.close(code=4001, reason="Unauthorized")
        return

    logger.info(f"WS Auth Success: {device.name}")

    # 2. Accept & Connect
    await manager.connect_device(websocket, device_id)
    
    try:
        while True:
            # Wait for messages (Ping/Heartbeat from agent)
            data = await websocket.receive_text()
            # We can basically ignore agent messages for now, or handle Ping
            # Agent says "I'm alive"
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except:
                pass
    except WebSocketDisconnect:
        manager.disconnect_device(device_id)
    except Exception as e:
        print(f"WS Device Error: {e}")
        manager.disconnect_device(device_id)


async def notify_user(user_id: int, message: dict):
    """Helper function to notify a user via WebSocket."""
    await manager.broadcast_to_user(message, user_id)

async def send_command_to_device(device_id: str, command: str, payload: dict = None):
    """Helper to send command to device."""
    # Accept int or str, convert to str to match manager key
    return await manager.send_to_device({"type": "command", "cmd": command, "payload": payload or {}}, str(device_id))



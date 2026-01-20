"""WebSocket message types and parsing."""
from dataclasses import dataclass
from typing import Dict, Any, Optional
import json

@dataclass
class WebSocketMessage:
    """Incoming WebSocket message."""
    type: str
    cmd: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_json(cls, data: str) -> 'WebSocketMessage':
        try:
            obj = json.loads(data)
            return cls(
                type=obj.get('type', ''),
                cmd=obj.get('cmd'),
                payload=obj.get('payload')
            )
        except json.JSONDecodeError:
            return cls(type='error', payload={'error': 'Invalid JSON'})

@dataclass  
class WebSocketCommand:
    """Parsed command logic for handlers."""
    command: str
    payload: Optional[Dict[str, Any]] = None

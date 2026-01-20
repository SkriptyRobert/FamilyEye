"""WebSocket module for real-time backend communication."""
from .client import WebSocketClient
from .messages import WebSocketCommand, WebSocketMessage

__all__ = ['WebSocketClient', 'WebSocketCommand', 'WebSocketMessage']

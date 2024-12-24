from datetime import datetime
from typing import Optional
from ..core.event import EventManager
from .message_manager import MessageManager

class Room:
    def __init__(self, user_id: str):
        self.id = f"room_{datetime.now().timestamp()}"
        self.user_id = user_id
        self.sid: Optional[str] = None
        self.event_manager = EventManager()
        self.message_manager = MessageManager()
        self.autogpt = None  # 明示的にNoneで初期化 
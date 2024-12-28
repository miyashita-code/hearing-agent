# /autogpt_modules/communication/room.py
from datetime import datetime
from typing import Optional
from ..core.event import EventManager
from .message_manager import MessageManager
from fastapi import WebSocket # 追加

class Room:
    def __init__(self, user_id: str):
        self.id = f"room_{user_id}_{datetime.now().timestamp()}"
        self.user_id = user_id
        self.event_manager = EventManager()
        self.message_manager = MessageManager()
        self.autogpt: Optional['AutoGPT'] = None
        self.last_active = datetime.now()
        self.websocket: Optional[WebSocket] = None # 追加
        self.new_message_flag = False

    def update_activity(self):
        self.last_active = datetime.now()
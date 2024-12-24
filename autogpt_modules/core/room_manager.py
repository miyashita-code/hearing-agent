from datetime import datetime, timedelta
from typing import Dict, Optional
from .message_manager import MessageManager
from .event_manager import EventManager
from .auto_gpt import AutoGPT

class Room:
    def __init__(self, user_id: str):
        self.id = f"room_{user_id}_{datetime.now().timestamp()}"
        self.user_id = user_id
        self.message_manager = MessageManager()
        self.event_manager = EventManager()
        self.autogpt = None  # AutoGPTインスタンスは後で設定
        self.last_active = datetime.now()
        self.new_message_flag = False

    def update_activity(self):
        self.last_active = datetime.now()

class RoomManager:
    def __init__(self, room_timeout: int = 30):
        self._rooms: Dict[str, Room] = {}
        self._room_timeout = timedelta(minutes=room_timeout)

    def get_or_create_room(self, user_id: str) -> Room:
        # 既存のアクティブなルームを探す
        active_room = self._find_active_room(user_id)
        if active_room:
            active_room.update_activity()
            return active_room

        # 新しいルームを作成
        room = Room(user_id)
        self._rooms[room.id] = room
        return room

    def _find_active_room(self, user_id: str) -> Optional[Room]:
        current_time = datetime.now()
        for room in self._rooms.values():
            if (room.user_id == user_id and 
                current_time - room.last_active <= self._room_timeout):
                return room
        return None

    def cleanup_inactive_rooms(self):
        current_time = datetime.now()
        inactive_rooms = [
            room_id for room_id, room in self._rooms.items()
            if current_time - room.last_active > self._room_timeout
        ]
        for room_id in inactive_rooms:
            del self._rooms[room_id] 
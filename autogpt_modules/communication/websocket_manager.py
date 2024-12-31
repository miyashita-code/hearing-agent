from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import WebSocket
import logging

from ..core.room import Room

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, room_timeout: int = 30):
        self._rooms: Dict[str, Room] = {}
        self._sockets: Dict[str, WebSocket] = {}
        self._room_timeout = timedelta(minutes=room_timeout)
        logger.debug("WebSocketManager initialized")

    def get_or_create_room(self, user_id: str) -> Room:
        """ルームを取得または作成"""
        logger.debug(f"Attempting to get/create room for user_id: {user_id}")
        logger.debug(f"Current rooms before get/create: {list(self._rooms.keys())}")
        
        active_room = self._find_active_room(user_id)
        if active_room:
            logger.debug(f"Found active room: {active_room.id}")
            active_room.update_activity()
            return active_room
        
        room = Room(user_id)
        logger.debug(f"Created new room with ID: {room.id}")
        self._rooms[room.id] = room
        logger.debug(f"Current rooms after creation: {list(self._rooms.keys())}")
        return room

    def _find_active_room(self, user_id: str) -> Optional[Room]:
        """アクティブなルームを探す"""
        current_time = datetime.now()
        for room in self._rooms.values():
            if (room.user_id == user_id and 
                current_time - room.last_active <= self._room_timeout):
                return room
        return None

    def get_room(self, room_id: str) -> Optional[Room]:
        """指定されたIDのルームを取得"""
        logger.debug(f"Attempting to get room with ID: {room_id}")
        logger.debug(f"Current rooms in manager: {list(self._rooms.keys())}")
        room = self._rooms.get(room_id)
        if room:
            logger.debug(f"Found room: {room.id}")
            room.update_activity()
        else:
            logger.debug(f"Room not found for ID: {room_id}")
        return room

    def get_room_by_sid(self, sid: str) -> Optional[Room]:
        """SIDからルームを取得"""
        socket = self._sockets.get(sid)
        if socket:
            for room in self._rooms.values():
                if room.websocket == socket:
                    return room
        return None

    async def on_message(self, room_id: str, message: str):
        """メッセージ受信時の処理"""
        room = self._rooms.get(room_id)
        if room:
            await room.message_manager.add_message(message, "user")

    async def send_message(self, room_id: str, message: str):
        """ツールからの送信用メソッド"""
        room = self._rooms.get(room_id)
        if room and room.websocket:
            await room.websocket.send_text(message)
            print(f"####### sent message to room {room_id}: {message} #######")

    async def on_disconnect(self, room_id: str):
        """切断時の処理"""
        if room_id in self._rooms:
            del self._rooms[room_id]

    async def connect(self, websocket: WebSocket, user_id: str):
        """WebSocket接続時の処理"""
        logger.debug(f"Connecting WebSocket for user_id: {user_id}")
        await websocket.accept()
        room = self.get_or_create_room(user_id)
        logger.debug(f"Room for connection: {room.id}")
        room.websocket = websocket
        self._sockets[websocket.client.port] = websocket
        logger.debug(f"WebSocket connected, current rooms: {list(self._rooms.keys())}")
        return room

    async def disconnect(self, websocket: WebSocket):
        """WebSocket切断時の処理"""
        sid = websocket.client.port
        if sid in self._sockets:
            room = self.get_room_by_sid(sid)
            if room:
                await self.on_disconnect(room.id)
            del self._sockets[sid]

    def cleanup_inactive_rooms(self):
        """非アクティブなルームを削除する"""
        current_time = datetime.now()
        inactive_rooms = [
            room_id for room_id, room in self._rooms.items()
            if current_time - room.last_active > self._room_timeout
        ]
        for room_id in inactive_rooms:
            del self._rooms[room_id]
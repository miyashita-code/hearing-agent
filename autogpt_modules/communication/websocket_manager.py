from typing import Dict, Optional
from .room import Room
from fastapi_socketio import SocketManager

class WebSocketManager:
    def __init__(self):
        self._rooms: Dict[str, Room] = {}
        self._sio = None  # Socket.IOインスタンスへの参照を保持

    def set_socketio(self, sio):
        """Socket.IOインスタンスを設定"""
        self._sio = sio

    def get_or_create_room(self, user_id: str) -> Room:
        """ルームを取得または作成"""
        for room in self._rooms.values():
            if room.user_id == user_id:
                return room
        # 新しいルームを作成
        room = Room(user_id)
        self._rooms[room.id] = room
        return room

    def get_room_by_sid(self, sid: str) -> Optional[Room]:
        """SIDからルームを取得"""
        for room in self._rooms.values():
            if room.sid == sid:
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
        if room and room.sid and self._sio:
            await self._sio.emit('message', message, room=room.sid)

    async def on_disconnect(self, room_id: str):
        """切断時の処理"""
        if room_id in self._rooms:
            del self._rooms[room_id]
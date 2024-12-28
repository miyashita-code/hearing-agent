from typing import Dict, Optional
from .room import Room
from fastapi import WebSocket # 追加

class WebSocketManager:
    def __init__(self):
        self._rooms: Dict[str, Room] = {}
        self._sockets: Dict[str, WebSocket] = {} # 追加: sidとWebSocketの対応

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
        await websocket.accept()
        room = self.get_or_create_room(user_id)
        room.websocket = websocket
        self._sockets[websocket.client.port] = websocket # 追加: sidとWebSocketの対応
        return room

    async def disconnect(self, websocket: WebSocket):
        """WebSocket切断時の処理"""
        sid = websocket.client.port
        if sid in self._sockets:
            room = self.get_room_by_sid(sid)
            if room:
                await self.on_disconnect(room.id)
            del self._sockets[sid]
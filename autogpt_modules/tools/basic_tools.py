import json
from typing import Optional
from langchain.tools.base import BaseTool
from ..core.event_manager import EventManager
from ..communication import WebSocketManager, MessageManager
from pydantic import Field, PrivateAttr
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseWebSocketTool(BaseTool):
    """Base class for all WebSocket-enabled tools."""
    room_id: Optional[str] = Field(default=None)
    
    # プライベート属性として宣言
    _websocket_manager: Optional[WebSocketManager] = PrivateAttr(default=None)
    _message_manager: Optional[MessageManager] = PrivateAttr(default=None)

    def __init__(self, websocket_manager: Optional[WebSocketManager] = None, room_id: Optional[str] = None):
        super().__init__()
        self._websocket_manager = websocket_manager
        self._message_manager = None
        if websocket_manager and room_id:
            room = websocket_manager._rooms.get(room_id)
            if room:
                self._message_manager = room.message_manager
        self.room_id = room_id


class ReplyMessage(BaseWebSocketTool):
    """Tool for sending direct messages to the user."""
    name: str = Field(default="reply_message")
    description: str = Field(default=(
        "args: "
        "   message: string (ユーザーに送信するメッセージの内容)"
        ""
        "ユーザーに直接メッセージを送信します。"
        "目的に沿ったメッセージを送信してください。"
        "メッセージは複数回のインタラクションが時系列にわたり継続していることを意識し、"
        "ユーザーの入力が遅いときには何度もメッセージを送信することはフラストレーションを高めるので積極的にwaitを使用してください."
        "例えば、２回以上連続して同じ内容をあなたから積極的に送ることはありえません."
        "また, userの入力が複数回に分けて送信してそうなときはwaitで一度待ってみるのも賢いかもしれません."
    ))

    def _run(self, tool_input: str) -> str:
        """同期的にメッセージを送信（非推奨）"""
        print("[DEBUG] ReplyMessage._run called (sync method not supported)")
        return "同期実行はサポートされていません。async を使用してください。"

    async def _arun(self, message: str) -> str:
        """Send a text message through WebSocket (Async)"""
        logger.debug("=" * 50)
        logger.debug("ReplyMessage Tool Execution")
        logger.debug("=" * 50)
        logger.debug(f"Input: {message}")
        
        try:
            data = json.loads(message)
            message = data.get("message", message)
            logger.debug(f"Parsed message: {message}")
        except json.JSONDecodeError:
            message = message
            logger.debug("Using raw input as message")

        if self._websocket_manager and self.room_id:
            try:
                json_data = {
                    "type": "response",
                    "room_id": self.room_id,
                    "user_id": self._get_user_id(),
                    "timestamp": datetime.now().isoformat(),
                    "data": {"content": message},
                }
                logger.debug(f"Sending: {json_data}")
                
                await self._websocket_manager.send_message(
                    self.room_id,
                    json.dumps(json_data)
                )
                logger.debug("Message sent successfully")
                if self._message_manager:
                    await self._message_manager.add_message(message, "assistant")
                
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                return f"Error: {str(e)}"
        else:
            logger.warning("WebSocket connection not available")
            return "WebSocket connection not available"

        logger.debug("=" * 50)
        return message

    def _get_user_id(self) -> Optional[str]:
        """Get user ID from room"""
        if self._websocket_manager and self.room_id:
            room = self._websocket_manager._rooms.get(self.room_id)
            if room:
                return room.user_id
        return None

class ReplyMessageWithStamp(BaseWebSocketTool):
    """Tool for sending stamps to the user."""
    name: str = Field(default="reply_message_with_stamp")
    description: str = Field(default=(
        "args: "
        "   package_id: string (スタンプのパッケージID)"
        "   sticker_id: string (スタンプのステッカーID)"
        ""
        "Send a stamp to the user on LINE. "
        "Use this when waiting for a response instead of verbal prompting."
        "積極的に使おう！！"
        "waitがしばらく長く続いた場合は, 0のstampを送信するとよい(5min, 60minとか続いているタイミングで)"
    ))

    def _run(self, tool_input: str) -> str:
        """同期的にスタンプを送信（非推奨）"""
        return "同期実行はサポートされていません。async を使用してください。"

    async def _arun(self, tool_input: str) -> str:
        """Send a stamp through WebSocket (Async)"""
        # "package_id" などを含む JSON 文字列として受け取るなら適宜パースし、
        # 個別の変数に分解してください（例として直接 tool_input を利用）
        # ここでは簡易の例として以下のように実装
        data = json.loads(tool_input)
        package_id = data.get("package_id", "0")
        sticker_id = data.get("sticker_id", "0")

        if self._websocket_manager and self.room_id:
            await self._websocket_manager.send_message(
                self.room_id,
                json.dumps({
                    "type": "stamp",
                    "room_id": self.room_id,
                    "user_id": self._get_user_id(),
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "package_id": package_id,
                        "sticker_id": sticker_id,
                    },
                })
            )
        return f"Stamp sent: package_id={package_id}, sticker_id={sticker_id}"

    def _get_user_id(self) -> Optional[str]:
        """Get user ID from room"""
        if self._websocket_manager and self.room_id:
            room = self._websocket_manager._rooms.get(self.room_id)
            if room:
                return room.user_id
        return None
    
class Finish(BaseTool):
    name: str = Field(default="finish")
    description: str = Field(default=(
        "use this to signal that you have finished all your objectives. "
        "Provide a final response message as the input."
    ))

    def _run(self, tool_input: str) -> str:
        # tool_inputをそのまま最終出力として返す
        return tool_input

    async def _arun(self, tool_input: str) -> str:
        # 非同期対応が必要な場合はここで実装
        # シンプルな処理なので同期と同様
        return self._run(tool_input)

class GoNext(BaseTool):
    name: str = Field(default="go_next")
    description: str = Field(default=(
        "use this to signal that you have finished current goal and move to next goal. "
        "before callingthis, you shold save some sata if neccesary.",
    ))

    def _run(self, tool_input: str) -> str:
        # tool_inputをそのまま最終出力として返す
        return tool_input

    async def _arun(self, tool_input: str) -> str:
        # 非同期対応が必要な場合はここで実装
        # シンプルな処理なので同期と同様
        return self._run(tool_input)

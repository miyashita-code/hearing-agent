from typing import Optional
from langchain.tools.base import BaseTool
from asyncio import sleep, CancelledError
from ..core.event import EventManager
from ..communication import WebSocketManager, MessageManager
from pydantic import Field, PrivateAttr

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

    async def _send_message(self, message: str) -> None:
        """WebSocketを通じてメッセージを送信"""
        if self._websocket_manager and self.room_id:
            print(f"Sending message: {message} to room: {self.room_id}")
            await self._websocket_manager.send_message(self.room_id, message)

            print(f"Adding message: {message} to message_manager")
            if self._message_manager:
                try:
                    await self._message_manager.add_message(message, "assistant")
                except Exception as e:
                    print(f"Error adding message to message_manager: {e}")

class ReplyMessage(BaseWebSocketTool):
    """Tool for sending direct messages to the user."""
    name: str = Field(default="reply_message")
    description: str = Field(default="""
    args: 
        message: str (ユーザーに送信するメッセージの内容)
                             
    ユーザーに直接メッセージを送信します。
    目的に沿ったメッセージを送信してください。
    メッセージは複数回のインタラクションが時系列にわたり継続していることを意識し、
    ユーザーの入力が遅いときには何度もメッセージを送信することはフラストレーションを高めるので積極的にwaitを使用してください.
    例えば、２回以上連続して同じ内容をあなたから積極的に送ることはありえません.
    また, userの入力が複数回に分けて送信してそうなときはwaitで一度待ってみるのも賢いかもしれません.
    """)

    def _run(self, message: str) -> str:
        return message

    async def _arun(self, message: str) -> str:
        await self._send_message(message)
        return message

class ReplyMessageWithStamp(BaseWebSocketTool):
    """Tool for sending stamps to the user."""
    name: str = Field(default="reply_message_with_stamp")
    description: str = Field(default=(
        "args: "
        "   index: int (スタンプのインデックス, 0のみ有効)"
        ""
        "Send a stamp to the user on LINE. "
        "Currently only index 0 (peek stamp) is available. "
        "Use this when waiting for a response instead of verbal prompting."
        "積極的に使おう！！"
        "waitがしばらく長く続いた場合は, 0のstampを送信するとよい(5min, 60minとか続いているタイミングで)"
    ))
    
    def _run(self, index: int) -> str:
        if index != 0:
            return "Invalid stamp index. Only 0 (peek stamp) is available."
        return "Peek stamp sent"
        
    async def _arun(self, index: int) -> str:
        if index != 0:
            return "Invalid stamp index. Only 0 (peek stamp) is available."
        await self._send_message("STAMP:0")
        return "Peek stamp sent"

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

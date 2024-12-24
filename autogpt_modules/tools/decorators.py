from functools import wraps
from typing import Callable, Any, Type
from langchain.tools.base import BaseTool
from ..communication import WebSocketManager

def websocket_tool(cls: Type[BaseTool]):
    """WebSocket送信機能を付与するデコレータ"""
    original_arun = cls._arun
    
    @wraps(original_arun)
    async def wrapped_arun(self, *args, **kwargs):
        result = await original_arun(self, *args, **kwargs)
        if hasattr(self, 'websocket_manager') and hasattr(self, 'room_id'):
            if self.websocket_manager and self.room_id:
                await self.websocket_manager.send_message(
                    self.room_id,
                    result
                )
                self.message_manager.add_message(result, "assistant")
        return result

    cls._arun = wrapped_arun
    return cls
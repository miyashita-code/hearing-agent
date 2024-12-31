import json
from typing import Optional, Dict
from langchain.tools.base import BaseTool
from pydantic import Field
from datetime import datetime
from ..communication import WebSocketManager
from .basic_tools import BaseWebSocketTool
from ..utils.llm.llm_chains import generate_summary
import logging

logger = logging.getLogger(__name__)

class SaveResult(BaseWebSocketTool):
    """Tool for saving and managing task results."""
    name: str = Field(default="save_result")
    description: str = Field(default=(
        "args: "
        "   goal: string (このゴールに対する結果を保存する)"
        "現在のゴールの実行結果をチャット履歴から要約して保存します。"
        "保存された結果は後続のプラン生成時に参照されます。"
    ))

    def _run(self, tool_input: str) -> str:
        """同期的に結果を保存（非推奨）"""
        return "同期実行はサポートされていません。async を使用してください。"

    async def _arun(self, tool_input: str) -> str:
        """Save a result summary (Async)"""
        logger.debug("=" * 50)
        logger.debug("SaveResult Tool Execution")
        logger.debug("=" * 50)
        logger.debug(f"Input: {tool_input}")

        try:
            data = json.loads(tool_input)
            goal = data.get("goal", "")
            metadata = data.get("metadata", {})
        except json.JSONDecodeError:
            logger.error("Invalid JSON input")
            return "Error: Invalid input format. Expected JSON with 'goal' field."

        if not goal:
            return "Error: Goal is required."

        if self._websocket_manager and self.room_id:
            try:
                room = self._websocket_manager._rooms.get(self.room_id)
                if not room:
                    return "Error: Room not found"

                # チャット履歴を取得
                chat_history = room.message_manager.get_messages()
                chat_history_for_llm = room.message_manager.get_chat_history()
                
                # LLMを使用して結果を要約
                summary = await generate_summary(
                    goal=goal,
                    chat_history=chat_history,
                    history=chat_history_for_llm
                )
                
                # 結果を保存
                await room.result_manager.add_result(goal, summary, metadata)
                
                # WebSocket経由で通知
                json_data = {
                    "type": "result_saved",
                    "room_id": self.room_id,
                    "user_id": self._get_user_id(),
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "goal": goal,
                        "summary": summary,
                        "metadata": metadata
                    },
                }
                
                await self._websocket_manager.send_message(
                    self.room_id,
                    json.dumps(json_data)
                )
                
                logger.debug("Result saved successfully")
                return summary

            except Exception as e:
                logger.error(f"Failed to save result: {e}")
                return f"Error: {str(e)}"
        else:
            logger.warning("WebSocket connection not available")
            return "WebSocket connection not available"

    def _get_user_id(self) -> Optional[str]:
        """Get user ID from room"""
        if self._websocket_manager and self.room_id:
            room = self._websocket_manager._rooms.get(self.room_id)
            if room:
                return room.user_id
        return None
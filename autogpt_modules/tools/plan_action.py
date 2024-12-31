import json
from typing import Optional, Dict
from langchain.tools.base import BaseTool
from pydantic import Field
from datetime import datetime
from ..communication import WebSocketManager
from .basic_tools import BaseWebSocketTool
from ..utils.llm.llm_chains import generate_plan
import logging

logger = logging.getLogger(__name__)

import json
import logging
from typing import Optional, Type

from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools.base import BaseTool

# ★ このあたりはユーザー環境に合わせて import を修正してください ★
from ..communication import WebSocketManager
from .basic_tools import BaseWebSocketTool
from ..utils.llm.llm_chains import generate_plan

logger = logging.getLogger(__name__)



class PlanActionInput(BaseModel):
    """PlanAction に必要な引数スキーマ"""
    goal: str = Field(..., description="現在のゴール（必須）")
    context: Optional[str] = Field("", description="追加のコンテキスト情報（任意）")


class PlanAction(BaseWebSocketTool):
    """
    Tool for generating and managing action plans.
    
    - LLMからは `{"goal": "...", "context": "..."}`
      のような形で引数を渡して呼び出す。
    - 同期実行 (_run) はサポートしないので、基本的に `_arun` を使用。
    """

    # Tool名や説明
    name: str = "plan_action"
    description: str = (
        "現在のゴールに対する実行プランを生成します。"
        "過去のゴールと結果の履歴を参照して、より効果的なプランを立案します。"
        "プランは自動的に保存され、後で参照できます。"
    )

    args_schema: Type[PlanActionInput] = PlanActionInput

    def _run(self, goal: str, context: Optional[str] = None) -> str:
        """
        同期的にプランを生成（非推奨）
        LangChain上は _run() が必須なので定義はするが、
        実行してもサポートしないメッセージを返すだけ。
        """
        return "同期実行はサポートされていません。async を使用してください。"

    async def _arun(self, goal: str, context: Optional[str] = None) -> str:
        """
        非同期でプランを生成するメソッド。
        goal と context は StructuredTool 準拠で
        直接キーワード引数として受け取れる。
        """
        logger.debug("=" * 50)
        logger.debug("PlanAction Tool Execution")
        logger.debug("=" * 50)
        logger.debug(f"Goal: {goal}")
        logger.debug(f"Context: {context}")

        # goal が空の場合はエラー
        if not goal:
            return "Error: Goal is required."

        # WebSocketと部屋が有効かチェック
        if self._websocket_manager and self.room_id:
            try:
                room = self._websocket_manager._rooms.get(self.room_id)
                if not room:
                    return "Error: Room not found"

                # 過去の結果を取得
                past_results = room.result_manager.get_goal_result_pairs()

                # チャット履歴を取得
                chat_history = room.message_manager.get_chat_history()

                # LLM を使用してプランを生成
                plan = await generate_plan(
                    goal=goal,
                    context=context,
                    past_results=past_results,
                    history=chat_history
                )

                # プランを保存
                await room.plan_manager.add_plan(goal, plan)

                # WebSocket経由で通知
                json_data = {
                    "type": "plan_created",
                    "room_id": self.room_id,
                    "user_id": self._get_user_id(),
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "goal": goal,
                        "plan": plan
                    },
                }
                await self._websocket_manager.send_message(
                    self.room_id,
                    json.dumps(json_data)
                )

                logger.debug("Plan created and saved successfully")
                return plan

            except Exception as e:
                logger.error(f"Failed to create plan: {e}")
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



from typing import List, Dict, Optional
from datetime import datetime
import json
from pydantic import BaseModel, Field

class ActionPlan(BaseModel):
    """アクションプランを表すモデル"""
    plan: str = Field(..., description="実行プランの内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="プラン作成時のタイムスタンプ")
    metadata: Optional[Dict] = Field(default=None, description="追加のメタデータ")


class ActionPlanManager:
    """アクションプランを管理するクラス"""
    def __init__(self):
        self._plans: List[ActionPlan] = []

    async def add_plan(self, plan: str, metadata: Optional[Dict] = None) -> ActionPlan:
        """新しいプランを追加"""
        plan_obj = ActionPlan(
            plan=plan,
            metadata=metadata
        )
        self._plans.append(plan_obj)
        return plan_obj

    def get_plans(self) -> List[ActionPlan]:
        """全てのプランを取得"""
        return self._plans

    def get_latest_plan(self) -> Optional[ActionPlan]:
        """最新のプランを取得"""
        return self._plans[-1] if self._plans else None

    def get_plans_for_goal(self, goal: str) -> List[ActionPlan]:
        """特定のゴールに関連するプランを取得"""
        return [plan for plan in self._plans if plan.goal == goal]

    def to_dict(self) -> Dict:
        """プラン一覧をdict形式で取得"""
        return {
            "plans": [plan.model_dump() for plan in self._plans]
        }


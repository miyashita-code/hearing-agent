from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class Result(BaseModel):
    """タスク実行結果を表すモデル"""
    summary: str = Field(..., description="実行結果の要約")
    timestamp: datetime = Field(default_factory=datetime.now, description="結果記録時のタイムスタンプ")
    metadata: Optional[Dict] = Field(default=None, description="追加のメタデータ")

class ResultManager:
    """タスク実行結果を管理するクラス"""
    def __init__(self):
        self._results: List[Result] = []

    async def add_result(self, summary: str, metadata: Optional[Dict] = None) -> Result:
        """新しい結果を追加"""
        result_obj = Result(
            summary=summary,
            metadata=metadata
        )
        self._results.append(result_obj)
        return result_obj

    def get_results(self) -> List[Result]:
        """全ての結果を取得"""
        return self._results

    def get_latest_result(self) -> Optional[Result]:
        """最新の結果を取得"""
        return self._results[-1] if self._results else None

    def get_results_for_goal(self, goal: str) -> List[Result]:
        """特定のゴールに関連する結果を取得"""
        return [result for result in self._results if result.goal == goal]

    def get_goal_result_pairs(self) -> List[Dict[str, str]]:
        """全てのゴールと結果のペアを取得"""
        return [{"goal": r.goal, "result": r.summary} for r in self._results]

    def to_dict(self) -> Dict:
        """結果一覧をdict形式で取得"""
        return {
            "results": [result.model_dump() for result in self._results]
        } 
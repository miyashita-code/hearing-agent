from ast import Dict
from typing import Dict, Any, Optional

from ..communication import WebSocketManager
from ..core.event_manager import EventManager

import asyncio
from pydantic import Field, PrivateAttr
from .basic_tools import BaseWebSocketTool


class Wait(BaseWebSocketTool):
    """指定された時間だけ待機するツール"""
    
    name: str = Field(default="wait")
    description: str = Field(
        default=(
            "args: "
            "   minutes: float (待機する分数)"
            "指定された分数だけ待機します。ユーザーからの新着メッセージがあったときには即座に再開します. "
            "ユーザーの入力が遅いときに必要以上にメッセージを送信しないためのツールです. "
            "ユーザーの入力が遅いときには何度もメッセージを送信することはフラストレーションを高めるので積極的にwaitを使用してください."
            "連続でwaitを発動するときはexpスケールで設定時間を長くするといい. (1->2->4->8みたいにだんだん長くなる). EVENT HISTORYで連続してwaitが発動しているかを確認できる"
            "UXを高める目的以外でuserの応答を無視してwaitすることは許されない"
        )
    )
    
    # プライベート属性として宣言（アンダースコアプレフィックス付き）
    _websocket_manager: WebSocketManager = PrivateAttr()
    _event_manager: EventManager = PrivateAttr()
    _waiting: bool = PrivateAttr(default=False)
    _room_id: str = PrivateAttr(default=None)

    def __init__(
        self,
        websocket_manager: WebSocketManager,
        event_manager: EventManager,
        room_id: Optional[str] = None,
    ):
        super().__init__(websocket_manager=websocket_manager, room_id=room_id)
        self._event_manager = event_manager
        self._waiting = False
        self._waiting_info: Dict[str, float] = {"consecutive_waiting_duration": 0, "prev_waiting_info": 0}

    async def _check_new_message(self, old_user_msg_id: str, old_user_msg_content: str) -> bool:
        """新規で異なるユーザーメッセージがあるかを判定"""
        room = self._websocket_manager._rooms.get(self._room_id)
        if not room:
            return False
        
        messages = room.message_manager.get_messages()
        if not messages:
            return False
        
        # 最後のユーザーメッセージ取得
        for msg in reversed(messages):
            if msg.sender == "user":
                # 新しいメッセージIDまたは内容が異なるものが来ているかをチェック
                if msg.id != old_user_msg_id or msg.content != old_user_msg_content:
                    return True
                break
        return False

    async def _wait_with_check(self, minutes: float) -> str:
        """メッセージチェック付きの待機処理"""
        self._waiting = True
        total_seconds = minutes * 60
        check_interval = 0.1  # 0.1秒ごとにチェック

        elapsed_time = 0
        initial_event_count = len(self._event_manager.get_event_history())

        while elapsed_time < total_seconds and self._waiting:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval

            # event_historyを取得して、wait開始後に発生したイベントを確認
            event_history = self._event_manager.get_event_history()
            current_events = event_history[initial_event_count:]

            # new_message_come イベントがあるかチェック
            for ev in current_events:
                if ev.get('action') == 'new_message_come':
                    # 新規メッセージイベントが確認されたため待機終了
                    self._waiting = False
                    print("BREAK WAIT due to new_message_come event")
                    self._update_waiting_info(
                        consecutive_waiting_duration=self.get_waiting_info()["consecutive_waiting_duration"] + elapsed_time/60,
                        prev_waiting_info=elapsed_time/60
                    )
                    return f"{elapsed_time/60:.1f}分経過。new_message_comeイベントにより待機を終了しました。"
                
                if ev.get('action') == 'finish_session':
                    # セッション終了イベントが確認されたため待機終了
                    self._waiting = False
                    print("BREAK WAIT due to finish_session event")
                    self._update_waiting_info(
                        consecutive_waiting_duration=self.get_waiting_info()["consecutive_waiting_duration"] + elapsed_time/60,
                        prev_waiting_info=elapsed_time/60
                    )
                    return f"{elapsed_time/60:.1f}分経過。finish_sessionイベントにより待機を終了しました。"


        # ループを抜けた場合は、待機時間終了または_waitingがFalseになった状態
        self._waiting = False
        self._update_waiting_info(
            consecutive_waiting_duration=self.get_waiting_info()["consecutive_waiting_duration"] + minutes,
            prev_waiting_info=minutes
        )
        return f"{minutes}分間の待機が完了しました。"

    async def _arun(self, minutes: float = 1.0) -> str:
        """
        Args:
            minutes (float): 待機する分数（デフォルト: 1.0分）
        Returns:
            str: 待機完了メッセージ
        """
        try:
            wait_time = float(minutes)
            if wait_time < 0:
                return "待機時間は0以上の値を指定してください。"
            if wait_time > 60:  # 最大待機時間を60分に制限
                wait_time = 60
        except ValueError:
            return "待機時間は数値で指定してください。"

            
        await self._event_manager.add_event(
            action="wait",
            purpose=f"{wait_time}分間待機開始",
            result=None
        )

        print(f"=== wait start {wait_time} min===")
        result = await self._wait_with_check(wait_time)


        print("=== wait end ===")
        return result

    def _run(self, minutes: float = 1.0) -> str:
        raise NotImplementedError("このツールは非同期でのみ使用できます。") 
    
    def reset_waiting_info(self):
        self._waiting_info = {"consecutive_waiting_duration": 0, "prev_waiting_info": 0}

    def _update_waiting_info(
            self, 
            consecutive_waiting_duration: float = 0, 
            prev_waiting_info: float = 0
        ):
        self._waiting_info["consecutive_waiting_duration"] = consecutive_waiting_duration
        self._waiting_info["prev_waiting_info"] = prev_waiting_info

    def get_waiting_info(self) -> 'Dict[str, float]':
        """待機情報を取得する

        Returns:
            Dict[str, float]: 待機情報
        """
        return {
            "consecutive_waiting_duration": self._waiting_info["consecutive_waiting_duration"],
            "prev_waiting_info": self._waiting_info["prev_waiting_info"]
        }


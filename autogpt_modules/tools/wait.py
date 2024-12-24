from typing import Optional
from langchain.tools import BaseTool
from ..communication import WebSocketManager
from ..core.event import EventManager
from .decorators import websocket_tool
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

            # デバッグ用
            # print("EVENT NUMBER:", len(current_events))
            # for e in current_events:
            #     print(e)

            # new_message_come イベントがあるかチェック
            for ev in current_events:
                if ev.get('action') == 'new_message_come':
                    # 新規メッセージイベントが確認されたため待機終了
                    self._waiting = False
                    print("BREAK WAIT due to new_message_come event")
                    return f"{elapsed_time/60:.1f}分経過。new_message_comeイベントにより待機を終了しました。"

            # 上記forループ内で見つからなければ、そのまま待機継続
            # 待機終了判定はループ条件に依存するためここでは特に何もしない

        # ループを抜けた場合は、待機時間終了または_waitingがFalseになった状態
        self._waiting = False
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
            if wait_time > 10:  # 最大待機時間を10分に制限
                wait_time = 10
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
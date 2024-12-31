from datetime import datetime
from typing import Dict, List, Any

class Event:
    """単一のイベントを表現するクラス"""
    def __init__(self, action: str, purpose: str=None, result: str=None):
        self.time = datetime.now().strftime("%H:%M:%S")
        self.action = action
        self.purpose = purpose if purpose else ""
        self.result = result if result else ""

    def to_dict(self) -> Dict[str, str]:
        """イベントを辞書形式に変換"""
        return {
            "time": self.time,
            "action": self.action,
            "purpose": self.purpose,
            "result": self.result
        }

class EventManager:
    """イベント履歴を管理するクラス"""
    def __init__(self):
        self._event_history: List[Event] = []
        self._listeners = {}
        self._new_messages = False
        
    async def add_event(self, action: str, purpose: str=None, result: str=None) -> None:
        """イベント履歴に新しいイベントを追加
        
        Args:
            action (str): 実行されたアクション
            purpose (str): アクションの目的
            result (str): アクションの結果
        """
        event = Event(action, purpose, result)
        self._event_history.append(event)
    
    def get_event_history(self) -> List[Dict[str, str]]:
        """イベント履歴を取得
        
        Returns:
            List[Dict[str, str]]: イベント履歴のリスト
        """
        return [event.to_dict() for event in self._event_history]
    
    async def emit(self, event_name: str, data: Any = None) -> None:
        if event_name == "new_message":
            self._new_messages = True
        if event_name in self._listeners:
            for listener in self._listeners[event_name]:
                await listener(data)
    
    def has_new_messages(self) -> bool:
        if self._new_messages:
            self._new_messages = False
            return True
        return False
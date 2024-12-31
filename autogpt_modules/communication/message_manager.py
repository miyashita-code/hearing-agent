from datetime import datetime
from typing import List, Dict
from ..core.event_manager import EventManager

class Message:
    def __init__(self, content: str, sender: str):
        self.id = f"msg_{datetime.now().timestamp()}"
        self.content = content
        self.sender = sender
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "sender": self.sender,
            "timestamp": self.timestamp.isoformat()
        }

class MessageManager:
    def __init__(self):
        self._messages: List[Message] = []



    async def add_message(self, content: str, sender: str) -> Message:
        """新しいメッセージを追加してイベントを発火"""
        message = Message(content, sender)
        self._messages.append(message)
        self.new_messages_since_last_check = True

        return message

    def get_messages(self) -> List[Dict]:
        """全メッセージを取得"""
        return [msg.to_dict() for msg in self._messages]

    def get_chat_history(self) -> List[Dict]:
        """LLMに渡すためのチャット履歴を取得"""
        return [
            {
                "role": msg.sender,
                "content": msg.content
            }
            for msg in self._messages
        ]

    def clear(self) -> None:
        """メッセージをクリア"""
        self._messages.clear()

    def has_new_messages(self) -> bool:
        """新しいメッセージがあるかチェック"""
        try:
            return self._messages[-1].sender == "user"
        except:
            return False

    def get_consecutive_message_number(self) -> int:
        """ユーザーからの新しい応答がない場合の連続応答数
        
        Returns:
            int: assistantからの連続メッセージ数。
                 最新のメッセージがuserの場合は0を返す。
                 userからの連続メッセージ数の場合は負の値を返す。
        """
        if len(self._messages) == 0:
            return 0
            
        count = 0
        for message in reversed(self._messages):
            if message.sender == "assistant":
                if count < 0:  # userの連続後にassistantが来た場合
                    break
                count += 1
            elif message.sender == "user":
                if count > 0:  # assistantの連続後にuserが来た場合
                    break
                count -= 1
            else:
                break
                
        return count



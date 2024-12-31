from datetime import datetime, timedelta
from typing import Dict, Optional

from autogpt_modules.core.event_manager import EventManager

from autogpt_modules.communication.message_manager import MessageManager
from autogpt_modules.communication.plan_manager import ActionPlanManager
from autogpt_modules.communication.result_manager import ResultManager


class Room:
    def __init__(self, user_id: str):
        self.id = f"room_{user_id}_{datetime.now().timestamp()}"
        self.user_id = user_id
        self.message_manager = MessageManager()
        self.event_manager = EventManager()
        self.autogpt : Optional["AutoGPT"] = None
        self.last_active = datetime.now()
        self.new_message_flag = False
        self.plan_manager = ActionPlanManager()
        self.result_manager = ResultManager()

    def update_activity(self):
        self.last_active = datetime.now()


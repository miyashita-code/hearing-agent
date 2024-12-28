import traceback
from typing import List, Callable, Any, Dict
from datetime import datetime
import json
from langchain.tools.base import BaseTool
from langchain_core.prompts import BaseChatPromptTemplate
from langchain_core.messages import BaseMessage, SystemMessage
from ..communication import MessageManager
from .base_prompt import SYSTEM_PROMPT, RESPONSE_FORMAT, construct_base_prompt
from pydantic import Field
from pydantic import BaseModel



from typing import List, Callable, Any, Dict, Optional
from datetime import datetime
import json
from langchain.tools.base import BaseTool
from langchain_core.prompts import BaseChatPromptTemplate
from langchain_core.messages import BaseMessage, SystemMessage
from ..communication import MessageManager
from .base_prompt import SYSTEM_PROMPT, RESPONSE_FORMAT, construct_base_prompt
from pydantic import Field, BaseModel

class AutoGPTPrompt(BaseChatPromptTemplate, BaseModel):
    ai_name: str
    ai_role: str
    tools: List[BaseTool]
    input_variables: List[str]
    token_counter: Callable[[str], int]
    send_token_limit: int = 4096
    get_chat_history: Optional[Callable[[], List[str]]] = None
    get_event_history: Optional[Callable[[], List[Dict[str, str]]]] = None
    get_is_new_response_from_user_came: Optional[Callable[[], bool]] = None
    get_consecutive_message_number: Optional[Callable[[], int]] = None

    class Config:
        arbitrary_types_allowed = True

    def _format_tools_with_number(self) -> str:
        tool_strings = []
        for i, tool in enumerate(self.tools, 1):
            args_str = ", ".join(f"{name}: {typ}" for name, typ in tool.args.items())
            tool_strings.append(f"*{i}. {tool.name}: {tool.description}, Args: {args_str}")
        return "\n".join(tool_strings)

    def _format_goals(self, goals: List[str]) -> str:
        return "\n".join(f"{i+1}. {goal}" for i, goal in enumerate(goals))
    
    def _format_list_with_order_number(self, list: List[str], prefix: str = "") -> str:
        return "\n".join(f"{prefix}{i+1}. {item}" for i, item in enumerate(list))

    def construct_full_prompt(self, goals: List[str], current_goal: str, common_rule: str) -> str:
        formatted_goals = self._format_goals(goals)
        formatted_tools = self._format_tools_with_number()
        response_format = self._construct_response_format()
        chat_history = self._format_list_with_order_number(self.get_chat_history() if self.get_chat_history else [], prefix="b")
        event_history = self._format_list_with_order_number(self.get_event_history() if self.get_event_history else [], prefix="a")
        flags_format = {}#{"is_finish": "true or false, if true, you will choose finish command.", "is_go_next": "true or false, if true, you should choose go_next command.", "is_update_info": "true or false, if true, you should update info command.", "is_planning": "true or false, if true, you should choose planning command."}

        try:
            is_new_response_from_user_came = self.get_is_new_response_from_user_came() if self.get_is_new_response_from_user_came else False
            consecutive_message_number = self.get_consecutive_message_number() if self.get_consecutive_message_number else 0
        except Exception as e:
            print(f"Error occurred while getting message status: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {e.__dict__}")
            print(f"Error traceback: {traceback.format_exc()}")
            # デフォルト値を設定
            is_new_response_from_user_came = False
            consecutive_message_number = 0


        full_prompt = construct_base_prompt(
            formatted_goals=formatted_goals,
            current_goal=current_goal,
            common_rule=common_rule,
            chat_history=chat_history,
            event_history=event_history,
            is_new_response_from_user_came=is_new_response_from_user_came,
            formatted_tools=formatted_tools,
            response_format=response_format,
            consecutive_message_number=consecutive_message_number,
            flags_format=flags_format
        )

        return full_prompt

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """メッセージをフォーマットして返す"""

        full_prompt = self.construct_full_prompt(
            goals=kwargs.get("goals", []),
            current_goal=kwargs.get("goal", ""),
            common_rule=kwargs.get("common_rule", "")
        )

        return [SystemMessage(content=full_prompt)]
    
    def _construct_response_format(self) -> Dict[str, Any]:
        return RESPONSE_FORMAT

    @property
    def _prompt_type(self) -> str:
        return "autogpt"

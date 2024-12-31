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
    get_summaries: Optional[Callable[[], List[str]]] = None
    get_action_plan: Optional[Callable[[], str]] = None
    get_is_new_response_from_user_came: Optional[Callable[[], bool]] = None
    get_consecutive_message_number: Optional[Callable[[], int]] = None
    get_waiting_info: Optional[Callable[[], Dict[str, Any]]] = None


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
    
    def _format_dicts_with_order_number(self, dicts: List[Dict[str, Any]], prefix: str = "") -> str:
        try:
            return "\n".join(f"{prefix}{i+1}. {json.dumps(dict)}" for i, dict in enumerate(dicts))
        except Exception as e:
            print(f"Error occurred while formatting dicts: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {e.__dict__}")
            print(f"Error traceback: {traceback.format_exc()}")
            return ""

    def construct_full_prompt(self, goals: List[str], current_goal: str, common_rule: str, flags: Dict[str, bool]) -> str:
        formatted_goals = self._format_goals(goals)
        formatted_tools = self._format_tools_with_number()
        response_format = self._construct_response_format()
        chat_history = self._format_list_with_order_number(self.get_chat_history() if self.get_chat_history else [], prefix="b")
        event_history = self._format_list_with_order_number(self.get_event_history() if self.get_event_history else [], prefix="a")
        summaries = self._format_dicts_with_order_number(self.get_summaries() if self.get_summaries else [], prefix="c")
        action_plan = self.get_action_plan() if self.get_action_plan else ""
        flags_format = self._construct_flags_format(flags)
        waiting_info = self.get_waiting_info()
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
            # 目標と規則に関する情報
            formatted_goals=formatted_goals,
            current_goal=current_goal, 
            common_rule=common_rule,
            action_plan=action_plan,

            # 履歴情報
            event_history=event_history,
            chat_history=chat_history,
            summaries=summaries,

            # メッセージング制御情報
            is_new_response_from_user_came=is_new_response_from_user_came,
            consecutive_message_number=consecutive_message_number,
            waiting_info=json.dumps(waiting_info),

            # システム設定情報
            formatted_tools=formatted_tools,
            response_format=response_format,
            flags_format=flags_format
        )

        print(f"\n\n +++++++++++++++++++++++++++++ \n\n[debug] full_prompt: {full_prompt} \n\n +++++++++++++++++++++++++++++")

        return full_prompt

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """メッセージをフォーマットして返す"""
        full_prompt = self.construct_full_prompt(
            goals=kwargs.get("goals", []),
            current_goal=kwargs.get("current_goal", ""),
            common_rule=kwargs.get("common_rule", ""),
            flags=kwargs.get("flags", {})
        )

        return [SystemMessage(content=full_prompt)]
    
    def _construct_response_format(self) -> Dict[str, Any]:
        return RESPONSE_FORMAT
    
    def _construct_flags_format(self, flags: Dict[str, bool]) -> str:
        def _create_flag_entry(flag_name: str, flags: Dict[str, bool]) -> Dict[str, Any]:
            return {
                "description": f"true or false, if true, you should choose `{flag_name}` command.",
                "value": "true" if flags.get(flag_name, False) else "false"
            }
        
        # ex) flag_names = ["finish", "go_next", "plan_action"]
        flag_names = flags.keys()

        flag_dict = {
            f"{flag_name}_flag": _create_flag_entry(flag_name,
                flags)
            for flag_name in flag_names
        }

        flag_format = json.dumps(flag_dict, indent=2, ensure_ascii=False)
        return flag_format


    @property
    def _prompt_type(self) -> str:
        return "autogpt"

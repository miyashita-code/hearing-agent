from __future__ import annotations

from typing import List, Optional, Any, Dict, Callable
import os
from datetime import datetime
import json

from dotenv import load_dotenv
from langchain.chains.llm import LLMChain
from langchain_core.language_models import BaseChatModel
from langchain.tools.base import BaseTool
from langchain_experimental.autonomous_agents.autogpt.output_parser import (
    AutoGPTOutputParser,
    BaseAutoGPTOutputParser,
)
from langchain_experimental.autonomous_agents.autogpt.prompt_generator import (
    FINISH_NAME,
)
from langchain_core.runnables import RunnableSequence

from .custom_congif import MODEL
from .autogpt_prompt import AutoGPTPrompt
from .event import EventManager
from ..communication import MessageManager, WebSocketManager, RoomManager # WebSocketManager, RoomManagerを追加
from ..tools import (
    ReplyMessage,
    ReplyMessageWithStamp,
    Wait,
)

from .event import Event
from utils import string_to_bool
# 最初に.envを読み込む
load_dotenv()

class AutoGPT:
    """Autonomous agent system for chat-based interaction."""
    
    def __init__(
        self,
        ai_name: str,
        ai_role: str,
        tools: List[BaseTool],
        llm: BaseChatModel,
        output_parser: Optional[BaseAutoGPTOutputParser] = None,
        chain: Optional[RunnableSequence] = None,
        verbose: bool = True,
        event_manager: EventManager = None,
        websocket_manager: WebSocketManager = None, # 追加
        room_manager: RoomManager = None, # 追加

    ):
        self.ai_name = ai_name
        self.ai_role = ai_role
        self.tools = tools
        self.llm = llm
        self.output_parser = output_parser or AutoGPTOutputParser()
        self.chain = chain
        self.verbose = verbose
        self.count = 0
        self.event_manager = event_manager
        self.websocket_manager = websocket_manager
        self.room_manager = room_manager
        self.disconnect_flag = False

    @classmethod
    def from_llm_and_tools(
        cls,
        ai_name: str,
        ai_role: str,
        tools: List[BaseTool],
        llm: BaseChatModel,
        get_chat_history: Callable[[], List[Dict[str, Any]]],
        get_event_history: Callable[[], List[Dict[str, Any]]],
        verbose: bool = True,
        event_manager: EventManager = None,
        message_manager: MessageManager = None,
        websocket_manager: WebSocketManager = None, # 追加
        room_manager: RoomManager = None, # 追加
    ) -> AutoGPT:
        """LLMとツールからAutoGPTインスタンスを作成"""
        output_parser = AutoGPTOutputParser()

        prompt = AutoGPTPrompt(
            ai_name=ai_name,
            ai_role=ai_role,
            tools=tools,
            input_variables=[],
            token_counter=llm.get_num_tokens,
            get_chat_history=get_chat_history,
            get_event_history=get_event_history,
            verbose=verbose,
            event_manager=event_manager,
            get_consecutive_message_number=message_manager.get_consecutive_message_number,
            get_is_new_response_from_user_came=message_manager.has_new_messages
            )

        chain = prompt | llm

        return cls(
            ai_name=ai_name,
            ai_role=ai_role,
            tools=tools,
            llm=llm,
            output_parser=output_parser,
            chain=chain,
            verbose=verbose,
            event_manager=event_manager,
            websocket_manager=websocket_manager, # 追加
            room_manager=room_manager, # 追加
        )

    async def _log(self, message: str, data: Any = None) -> None:
        """デバッグ情報をログ出力"""
        if self.verbose:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{timestamp}] {message}")
            if data:
                if isinstance(data, (dict, list)):
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    print(str(data))

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any], purpose: str) -> str:
        """ツールを実行"""

        tools = {t.name: t for t in self.tools}
        if tool_name not in tools:
            error = f"Error: {tool_name} is not a valid tool."
            return error
            
        tool = tools[tool_name]
        try:
            result = await tool._arun(**args)

            await self.event_manager.add_event(
                action="tool_execution : " + tool_name,
                purpose=purpose,
                result=result
            )
            print(f"add_event: {result}")
            return result
        except Exception as e:
            error = f"Error: {str(e)}"
            return error

    async def run(self, goals: List[str], common_rule: str = "", room_id: str = None) -> str: # room_idを追加
        """Run the agent on a list of goals."""

        self._set_disconnect_flag(False)

        print("\n"*50)

        # 各ゴールに対してサブタスクを実行
        for i, goal in enumerate(goals, 1):
            print(f"=== Processing Goal {i}/{len(goals)} ===")


            result = await self._run_subtask(goals, goal, common_rule, i, room_id) # room_idを追加
            if not result:
                error = f"Failed to complete goal {i}: {goal}"
                print(error)
                return error
            
            await self.event_manager.add_event(
                action="***PREVIOUS_GOAL_COMPLETED***",
                purpose="so GOAL were updated already !",
                result=goal[:max(len(goal), 30)] + "..." + "was completed !"
            )

            self.reset_count()
                
        success = "=== All goals completed successfully! ==="
        return success

    async def _run_subtask(self, goals: List[str], current_goal: str, common_rule: str, goal_index: int, room_id: str = None) -> str: # room_idを追加
        """Run a subtask for the agent."""
        room = self.room_manager.get_room(room_id)
        
        while not self.is_finish():  # 永続的なループ
            try:
                print(f"=== AutoGPT Run {goal_index}-{self.count}===")

                # Prepare input for AI
                input_dict = {
                    "goals": goals,
                    "current_goal": f"goal index: {goal_index}, {current_goal}",
                    "common_rule": common_rule,
                }

                # Get AI response using the new chain format
                assistant_reply = await self.chain.ainvoke(input_dict)


                # 応答形式の変更に対応
                response_text = (
                    assistant_reply.content 
                    if hasattr(assistant_reply, 'content') 
                    else assistant_reply
                )

                print(f"[DEBUG] response_text: \n{response_text}")

                # Parse response

                action = self.output_parser.parse(response_text)

                # Check for task completion
                if action.name == FINISH_NAME:
                    result = action.args.get("response", "Task completed")
                    await self._log("Task Completed:", result)
                    return result
                
                if action.name == "go_next":
                    result = action.args.get("response", "Task completed")
                    await self._log("Task Completed:", result)
                    return result
                

                try:
                        # assistant_reply.content は JSON文字列として返ってくるためパースが必要
                    parsed_response = json.loads(response_text)
                    purpose = parsed_response.get("thoughts", {}).get("text", "")

                    is_finish = string_to_bool(parsed_response.get("thoughts", {}).get("is_finish", "false"))
                    is_go_next = string_to_bool(parsed_response.get("thoughts", {}).get("is_go_next", "false"))
                except:
                    purpose = ""
                    is_finish = False
                    is_go_next = False

                # Return 
                if is_finish:
                    result = action.args.get("response", "Task completed")
                    await self._log("Task Completed:", result)
                    return result

                if is_go_next:
                    result = action.args.get("response", "Task completed")
                    await self._log("Task Completed:", result)
                    return "go_next"
                    
                print(f"[DEBUG] action.name: {action.name}")
                print(f"[DEBUG] action.args: {action.args}")

                result = await self._execute_tool(action.name, action.args, purpose)
                print(f"[DEBUG] result: {result}")

                self.add_count()
                
                    
            except Exception as e:
                error_msg = f"Error in subtask execution: {str(e)}"
                error_details = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "current_goal": current_goal
                }
                await self._log("ERROR", {"message": error_msg, "details": error_details})
                return error_msg
            
    def add_count(self):
        self.count += 1

    def reset_count(self):
        self.count = 0

    def _set_disconnect_flag(self, flag: bool):
        self.disconnect_flag = flag

    def finish(self):
        self._set_disconnect_flag(True)

    def is_finish(self):
        return self.disconnect_flag

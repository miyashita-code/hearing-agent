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

from .autogpt_prompt import AutoGPTPrompt

from ..communication import WebSocketManager


from .event_manager import Event
from utils import string_to_bool

load_dotenv()

class AutoGPT:
    """Autonomous agent system for chat-based interaction."""
    
    def __init__(
        self,
        ai_name: str,
        ai_role: str,
        tools: List[BaseTool],
        flag_names: List[str],
        llm: BaseChatModel,
        output_parser: Optional[BaseAutoGPTOutputParser] = None,
        chain: Optional[RunnableSequence] = None,
        verbose: bool = True,
        websocket_manager: WebSocketManager = None,
        room_id: str = None,
    ):
        self.room_id = room_id  
        self.websocket_manager = websocket_manager
        self.room = self.websocket_manager.get_room(self.room_id)

        self.ai_name = ai_name
        self.ai_role = ai_role
        self.tools = tools
        self.flag_names = flag_names
        self.flags_history : List[Dict[str, bool]] = []
        self.llm = llm
        self.output_parser = output_parser or AutoGPTOutputParser()
        self.chain = chain
        self.verbose = verbose
        self.count = 0
        
        self.disconnect_flag = False

        # Flag to guarantee to execute save_result at least once per one subgoal
        self._save_result_flag = False
        self.tools_dict = {t.name: t for t in self.tools}

    @classmethod
    def from_llm_and_tools(
        cls,
        ai_name: str,
        ai_role: str,
        tools: List[BaseTool],
        flag_names: List[str],
        llm: BaseChatModel,
        verbose: bool = True,
        websocket_manager: WebSocketManager = None,
        room_id: str = None,
    ) -> AutoGPT:
        """LLMとツールからAutoGPTインスタンスを作成"""
        output_parser = AutoGPTOutputParser()

        tools_dict = {t.name: t for t in tools}

        room = websocket_manager.get_room(room_id)

        if room is None:
            raise ValueError(f"Room not found for room_id: {room_id}")

        prompt = AutoGPTPrompt(
            verbose=verbose,
            ai_name=ai_name,
            ai_role=ai_role,
            tools=tools,
            input_variables=["goals", "current_goal", "common_rule", "flags"],
            token_counter=llm.get_num_tokens,

            # methods
            get_chat_history=room.message_manager.get_chat_history,
            get_event_history=room.event_manager.get_event_history,
            get_consecutive_message_number=room.message_manager.get_consecutive_message_number,
            get_is_new_response_from_user_came=room.message_manager.has_new_messages,
            get_summaries=room.result_manager.get_goal_result_pairs,
            get_plans=room.plan_manager.get_latest_plan,
            get_waiting_info=tools_dict["wait"].get_waiting_info if "wait" in tools_dict else None,
            )

        chain = prompt | llm

        return cls(
            ai_name=ai_name,
            ai_role=ai_role,
            tools=tools,
            flag_names=flag_names,
            llm=llm,
            output_parser=output_parser,
            chain=chain,
            verbose=verbose,
            websocket_manager=websocket_manager,
            room_id=room_id,
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
        
        # waitの情報をリセットする
        if tool_name != "wait":
            self.tools_dict["wait"].reset_waiting_info()

        # save_resultの場合は, 実行履歴を保存する
        if tool_name == "save_result":
            self.set_save_result_flag(True)
            
        tool = tools[tool_name]
        try:
            result = await tool._arun(**args)

            await self.room.event_manager.add_event(
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
            
            await self.room.event_manager.add_event(
                action="***PREVIOUS_GOAL_COMPLETED***",
                purpose="so GOAL were updated already !",
                result=goal[:max(len(goal), 30)] + "..." + "was completed !"
            )

            self.reset_count()
                
        success = "=== All goals completed successfully! ==="
        return success

    async def _run_subtask(self, goals: List[str], current_goal: str, common_rule: str, goal_index: int, room_id: str = None) -> str:
        """Run a subtask for the agent."""
        room = self.websocket_manager.get_room(room_id)
        print(f"\n[DEBUG] Room ID: {room_id}")
        print(f"[DEBUG] Room found: {room is not None}")

        # set flag as init planning mode
        self.set_flag("plan_action")
        print(f"\n[DEBUG] Initial flag set: plan_action{self.flags_history[-1]}")

        # set flag as save_result flag to False (yet not executed)
        self.set_save_result_flag(False)

        while not self.is_finish():
            try:
                print(f"\n=== AutoGPT Run {goal_index}-{self.count}===")

                # デバッグ: フラグの状態を確認
                flag_history = self.get_flag_history(1)
                print(f"\n[DEBUG] Flag History: {flag_history}")
                print(f"[DEBUG] Flag History Type: {type(flag_history)}")

                # Prepare input for AI
                input_dict = {
                    "goals": goals,
                    "current_goal": f"goal index: {goal_index}, {current_goal}",
                    "common_rule": common_rule,
                    "flags": flag_history if flag_history is not None else {},
                }


                # Get AI response using the new chain format
                assistant_reply = await self.chain.ainvoke(input_dict)
                print("\n[DEBUG] Assistant Reply received successfully")

                # 応答形式の変更に対応
                response_text = (
                    assistant_reply.content 
                    if hasattr(assistant_reply, 'content') 
                    else assistant_reply
                )

                print(f"\n[DEBUG] Response Text Type: {type(response_text)}")
                print(f"[DEBUG] response_text: \n{response_text}")

                # Parse response
                action = self.output_parser.parse(response_text)
                print(f"\n[DEBUG] Parsed Action: {action.name}")

                # Check for task completion
                if action.name == FINISH_NAME or action.name == "go_next":
                    if self._save_result_flag:
                        result = await self._execute_tool("save_result", {"goal": current_goal}, purpose="Before go to next, summarize this subgoal and save_result")
                        await self._log("Task Completed (automatically save_result, finished current task andgo to next):", result)
                    else:
                        result = action.args.get("response", "Task completed, finished current task and go to next")
                        await self._log("Task Completed:", result)
                    return result
                    
                    
                # 応答時の内部FLAGを参照して行動を強制する
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
                    result = await self._execute_tool("save_result", args={"goal": current_goal}, purpose="Before go to next, summarize this subgoal and save_result")
                    await self._log("Task Completed (automatically save_result):", result)
                    self.set_flag("finish")

                elif is_go_next:
                    result = await self._execute_tool("save_result", args={"goal": current_goal}, purpose="Before go to next, summarize this subgoal and save_result")
                    await self._log("Task Completed (automatically save_result):", result)
                    self.set_flag("go_next")

                else:
                    print(f"[DEBUG] action.name: {action.name}")
                    print(f"[DEBUG] action.args: {action.args}")

                    result = await self._execute_tool(action.name, action.args, purpose)
                    print(f"[DEBUG] result: {result}")

                    # set flag as all false
                    if action.name == "plan_action" and self.get_count() == 0:
                        # 初回のPLANINGをした後に返信をし忘れないようにFLAGを設定
                        self.set_flag("reply_message")
                    else:
                        self.set_flag("na")

                self.add_count()
                
                    
            except Exception as e:
                print(f"\n[DEBUG] Error in subtask execution:")
                print(f"Error Type: {type(e)}")
                print(f"Error Message: {str(e)}")
                print("Stack Trace:")
                import traceback
                traceback.print_exc()
                raise
            
    def add_count(self):
        self.count += 1

    def reset_count(self):
        self.count = 0

    def get_count(self):
        return self.count

    def _set_disconnect_flag(self, flag: bool):
        self.disconnect_flag = flag

    def finish(self):
        self._set_disconnect_flag(True)

    def is_finish(self):
        return self.disconnect_flag
    
    def set_flag(self, flag_name: str):
        def _get_base_flags():
            return {flag_name: False for flag_name in self.flag_names}
            
        new_flags = _get_base_flags()

        if flag_name in self.flag_names:
            new_flags[flag_name] = True

        self.flags_history.append(new_flags)

    def get_flag_history(self, prev_index: int):
        try:
            return self.flags_history[len(self.flags_history) - prev_index]
        except IndexError:
            return None
        
    def set_save_result_flag(self, flag: bool):
        self._save_result_flag = flag



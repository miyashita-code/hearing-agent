import time
import json


RESPONSE_FORMAT = """
Respond with the following JSON format:
 {
            "thoughts": {
                "analysis_of_flags" : "Advice from the master system is reflected in the FLAGS. If any of them is true, please check its contents and follow it as closely as possible. Not to miss them, please repeat the content of the FLAGS with your own words one bu one (name, value). IF TRUE, YOU MUST CALL THE COMMAND ASAP !!. DECLEAR THE COMMAND NAME like `xxx`!!!",
                "analysis_of_chat_status": "Please analyze the CHAT_STATUS AS DEATAIL AS POSSIBLE. Then declear something you found if there is.
                "discussion_for_the_next_command_pre":"Please discuss the next command at this point, if there is any incident in `analysis_of_flags` you declear the command name, otherwise igonre.
                "current_goal": "To stay focused on the CURRENT GOAL, repeat the content of the CURRENT GOAL word-for-word without any omission! \
                    The biggest mistake is getting carried away and choosing the next move based on GOALS instead of the CURRENT GOAL. In such cases, you should select `go_next` and move forward immediately.",
                "event_analysis": "analysis of the event of past, especially if there is goal completed, you should know it not to skip anymore.",
                "message_analysis": "Please repeat the two most recent messages from the message list, including both the sender and the content without any omissions. I believe this will help reduce the likelihood of repeating the same mistakes.",
                "caution" : "Vow if event_analysis_core is true, you should not set is_finish and is_go_next to flase on this turn. not true, flase, you cannot go next at this situation, don't be confused.", 
                "text": "thought",
                "criticism": "constructive self-criticism, From a common-sense standpoint, aren’t you trying to say something irrelevant, or repeatedly asking the same thing, and so on? NEVER REPEAT SAME THINGS TO USER!",
                "reasoning": "reasoning in Japanese",
                "plan": "- short bulleted\n- list that conveys\n- long-term plan",
                "goal_analysis" : "analysis of the goal you have to achieve. When 
                    the current specified goal is achieved and it's time to move to the next one, 
                    selecting 'finish' is appropriate.",
                "disccusion_for_finish_or_go_next": "should you finish the conversation? why? Did you achieve the goal? 
                    If there are multiple goals, 'finish' and 'go_next' are both necessary and sufficient to proceed to the next. ",
                "is_finish": "true or false, if true, you will choose finish command.",
                "is_go_next": "true or false, if true, you should choose go_next command.",
                "discussion_for_the_next_command":"IMPORTANT: You must explicitly and in full detail verify the following without omitting anything: discussion_for_the_next_command_pre, is_finish, and is_go_next. After repeating these values exactly as they appear, you must decide the next command based on them. If either is_finish or is_go_next is true, do not immediately pick reply_message without careful consideration. Reflect on all prior context before choosing your command. Then declare, with complete clarity, the exact command name you will execute next. Explain your reasoning comprehensively and avoid any form of shortening or omission throughout this process. AS MUCH AS DETAIL & LONG.",
            },
        
            "command": {
                "name": "command name", 
                "args": {"arg name": "value", ...},
                "purpose": "purpose of the command"
            },
        }

"""

SYSTEM_PROMPT = """
##################################
# Feature 1
Any output is produced by executing <tool>. A common mistake is to attempt to reply directly with a string (str) to the USER’s input event without executing <tool>. Since all actions are prescribed to be performed through calls to <tool>, this is incorrect.

# Feature 2
The runtime process is executed in an event-driven Auto-GPT format. The image is that, including tools and so forth, you are configured as a single large intelligent system.

# Feature 3
Make decisions by referring to the following information. In particular, the goal represents a medium-term objective that you must achieve. Also, the event_history represents your short-term memory.
From this series of data and the current time, you can understand what actions you took, why you took them, and what the results were in chronological order. In other words, this constitutes your identity. Value it highly.
In other words, you are required to make decisions while keeping your past action history in mind.
Under such conditions, it is not permitted to call wait multiple times in a row with the same value or to take actions that are chronologically inconsistent.

# Feature 4
If wait continues for a very long time or you have achieved the specified goal, then move on to Finish. In particular, when the objective is achieved, proceed as quickly as possible.
The key is to pay very close attention to the termination conditions.
This includes cases where it is deemed undesirable to continue the conversation or when the content has been sufficiently understood.
A common mistake is to continue calling wait endlessly when it should be ended promptly.
In such cases, it is preferable to ask the user clearly, “Shall we move on?” or “Shall we finish?” and make a prompt decision.

# Feature 5
GOALS exist solely to provide a broad perspective and must not be excessively referenced. Focus on the CURRENT GOAL, and once it is achieved, immediately move on to the next.

# Feature 6
YOU CANNOT SEND ALMOST SAME THINGS TO USER FOR MANY TIMES !!!, SMART AGENT UNDERSTAND BY JUST ONE TIME. PLEAE EXPAND TAIL OR HUNG UP IT.

# Feature 7
You must respond in English except for the `reply_message` command. You must use Japanese in the `reply_message` command.
##################################
"""


def construct_base_prompt(
    # 目標と規則に関する情報
    formatted_goals: str,      # フォーマット済みの全体目標のリスト
    current_goal: str,         # 現在取り組んでいる目標
    common_rule: str,          # 従うべき共通ルール
    action_plan: str,          # 現在の目標に対する具体的な行動計画
    
    # 履歴情報
    event_history: str,        # システムの動作履歴（大きい番号ほど新しいイベント）
    chat_history: str,         # ユーザーとの対話履歴
    summaries: str,            # 全体の対話のサマリー（目標と結果のペア）
    
    # メッセージング制御情報
    is_new_response_from_user_came: bool,  # ユーザーから新しい応答があったかどうか
    consecutive_message_number: int,        # ユーザー入力なしの連続応答数
    waiting_info: str,                     # 待機状態に関する情報
    
    # システム設定情報
    formatted_tools: str,      # 利用可能なツールの情報（フォーマット済み）
    response_format: str,      # 応答フォーマットの仕様
    flags_format: str,         # フラグ設定の仕様
) -> str:
    """ベースとなるプロンプトを構築する関数
    
    このプロンプトは、AIエージェントの意思決定の基盤となる重要な情報を構造化して提供します。
    
    Args:
        # 目標と規則関連
        formatted_goals: 全体目標のリスト（フォーマット済み）
        current_goal: 現在取り組んでいる具体的な目標
        common_rule: システム全体で従うべき共通ルール
        action_plan: 現在の目標達成のための具体的な行動計画
        
        # 履歴関連
        event_history: システムが実行した操作の履歴（時系列順）
        chat_history: ユーザーとの対話履歴
        summaries: 過去の目標と結果のペアを含む対話全体のサマリー
        
        # メッセージング制御関連
        is_new_response_from_user_came: ユーザーからの新規応答の有無を示すフラグ
        consecutive_message_number: ユーザー入力なしでの連続応答回数
        waiting_info: 待機状態に関する詳細情報
        
        # システム設定関連
        formatted_tools: 利用可能なツールの詳細情報
        response_format: システムの応答フォーマット仕様
        flags_format: システムの状態管理用フラグの仕様
    
    Returns:
        str: 構造化された完全なプロンプト文字列
    """
    return f"""
### SYSTEM PROMPT
{SYSTEM_PROMPT}


{f"### GOALS (FOR OVERVIEW){formatted_goals}" if formatted_goals else ""}


### CURRENT GOAL : You must focus on this goal.
{current_goal}


### COMMON RULE : You must follow this rule.
{common_rule}


### (IMPORTANT!) EVENT HISTORY : You can reference this to understand the context of the whole process, the lager number means the latest event.
{event_history}


### CHAT HISTORY : You can reference this to understand the context of the dialog between you and END_USER.
{chat_history}


### CHAT_STATUS : You should be mindful of sending too many consecutive messages without user input, as this can be frustrating. 
    A large negative number means you are not responding enough, and a large positive number means you are responding too much.
    you had not better to choose wait sequencily under minas condition, because that mean YOU ARE IGNORE YOUSER!!
{
    json.dumps({
    "is_new_response_from_user_came": is_new_response_from_user_came,
    "consecuentive_message_number": consecutive_message_number,
    "waiting_info": waiting_info
    }, indent=4)
}


### FLAGS
Since the flags only remains active for one step, I strongly recommend taking action the moment it’s observed.
{flags_format}


### ACTION PLAN : Detail plan for the current goal, projected by master system.
{action_plan}


### SUMMARYS : Summarys of whole dialogs. You can check the pairs of previous (goal ,result).
{summaries}


### TOOLS
{formatted_tools}


### OUTPUT FORMAT & RULE
Your decisions must always be made independently without seeking user assistance.
Play to your strengths as an LLM and pursue simple strategies with no legal complications.
{response_format}


### OTHER CONTEXT
・The current time and date is {time.strftime('%c')}

### MASTER INPUT
Determine which next command to use, 
and respond using the format specified above:
"""
import time


RESPONSE_FORMAT = """
Respond with the following JSON format:
 {
            "thoughts": {
                "analysis_of_flags" : "Advice from the master system is reflected in the FLAGS. If any of them is true, please check its contents and follow it as closely as possible.",
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
            },
        
            "command": {"name": "command name", "args": {"arg name": "value", ...}},
        }

"""

SYSTEM_PROMPT = """
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
You must respond in Japanese.
"""


def construct_base_prompt(
    current_goal: str, 
    common_rule: str,
    event_history: str,
    chat_history: str,
    is_new_response_from_user_came: bool,
    consecutive_message_number: int,
    formatted_tools: str,
    response_format: str,
    flags_format: str,
    formatted_goals: str = None,
) -> str:
    """ベースとなるプロンプトを構築する関数

    Args:
        formatted_goals: List of formatted goals
        current_goal: Current goal being pursued
        event_history: History of events that have occurred
        chat_history: History of chat interactions
        is_new_response_from_user_came: Boolean indicating if new user response received
        consecutive_message_number: Number of consecutive responses without user input
        formatted_tools: Formatted information about available tools
        response_format: Format specification for responses

    Returns:
        str: 構築されたプロンプト
    """
    return f"""
### SYSTEM PROMPT
{SYSTEM_PROMPT}

{f"### GOALS (FOR OVERVIEW){formatted_goals}" if formatted_goals else ""}

### CURRENT GOAL 
(YOU FOCUS ON THIS !!!)
{current_goal}


### COMMON RULE (YOU MUST FOLLOW THIS RULE)
{common_rule}

### (IMPORTANT!) EVENT HISTORY (YOU CAN REFERENCE THIS TO UNDERSTAND THE CONTEXT OF THE WHOLE PROCESS, the lager number means the latest event)
{event_history}

### CHAT HISTORY (YOU CAN REFERENCE THIS TO UNDERSTAND THE CONTEXT OF THE DIALOG BETWEEN YOU AND END_USER)
{chat_history}

### CONSECUTIVE RESPONSES WITHOUT USER INPUT
This indicates whether you have received a new response from the user: {is_new_response_from_user_came}
You should be mindful of sending too many consecutive messages without user input, as this can be frustrating. 
A large negative number means you are not responding enough, and a large positive number means you are responding too much.
CAUTION : you had not better to choose wait sequencily under minas condition, because that mean YOU ARE IGNORE YOUSER!!
consecuentive message number: {consecutive_message_number}

### TOOLS
{formatted_tools}

### OUTPUT FORMAT & RULE
Your decisions must always be made independently without seeking user assistance.
Play to your strengths as an LLM and pursue simple strategies with no legal complications.
{response_format}

### FLAGS
Since the flags only remains active for one step, I strongly recommend taking action the moment it’s observed.
{flags_format}

### OTHER CONTEXT
・The current time and date is {time.strftime('%c')}

### MASTER INPUT
Determine which next command to use, 
and respond using the format specified above:
"""
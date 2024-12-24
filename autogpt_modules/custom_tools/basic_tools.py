from typing import Type
from langchain.tools.base import BaseTool


from langchain.tools import BaseTool




"""
以下のツールも同様に実装予定:

・replay_message(str)
    LINE上でUSERにMESSAGEを直接送信する関数。基本的には、ここを通してのみUSREに作用を及ぼせる。
    端的で明るい文章が好まれる。最も基本的な関数の一つ。同じ内容を連続して送信することは許されない、そういう時はスタンプを送信したほうが印象が良い。

・replay_message_with_stamp(index)
    LINE上でUSERにスタンプを送信する関数。0で"のぞき見"スタンプを送ることが出来る、それ以外は用意されていない。
    Userからの返信を期待する場面でなかなか返事が来ない時に送るとよい。

・search_longterm_memory(question : str)
    Userとの会話にパーソナライズされた汎用RAGで長期記憶を検索できる。
    小まめに確認して、Userとのコンテキストを適切に反映して親近感を演出しよう。

・save_longterm_memory(str)
    Userとの会話にパーソナライズされた汎用RAGに長期記憶として所望の情報を保存できる。
    些細な情報も小まめに保存することが大切。

・wait(minute : int)
    Userは実生活の中であなたに返信をするので、すぐには返答が来ないこともある。
    この関数はself.setIsWaiting(true)を実行したうえで、minute後にwaited eventを発火。

・pander_dialog_state(goal_of_dialog_analyze : str, dialog_data : str)
    対話状態を分析し、���り良い指示を行うための情報を提供。
    ユーザーの状態や心理状態を理解するのに役立つ。

・updata_instructions(instruction_text : str)
    会話をより良くするために指示を更新。
    指示は日本語で、意図を明確に示す必要がある。

・do_nothing_and_wait(is_wait_until_dialog_updated : bool)
    何もせずに待機。dialog_updatedがTrueの場合、
    対話の更新を待つ。
"""
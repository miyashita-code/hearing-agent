import os
from typing import Optional, List, TypeVar, Generic, Union
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import Generation, LLMResult
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from .prompt import (
    plan_prompt,
    summary_prompt,
)
from dotenv import load_dotenv

load_dotenv()

T = TypeVar('T')

class LLMResponse(Generic[T]):
    """LLMの応答を表す型"""
    def __init__(self, content: T):
        self.content = content

def get_llm(model_name: str) -> BaseChatModel:
    """LLMモデルを取得する

    Args:
        model_name (str): モデル名

    Returns:
        BaseChatModel: LLMモデル
    """
    if model_name.startswith(("gpt", "chatgpt")):
        return ChatOpenAI(
            model_name=model_name,
            temperature=0.7,
            streaming=True
        )
    else:
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0.7,
            convert_system_message_to_human=True
        )

def get_plan_chain():
    """プラン生成チェーンを取得する
    
    チェーンは以下の処理を順に行う：
    1. プロンプトテンプレートによるメッセージの構築
    2. LLMによる応答の生成
    3. 応答の文字列への変換

    Returns:
        Chain: プラン生成チェーン
    """
    model = get_llm(os.getenv("PLAN_ACTION_MODEL"))
    return plan_prompt | model | StrOutputParser()

def get_summary_chain():
    """要約生成チェーンを取得する
    
    チェーンは以下の処理を順に行う：
    1. プロンプトテンプレートによるメッセージの構築
    2. LLMによる応答の生成
    3. 応答の文字列への変換

    Returns:
        Chain: 要約生成チェーン
    """
    model = get_llm(os.getenv("SUMMARY_MODEL"))
    return summary_prompt | model | StrOutputParser()

def _extract_text_from_llm_response(response: Union[str, LLMResult, Generation]) -> str:
    """LLMの応答から文字列を抽出する

    Args:
        response (Union[str, LLMResult, Generation]): LLMの応答

    Returns:
        str: 抽出された文字列
    """
    if isinstance(response, str):
        return response
    elif isinstance(response, LLMResult):
        return response.generations[0][0].text
    elif isinstance(response, Generation):
        return response.text
    else:
        raise ValueError(f"Unsupported response type: {type(response)}")

async def generate_plan(
    goal: str,
    context: str,
    past_results: str,
    history: Optional[List[BaseMessage]] = None
) -> str:
    """プランを生成する

    Args:
        goal (str): 目標
        context (str): コンテキスト
        past_results (str): 過去の実行結果
        history (Optional[List[BaseMessage]], optional): チャット履歴. Defaults to None.

    Returns:
        str: 生成されたプラン
    
    Raises:
        ValueError: 入力が不正な場合
        RuntimeError: LLM呼び出しに失敗した場合
    """
    if not goal or not context:
        raise ValueError("goal と context は必須です")

    try:
        chain = get_plan_chain()
        result = await chain.ainvoke({
            "goal": goal,
            "context": context,
            "past_results": past_results,
            "history": history or []
        })
        print(f"[debug] action plan: {result}")
        return _extract_text_from_llm_response(result)
    except Exception as e:
        raise RuntimeError(f"プラン生成に失敗しました: {str(e)}") from e

async def generate_summary(
    goal: str,
    chat_history: str,
    history: Optional[List[BaseMessage]] = None
) -> str:
    """要約を生成する

    Args:
        goal (str): 目標
        chat_history (str): チャット履歴
        history (Optional[List[BaseMessage]], optional): チャット履歴. Defaults to None.

    Returns:
        str: 生成された要約
    
    Raises:
        ValueError: 入力が不正な場合
        RuntimeError: LLM呼び出しに失敗した場合
    """
    if not goal or not chat_history:
        raise ValueError("goal と chat_history は必須です")

    try:
        chain = get_summary_chain()
        result = await chain.ainvoke({
            "goal": goal,
            "chat_history": chat_history,
            "history": history or []
        })

        print(f"[debug] result: {result}")
        return _extract_text_from_llm_response(result)
    except Exception as e:
        raise RuntimeError(f"要約生成に失敗しました: {str(e)}") from e

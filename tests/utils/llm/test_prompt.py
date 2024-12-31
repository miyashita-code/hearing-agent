import os
import pytest
from langchain_core.messages import SystemMessage, HumanMessage

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autogpt_modules.utils.llm import (
    plan_prompt,
    summary_prompt,
    PLAN_SYSTEM_TEMPLATE,
    SUMMARY_SYSTEM_TEMPLATE,
    PLAN_HUMAN_TEMPLATE,
    SUMMARY_HUMAN_TEMPLATE
)

@pytest.fixture
def mock_chat_history():
    """チャット履歴のモックデータ"""
    return [
        {"role": "user", "content": "タスクを開始します"},
        {"role": "assistant", "content": "了解しました"},
        {"role": "user", "content": "進捗を確認したいです"},
        {"role": "assistant", "content": "現在の進捗は80%です"}
    ]

@pytest.fixture
def mock_past_results():
    """過去の結果のモックデータ"""
    return [
        {
            "goal": "テストゴール1",
            "result": "テスト結果1の要約"
        },
        {
            "goal": "テストゴール2",
            "result": "テスト結果2の要約"
        }
    ]

def test_plan_prompt_templates():
    """プランプロンプトテンプレートの検証"""
    # システムプロンプトの検証
    assert "プランニング" in PLAN_SYSTEM_TEMPLATE
    assert "目標の分析" in PLAN_SYSTEM_TEMPLATE
    assert "実行ステップ" in PLAN_SYSTEM_TEMPLATE
    
    # ユーザープロンプトの検証
    assert "{goal}" in PLAN_HUMAN_TEMPLATE
    assert "{context}" in PLAN_HUMAN_TEMPLATE
    assert "{past_results}" in PLAN_HUMAN_TEMPLATE

def test_summary_prompt_templates():
    """要約プロンプトテンプレートの検証"""
    # システムプロンプトの検証
    assert "要約" in SUMMARY_SYSTEM_TEMPLATE
    assert "目標の達成状況" in SUMMARY_SYSTEM_TEMPLATE
    assert "主要な成果" in SUMMARY_SYSTEM_TEMPLATE
    
    # ユーザープロンプトの検証
    assert "{goal}" in SUMMARY_HUMAN_TEMPLATE
    assert "{chat_history}" in SUMMARY_HUMAN_TEMPLATE

def test_plan_prompt_format():
    """プラン生成プロンプトのフォーマットテスト"""
    goal = "テストゴール"
    context = "テストコンテキスト"
    past_results = "過去の結果1\n過去の結果2"
    history = []

    messages = plan_prompt.format_messages(
        goal=goal,
        context=context,
        past_results=past_results,
        history=history
    )

    assert len(messages) >= 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[-1], HumanMessage)

    system_message = messages[0].content
    human_message = messages[-1].content

    assert "プランニング" in system_message
    assert "目標の分析" in system_message
    assert "実行ステップ" in system_message
    assert f"目標: {goal}" in human_message
    assert f"コンテキスト: {context}" in human_message
    assert past_results in human_message

def test_summary_prompt_format():
    """要約生成プロンプトのフォーマットテスト"""
    goal = "テストゴール"
    chat_history = "ユーザー: こんにちは\nアシスタント: はい"
    history = []

    messages = summary_prompt.format_messages(
        goal=goal,
        chat_history=chat_history,
        history=history
    )

    assert len(messages) >= 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[-1], HumanMessage)

    system_message = messages[0].content
    human_message = messages[-1].content

    assert "要約" in system_message
    assert "目標の達成状況" in system_message
    assert "主要な成果" in system_message
    assert f"目標: {goal}" in human_message
    assert chat_history in human_message

def test_prompt_variable_validation():
    """プロンプト変数のバリデーションテスト"""
    with pytest.raises(KeyError):
        plan_prompt.format_messages()

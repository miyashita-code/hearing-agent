import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.outputs import Generation, LLMResult
from autogpt_modules.utils.llm.llm_chains import (
    get_llm,
    get_plan_chain,
    get_summary_chain,
    generate_plan,
    generate_summary,
)

@pytest.fixture
def mock_past_results():
    return [
        {"goal": "テストゴール1", "result": "テスト結果1の要約"},
        {"goal": "テストゴール2", "result": "テスト結果2の要約"}
    ]

@pytest.fixture
def mock_chat_history():
    return [
        {"content": "タスクを開始します", "role": "user"},
        {"content": "了解しました", "role": "assistant"},
        {"content": "進捗を確認したいです", "role": "user"},
        {"content": "現在の進捗は80%です", "role": "assistant"}
    ]

def test_get_llm_gpt():
    """GPTモデル取得のテスト"""
    with patch("autogpt_modules.utils.llm.llm_chains.ChatOpenAI") as mock_chat:
        mock_instance = MagicMock()
        mock_instance.model_name = "gpt-4"
        mock_chat.return_value = mock_instance
        
        llm = get_llm("gpt-4")
        assert llm.model_name == "gpt-4"
        mock_chat.assert_called_once_with(
            model_name="gpt-4",
            temperature=0.7,
            streaming=True
        )

def test_get_llm_gemini():
    """Geminiモデル取得のテスト"""
    with patch("autogpt_modules.utils.llm.llm_chains.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_instance.model_name = "models/gemini-exp-1206"
        mock_chat.return_value = mock_instance
        
        llm = get_llm("gemini-exp-1206")
        assert llm.model_name == "models/gemini-exp-1206"
        mock_chat.assert_called_once_with(
            model="gemini-exp-1206",
            temperature=0.7,
            convert_system_message_to_human=True
        )

def test_get_plan_chain():
    """プラン生成チェーン取得のテスト"""
    with patch("autogpt_modules.utils.llm.llm_chains.get_llm") as mock_get_llm:
        chain = get_plan_chain()
        assert chain is not None
        mock_get_llm.assert_called_once_with("gemini-exp-1206")

def test_get_summary_chain():
    """要約生成チェーン取得のテスト"""
    with patch("autogpt_modules.utils.llm.llm_chains.get_llm") as mock_get_llm:
        chain = get_summary_chain()
        assert chain is not None
        mock_get_llm.assert_called_once_with("gemini-exp-1206")

@pytest.mark.asyncio
async def test_generate_plan_input_format(mock_past_results):
    """プラン生成の入力フォーマット��スト"""
    goal = "テストゴール"
    context = "テストコンテキスト"
    past_results = "\n".join([
        f"ゴール: {r['goal']}\n結果: {r['result']}\n"
        for r in mock_past_results
    ])

    with patch("autogpt_modules.utils.llm.llm_chains.get_plan_chain") as mock_get_chain:
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value="テストプラン")
        mock_get_chain.return_value = mock_chain

        result = await generate_plan(
            goal=goal,
            context=context,
            past_results=past_results,
        )
        assert result == "テストプラン"
        mock_chain.ainvoke.assert_called_once_with({
            "goal": goal,
            "context": context,
            "past_results": past_results,
            "history": []
        })

@pytest.mark.asyncio
async def test_generate_summary_input_format(mock_chat_history):
    """要約生成の入力フォーマットテスト"""
    goal = "テストゴール"
    chat_history = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in mock_chat_history
    ])

    with patch("autogpt_modules.utils.llm.llm_chains.get_summary_chain") as mock_get_chain:
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value="テスト要約")
        mock_get_chain.return_value = mock_chain

        result = await generate_summary(
            goal=goal,
            chat_history=chat_history,
        )
        assert result == "テスト要約"
        mock_chain.ainvoke.assert_called_once_with({
            "goal": goal,
            "chat_history": chat_history,
            "history": []
        })

@pytest.mark.asyncio
async def test_generate_plan_validation():
    """プラン生成の入力バリデーションテスト"""
    with pytest.raises(ValueError):
        await generate_plan("", "context", "past_results")
    
    with pytest.raises(ValueError):
        await generate_plan("goal", "", "past_results")

@pytest.mark.asyncio
async def test_generate_summary_validation():
    """要約生成の入力バリデーションテスト"""
    with pytest.raises(ValueError):
        await generate_summary("", "chat_history")
    
    with pytest.raises(ValueError):
        await generate_summary("goal", "")

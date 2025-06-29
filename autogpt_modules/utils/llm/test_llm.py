import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import aiohttp
import json

load_dotenv()

async def test_openai_connection():
    """OpenAI APIの接続テスト"""
    try:
        llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",  # 基本的なモデルで試験
            temperature=0.7,
            streaming=False,
            request_timeout=30
        )
        
        result = await llm.ainvoke("こんにちは。簡単なテストメッセージです。")
        print("=== OpenAI API テスト結果 ===")
        print(f"応答: {result.content}")
        print("OpenAI APIは正常に動作しています")
        return True
    except Exception as e:
        print("=== OpenAI API エラー ===")
        print(f"エラータイプ: {type(e)}")
        print(f"エラーメッセージ: {str(e)}")
        return False

async def test_gemini_connection():
    """Gemini APIの接続テスト"""
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7
        )
        
        result = await llm.ainvoke("こんにちは。簡単なテストメッセージです。")
        print("=== Gemini API テスト結果 ===")
        print(f"応答: {result.content}")
        print("Gemini APIは正常に動作しています")
        return True
    except Exception as e:
        print("=== Gemini API エラー ===")
        print(f"エラータイプ: {type(e)}")
        print(f"エラーメッセージ: {str(e)}")
        return False

async def test_deepseek_connection():
    """Deepseek APIの接続テスト"""
    try:
        llm = ChatOpenAI(
            temperature=0, 
            model=os.getenv("BASE_MODEL"), 
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            streaming=True,
            base_url=os.getenv("DEEPSEEK_BASE_URL")
        ).bind(
            response_format={"type": "json_object"}
        )
        
        result = await llm.ainvoke("テストメッセージです。JSONで応答してください。")
        print("=== Deepseek API テスト結果 ===")
        print(f"応答: {result.content}")
        print("Deepseek APIは正常に動作しています")
        return True
    except Exception as e:
        print("=== Deepseek API エラー ===")
        print(f"エラータイプ: {type(e)}")
        print(f"エラーメッセージ: {str(e)}")
        return False

async def run_test():
    """APIテストを実行"""
    print("APIテストを開始します...")
    
    # 環境変数の確認
    print("\n=== 環境変数の確認 ===")
    print(f"DEEPSEEK_API_KEY: {'設定されています' if os.getenv('DEEPSEEK_API_KEY') else '設定されていません'}")
    print(f"DEEPSEEK_BASE_URL: {os.getenv('DEEPSEEK_BASE_URL', 'デフォルトURLを使用')}")
    print(f"BASE_MODEL: {os.getenv('BASE_MODEL', 'モデルが設定されていません')}")
    
    # Deepseekテスト
    print("\nDeepseek APIをテストします...")
    result = await test_deepseek_connection()
    
    # 総合結果
    print("\n=== テスト総合結果 ===")
    print(f"Deepseek API: {'成功 ✅' if result else '失敗 ❌'}")

if __name__ == "__main__":
    asyncio.run(run_test()) 
import pytest
import os
import sys
from pathlib import Path

# プロジェクトルートへのパスを取得
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """環境変数のモック"""
    # OpenAI
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    
    # Google Cloud
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-api-key")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-api-key")
    
    # Model settings
    monkeypatch.setenv("PLAN_ACTION_MODEL", "gpt-3.5-turbo")  # テスト用にGPTモデルを使用
    monkeypatch.setenv("SUMMARY_MODEL", "gpt-3.5-turbo")      # テスト用にGPTモデルを使用

@pytest.fixture(scope="session", autouse=True)
def setup_path():
    """テスト実行前にPythonパスを設定"""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT)) 
# Hearing Agent - 認知症患者のための自律的対話支援システム

## 🌟 概要

Hearing Agentは、認知症患者の日常生活における手続き記憶（IADL: Instrumental Activities of Daily Living）をドキュメント化し、支援するための自律的な対話システムです。AutoGPTの設計思想に基づき、**JSONで定義されたゴールに従って自律的にワークフローを実行**する革新的なアーキテクチャを採用しています。

### 🎯 設計思想

本システムの中核となる設計思想は以下の3つです：

1. **ゴール駆動型自律エージェント**
   - JSONフォーマットでゴールを定義すると、エージェントが自律的にタスクを分解・実行
   - 各ステップは独立したモジュールとして機能し、再利用可能

2. **ReActパターンによる思考と行動の統合**
   - Reasoning（推論）とActing（行動）を組み合わせた意思決定
   - 各行動の前に明確な理由付けを行い、透明性の高い処理を実現

3. **フラグベース制御システム**
   - `finish`, `go_next`, `plan_action`, `reply_message`などのフラグで柔軟な制御
   - 状況に応じた動的な行動選択が可能

## 🏗️ アーキテクチャ

```
hearing-agent/
├── autogpt_modules/          # AutoGPTコアモジュール
│   ├── core/                 # エージェントの中核実装
│   │   ├── auto_gpt.py      # メインエージェントロジック
│   │   ├── room.py          # セッション管理
│   │   └── event_manager.py # イベント駆動処理
│   ├── communication/        # 通信層
│   │   ├── websocket_manager.py
│   │   ├── message_manager.py
│   │   └── plan_manager.py
│   └── tools/               # エージェントツール群
│       ├── reply_message.py
│       ├── wait.py
│       ├── plan_action.py
│       └── save_result.py
├── hearing_module/          # ヒアリング特化モジュール
│   └── goals.py            # 5段階インタビュープロセス
└── main.py                 # FastAPIサーバー
```

## 💡 核心的な実装詳細

### ゴール定義の例

```python
hearing_goals = {
    "plan_details": [
        {
            "step_name": "対象行動の特定",
            "step_index": 1,
            "purpose": "どのIADLをマニュアル化したいかを特定",
            "key_point": "複数回の対話を通じて明確化",
            "details": {
                "approach": "オープンな質問から始めて段階的に具体化",
                "example_questions": [
                    "どのような活動でお困りですか？",
                    "具体的にどの部分が難しいと感じますか？"
                ],
                "completion_criteria": "具体的な行動が1つ特定される"
            }
        },
        # ... 他のステップ
    ],
    "common_rules": {
        "overview": "全体進行における基本的なルール",
        "rules": [
            "段階的詳細化を重視",
            "相手のペースに合わせる",
            "専門用語を避ける"
        ]
    }
}
```

### 自律的実行の仕組み

```python
# AutoGPTインスタンスの作成
autogpt = AutoGPT.from_llm_and_tools(
    ai_name="認知症サポーター",
    ai_role="認知症患者の生活支援エージェント",
    tools=[ReplyMessage(), Wait(), PlanAction(), SaveResult()],
    flag_names=["finish", "go_next", "plan_action", "reply_message"],
    llm=llm
)

# ゴールに基づく自律実行
await autogpt.run(
    goals=[dict_to_string(goal) for goal in hearing_goals["plan_details"]],
    common_rule=dict_to_string(hearing_goals["common_rules"])
)
```

## 🚀 クイックスタート

### 環境設定

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/hearing-agent.git
cd hearing-agent

# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを編集して必要なAPIキーを設定
```

### 起動方法

```bash
# 開発サーバーの起動
python main.py

# または、プロダクション環境での起動
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔧 開発者向け情報

### テストの実行

```bash
# 全テストの実行
python -m pytest tests/ -v

# カバレッジレポート付き
python -m pytest tests/ --cov=autogpt_modules --cov-report=html
```

### 新しいツールの追加

1. `autogpt_modules/tools/`に新しいツールクラスを作成
2. `@tool`デコレータを使用してツールとして登録
3. `main.py`のツールリストに追加

```python
from autogpt_modules.tools.decorators import tool

@tool
class CustomTool:
    name = "custom_tool"
    description = "カスタムツールの説明"
    
    async def _run(self, input_data: str) -> str:
        # ツールのロジックを実装
        return "処理結果"
```

### WebSocket通信プロトコル

```javascript
// クライアント → サーバー
{
    "type": "start_hearing",  // セッション開始
    "data": {}
}

{
    "type": "message",        // ユーザーメッセージ
    "data": {
        "content": "ユーザーの入力"
    }
}

// サーバー → クライアント
{
    "type": "agent_message",
    "data": {
        "content": "エージェントの応答"
    }
}

{
    "type": "plan_update",
    "data": {
        "current_step": 2,
        "total_steps": 5,
        "description": "現在のステップ説明"
    }
}
```

## 🎨 モジュール性と拡張性

本システムの最大の特徴は、**他のタスクへの応用が容易**なモジュール設計です：

1. **ゴール定義の変更だけで新しいワークフローに対応**
   - 医療問診、カスタマーサポート、教育など様々な領域に適用可能

2. **ツールの組み合わせによる機能拡張**
   - 既存ツールの組み合わせで複雑な処理を実現
   - 新規ツールの追加も容易

3. **LLMモデルの切り替え**
   - OpenAI GPT、Google Gemini、DeepSeekなど複数のLLMに対応
   - 環境変数で簡単に切り替え可能

## 📊 パフォーマンスと最適化

- **非同期処理**: FastAPIとasyncioによる高速レスポンス
- **ストリーミング対応**: リアルタイムな応答生成
- **セッション管理**: Room単位での効率的なリソース管理
- **イベント駆動**: 必要な時だけ処理を実行

## 🤝 コントリビューション

プルリクエストを歓迎します！以下のガイドラインに従ってください：

1. Issueを作成して変更内容を説明
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

- AutoGPTプロジェクトチーム - 革新的なエージェントアーキテクチャの提供
- LangChainコミュニティ - 強力なLLM統合フレームワーク
- Re-MENTIAプロジェクトチーム - 認知症ケアへの深い洞察

---

**注意**: このシステムは認知症患者の支援を目的としていますが、医療行為の代替ではありません。専門的な医療アドバイスが必要な場合は、必ず医療従事者にご相談ください。

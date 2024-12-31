from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage

# プラン生成用のプロンプトテンプレート
PLAN_SYSTEM_TEMPLATE = """あなたは高度なプランニングAIアシスタントです。
与えられたゴールに対して、以下の情報を考慮しながら最適な実行プランを生成してください：

1. 過去の実行結果の履歴
2. 現在のコンテキスト
3. ゴールの要件と制約

プランは以下の形式で出力してください：

1. 現状と目標の分析
2. 実行ステップ（具体的なアクションのリスト）
3. 成功基準
4. リスクと対策

過去の結果から学んだ教訓を活かし、より効果的なプランを立案してください。"""

PLAN_HUMAN_TEMPLATE = """目標: {goal}
コンテキスト: {context}
過去の実行結果:
{past_results}

このゴールに対する実行プランを生成してください。"""

# 結果要約用のプロンプトテンプレート
SUMMARY_SYSTEM_TEMPLATE = """あなたは高度な要約AIアシスタントです。
与えられたチャット履歴から、ゴールの達成状況と重要なポイントを抽出し、簡潔に要約してください。

要約は以下の形式で出力してください：

1. 目標の達成状況
2. 主要な成果
3. 重要な学び
4. 次のステップへの提案

チャット履歴の文脈を理解し、もっとも重要な情報を抽出することに注力してください。"""

SUMMARY_HUMAN_TEMPLATE = """目標: {goal}
チャット履歴:
{chat_history}

このゴールの実行結果を要約してください。"""

# プロンプトテンプレートの作成
plan_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=PLAN_SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="history", optional=True),
    HumanMessagePromptTemplate.from_template(PLAN_HUMAN_TEMPLATE)
])

summary_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=SUMMARY_SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="history", optional=True),
    HumanMessagePromptTemplate.from_template(SUMMARY_HUMAN_TEMPLATE)
])

__all__ = [
    "plan_prompt",
    "summary_prompt",
    "PLAN_SYSTEM_TEMPLATE",
    "SUMMARY_SYSTEM_TEMPLATE",
    "PLAN_HUMAN_TEMPLATE",
    "SUMMARY_HUMAN_TEMPLATE"
]

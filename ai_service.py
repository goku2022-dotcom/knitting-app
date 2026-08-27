import os
from google import genai
from PIL import Image


# 1. 計算ツール（Function Calling用）
def calculate_yarn_needed(
    width_cm: float, length_cm: float, yarn_type: str = "並太"
) -> str:
    """編み物のサイズ（幅と長さ）から、必要な毛糸のおおよその玉数を計算するツール。

    Args:
        width_cm: 編みたい作品の幅（cm）
        length_cm: 編みたい作品の長さ（cm）
        yarn_type: 糸の太さ（極太 / 並太 / 中細 / 極細）
    """
    area = width_cm * length_cm
    coverage_map = {
        "極太": 400.0,
        "並太": 600.0,
        "中細": 800.0,
        "極細": 1000.0,
    }
    coverage = coverage_map.get(yarn_type, 600.0)
    skeins = max(1, round(area / coverage, 1))

    return f"【計算結果】面積 {area:.0f}cm² に対し、{yarn_type}の毛糸はおよそ {skeins} 玉必要です。"


# 2. RAG用：独自知識テキストから検索
def search_knowledge(user_query: str) -> str:
    """knowledge.txt を読み込み、質問に関連するブロックを抽出する"""
    file_path = "knowledge.txt"
    if not os.path.exists(file_path):
        return ""

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections = [s.strip() for s in content.split("\n\n") if s.strip()]
    matched_sections = []
    for section in sections:
        for word in ["ダイキ", "引き揃え", "輪", "ほどけない", "減らし目", "スピード", "魔法"]:
            if word in user_query and section not in matched_sections:
                matched_sections.append(section)

    if matched_sections:
        return "\n\n".join(matched_sections)
    return ""


# 3. ストリーミング対応のAI呼び出し関数
def get_knitting_advice_stream(
    api_key: str,
    mode: str,
    messages: list[dict],
    image: Image.Image | None = None,
):
    """回答を1文字ずつ細切れ（ストリーム）で順番に返すジェネレータ関数"""
    client = genai.Client(api_key=api_key)

    latest_user_message = messages[-1]["content"] if messages else ""
    retrieved_knowledge = search_knowledge(latest_user_message)

    base_system = (
        "あなたは編み物の中堅者の僕の友達です。"
        if mode == "🧶 デザイン・編み方のアドバイス"
        else "あなたは編み物の専門家です。"
    )

    if retrieved_knowledge:
        system_instruction = f"""{base_system}
以下の【参考マニュアル】に記載されている独自知識を最優先で参照して、ユーザーにわかりやすくアドバイスしてください。

【参考マニュアル】
{retrieved_knowledge}
"""
    else:
        system_instruction = f"{base_system} サイズや玉数の相談があれば計算ツールを使って正確に答えてください。"

    contents_list = [system_instruction]

    for m in messages:
        contents_list.append(f"{m['role']}: {m['content']}")

    if image is not None:
        contents_list.append(image)

    # generate_content_stream でリアルタイム生成
    response_stream = client.models.generate_content_stream(
        model="gemini-3.6-flash",  # お使いのモデルに合わせて調整
        contents=contents_list,
        config={
            "tools": [calculate_yarn_needed],
        },
    )

    # 届いた言葉の破片を順番に1つずつ画面側に送り出す
    for chunk in response_stream:
        if chunk.text:
            yield chunk.text
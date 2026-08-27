from google import genai
from PIL import Image
from pydantic import BaseModel, Field


# AIに返してもらうデータの設計図
class KnittingAdvice(BaseModel):
    difficulty: str = Field(
        description="難易度（例：初級 / 中級 / 上級 / 判定不能）"
    )
    recommended_hook_size: str = Field(
        description="おすすめの編み針や号数（例：かぎ針 6/0号、棒針 8号など）"
    )
    advice_comment: str = Field(
        description="ユーザーへのアドバイスやメッセージ本文"
    )
    tips: list[str] = Field(
        description="きれいに編むためのコツや注意点（箇条書き用・1〜3個）"
    )


# AI呼び出し専用の関数
def get_knitting_advice(
    api_key: str,
    mode: str,
    messages: list[dict],
    image: Image.Image | None = None,
) -> KnittingAdvice:
    client = genai.Client(api_key=api_key)

    if mode == "🧶 デザイン・編み方のアドバイス":
        system_instruction = "あなたは優しい編み物の超ベテランおばあちゃんです。画像や会話をもとに温かく丁寧に回答してください。"
    else:
        system_instruction = "あなたは編み物の厳格なプロ講師です。画像を細かく観察し、編み目の乱れや間違いを的確に指摘してください。"

    contents_list = [system_instruction]

    for m in messages:
        contents_list.append(f"{m['role']}: {m['content']}")

    if image is not None:
        contents_list.append(image)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=contents_list,
        config={
            "response_mime_type": "application/json",
            "response_schema": KnittingAdvice,
        },
    )

    return response.parsed
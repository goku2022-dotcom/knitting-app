from ai_service import KnittingAdvice, get_knitting_advice
from database import clear_db, init_db, load_messages, save_message
from PIL import Image
import streamlit as st

# DBの初期化（起動時に1回だけ実行）
init_db()

# 1. タイトル
st.title("🧶 画像も読めるAI編み物チャット")
st.caption("編み物の写真や図を見せてアドバイスをもらおう！")

# 2. リセットボタン（DBも空にする）
if st.sidebar.button("🗑️ 会話をリセット"):
    clear_db()
    st.session_state.messages = []
    st.rerun()

mode = st.sidebar.selectbox(
    "AIの診断モード",
    [
        "🧶 デザイン・編み方のアドバイス",
        "🔍 写真から編み目の間違い・ほつれ診断",
    ],
)

# 3. DBから過去の会話を復元して読み込む
if "messages" not in st.session_state:
    st.session_state.messages = load_messages()

# 4. 過去の会話を画面に表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image") is not None:
            st.image(msg["image"], width=300)
        st.write(msg["content"])

# 5. 画像アップロードボタン
uploaded_file = st.file_uploader(
    "編み物の写真や図面があればアップロード（任意）",
    type=["jpg", "png", "jpeg"],
)

# 6. チャット入力とAI通信
if user_input := st.chat_input("編み物について質問してね！"):
    img = None
    if uploaded_file is not None:
        img = Image.open(uploaded_file)

    # ユーザー入力を表示＆DBへ保存
    with st.chat_message("user"):
        if img is not None:
            st.image(img, width=300)
        st.write(user_input)

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "image": img}
    )
    save_message("user", user_input)  # DBに保存

    # AIの回答生成
    with st.chat_message("assistant"):
        with st.spinner("写真とメッセージを分析中..."):
            try:
                result: KnittingAdvice = get_knitting_advice(
                    api_key=st.secrets["GOOGLE_API_KEY"],
                    mode=mode,
                    messages=st.session_state.messages,
                    image=img,
                )

                col1, col2 = st.columns(2)
                col1.metric("📊 難易度", result.difficulty)
                col2.metric("🪡 おすすめの針", result.recommended_hook_size)

                st.write(result.advice_comment)

                if result.tips:
                    st.write("**💡 ワンポイントアドバイス**")
                    for tip in result.tips:
                        st.write(f"- {tip}")

                tips_text = ""
                if result.tips:
                    for t in result.tips:
                        tips_text += f"- {t}\n"

                saved_content = f"""**【難易度】** {result.difficulty} / **【針】** {result.recommended_hook_size}

{result.advice_comment}

**💡 ワンポイントアドバイス**
{tips_text}"""

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": saved_content,
                        "image": None,
                    }
                )
                save_message("assistant", saved_content)  # DBに保存

            except Exception as e:
                st.error(
                    "⚠️ AIとの通信で問題が発生しました。少し待ってから再度お試しください。"
                )
                st.caption(f"エラーの詳細: {e}")
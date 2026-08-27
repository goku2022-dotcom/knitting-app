from ai_service import get_knitting_advice_stream
from database import (
    clear_user_db,
    get_user_usage_stats,
    init_db,
    load_messages,
    log_api_usage,
    register_user,
    save_message,
    verify_user,
)
from PIL import Image
import streamlit as st

init_db()

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

# ==========================================
# 1. ログイン & 新規登録画面
# ==========================================
if st.session_state.logged_in_user is None:
    st.title("🧶 AI編み物チャット")
    tab_login, tab_register = st.tabs(["🔑 ログイン", "✨ 新規アカウント登録"])

    with tab_login:
        login_user = st.text_input("ユーザー名", key="login_username")
        login_pwd = st.text_input(
            "パスワード", type="password", key="login_password"
        )
        if st.button("ログイン", key="btn_login"):
            if verify_user(login_user.strip(), login_pwd):
                st.session_state.logged_in_user = login_user.strip()
                st.session_state.messages = load_messages(
                    st.session_state.logged_in_user
                )
                st.success("ログインしました！")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが正しくありません。")

    with tab_register:
        new_user = st.text_input("希望のユーザー名", key="reg_username")
        new_pwd = st.text_input(
            "パスワード", type="password", key="reg_password"
        )
        new_pwd_confirm = st.text_input(
            "パスワード（確認用）", type="password", key="reg_pwd_confirm"
        )
        if st.button("アカウント作成", key="btn_register"):
            if not new_user.strip() or not new_pwd:
                st.warning("ユーザー名とパスワードを入力してください。")
            elif new_pwd != new_pwd_confirm:
                st.error("パスワードが一致しません。")
            else:
                if register_user(new_user.strip(), new_pwd):
                    st.success(
                        "アカウントを作成しました！「ログイン」タブからログインしてください。"
                    )
                else:
                    st.error("このユーザー名は既に使用されています。")
    st.stop()

# ==========================================
# 2. ログイン後チャット画面
# ==========================================
current_user = st.session_state.logged_in_user

st.title("🧶 画像も読めるAI編み物チャット")
st.caption(f"ログイン中: **{current_user}** さん")

# --- サイドバー：運用ダッシュボード ---
with st.sidebar:
    st.write(f"👤 **{current_user}** さん")

    # API利用統計の表示
    stats = get_user_usage_stats(current_user)
    st.markdown("### 📊 API利用ダッシュボード")
    col_a, col_b = st.columns(2)
    col_a.metric("総トークン数", f"{stats['total_tokens']:,}")
    col_b.metric("概算コスト", f"${stats['total_cost_usd']:.4f}")

    if st.button("🚪 ログアウト"):
        st.session_state.logged_in_user = None
        st.session_state.messages = []
        st.rerun()

    if st.button("🗑️ 会話をリセット"):
        clear_user_db(current_user)
        st.session_state.messages = []
        st.rerun()

    mode = st.selectbox(
        "AIの診断モード",
        [
            "🧶 デザイン・編み方のアドバイス",
            "🔍 写真から編み目の間違い・ほつれ診断",
        ],
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image") is not None:
            st.image(msg["image"], width=300)
        st.write(msg["content"])

uploaded_file = st.file_uploader(
    "編み物の写真や図面があればアップロード（任意）",
    type=["jpg", "png", "jpeg"],
)

if user_input := st.chat_input("編み物について質問してね！"):
    img = None
    if uploaded_file is not None:
        img = Image.open(uploaded_file)

    with st.chat_message("user"):
        if img is not None:
            st.image(img, width=300)
        st.write(user_input)

    st.session_state.messages.append(
        {"role": "user", "content": user_input, "image": img}
    )
    save_message(current_user, "user", user_input)

    with st.chat_message("assistant"):
        try:
            response_generator = get_knitting_advice_stream(
                api_key=st.secrets["GOOGLE_API_KEY"],
                mode=mode,
                messages=st.session_state.messages,
                image=img,
            )

            full_response = st.write_stream(response_generator)

            # トークン数の概算計算（日本語はおよそ 1文字 ≒ 1〜1.5トークン）
            prompt_tokens = int(
                len(
                    "".join(
                        [m["content"] for m in st.session_state.messages[:-1]]
                    )
                )
                * 1.2
            )
            response_tokens = int(len(full_response) * 1.2)

            # Gemini Flashの標準単価（入力 $0.075/1M, 出力 $0.30/1M tokens）に基づいた概算料金
            cost_usd = (prompt_tokens * 0.000000075) + (
                response_tokens * 0.0000003
            )

            # ログ保存
            log_api_usage(
                current_user, prompt_tokens, response_tokens, cost_usd
            )

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response, "image": None}
            )
            save_message(current_user, "assistant", full_response)

            # サイドバーの数値を即時更新するために画面をリフレッシュ
            st.rerun()

        except Exception as e:
            st.error(
                "⚠️ AIとの通信で問題が発生しました。少し待ってから再度お試しください。"
            )
            st.caption(f"エラーの詳細: {e}")
import hashlib
import sqlite3

DB_NAME = "chat_history.db"


def hash_password(password: str) -> str:
    """パスワードをSHA-256でハッシュ化（暗号化）する"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    """データベースとテーブルを作成する初期設定"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. ユーザー管理テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # 2. メッセージ管理テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    # 3. API利用ログテーブル（新規追加）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            prompt_tokens INTEGER,
            response_tokens INTEGER,
            estimated_cost_usd REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def register_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    pwd_hash = hash_password(password)

    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, pwd_hash),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    pwd_hash = hash_password(password)

    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password_hash = ?",
        (username, pwd_hash),
    )
    user = cursor.fetchone()
    conn.close()

    return user is not None


def save_message(username: str, role: str, content: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (username, role, content) VALUES (?, ?, ?)",
        (username, role, content),
    )
    conn.commit()
    conn.close()


def load_messages(username: str) -> list[dict]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE username = ? ORDER BY id ASC",
        (username,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]


def clear_user_db(username: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE username = ?", (username,))
    conn.commit()
    conn.close()


# --- 新規追加: ログ記録と集計関数 ---


def log_api_usage(
    username: str, prompt_tokens: int, response_tokens: int, cost_usd: float
):
    """APIの利用量を記録する"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO api_logs (username, prompt_tokens, response_tokens, estimated_cost_usd)
        VALUES (?, ?, ?, ?)
    """,
        (username, prompt_tokens, response_tokens, cost_usd),
    )
    conn.commit()
    conn.close()


def get_user_usage_stats(username: str) -> dict:
    """指定ユーザーの合計トークン数と概算コストを集計する"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            COALESCE(SUM(prompt_tokens), 0),
            COALESCE(SUM(response_tokens), 0),
            COALESCE(SUM(estimated_cost_usd), 0.0)
        FROM api_logs
        WHERE username = ?
    """,
        (username,),
    )
    row = cursor.fetchone()
    conn.close()

    return {
        "total_prompt_tokens": row[0],
        "total_response_tokens": row[1],
        "total_tokens": row[0] + row[1],
        "total_cost_usd": row[2],
    }
import os
import sqlite3
import json
from datetime import datetime

# 環境変数からDBパスを取得、デフォルトは '/app/data/trends.db'
DB_PATH = os.environ.get("DATABASE_PATH", "./data/trends.db")

def get_connection():
    """データベース接続を取得します。"""
    # ディレクトリが存在しない場合は作成
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得できるようにする
    return conn

def init_db():
    """テーブルを作成し、初期設定データを投入します。"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. X/Yahooトレンド履歴テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS x_trends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        tweet_count_24h INTEGER,
        positive_ratio REAL,
        is_filtered_out INTEGER DEFAULT 0,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. note上位記事テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS note_ranking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id TEXT NOT NULL,
        title TEXT NOT NULL,
        tags TEXT, -- カンマ区切りの文字列
        like_count INTEGER,
        category TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. 突合・分析結果テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keyword_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL, -- YYYY-MM-DD
        keyword TEXT NOT NULL,
        x_score REAL,
        note_score REAL,
        total_score REAL,
        status TEXT, -- '第1象限', '第2象限', '第3象限', '第4象限'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. システム設定テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # 5. バッチ実行ステータステーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batch_status (
        status TEXT NOT NULL, -- 'idle', 'running', 'success', 'failed'
        message TEXT,
        progress INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # デフォルト設定値の投入
    default_settings = {
        "seed_keywords": json.dumps(["ツール", "AI", "効率化", "開発"]),
        "target_themes": json.dumps([
            "ソフトウェア開発やプログラミング、システム設計に関する技術的な話題",
            "業務効率化や生産性向上、ITツールの活用に関する実用的な話題",
            "Web開発やアプリ構築、フロントエンド・バックエンド技術に関する話題",
            "AI活用や人工知能、機械学習を用いた自動化に関する技術的な話題"
        ]),
        "ng_keywords": json.dumps(["地震", "プレゼント", "懸賞", "キャンペーン", "公式", "無料", "中止", "逮捕", "火事"]),
        "similarity_threshold": "0.81",
        "note_category": "tech"
    }

    for key, val in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    # バッチ初期ステータスの投入
    cursor.execute("SELECT COUNT(*) FROM batch_status")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO batch_status (status, message, progress) VALUES (?, ?, ?)", ("idle", "待機中", 0))

    conn.commit()
    conn.close()

# ----------------- 設定関連 -----------------

def get_settings():
    """現在のシステム設定を全取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    
    settings = {}
    for row in rows:
        key = row["key"]
        val = row["value"]
        # JSONデコード可能なものはデコードして返す
        try:
            settings[key] = json.loads(val)
        except json.JSONDecodeError:
            try:
                # 浮動小数点数
                settings[key] = float(val)
            except ValueError:
                settings[key] = val
    return settings

def update_setting(key: str, value) -> bool:
    """指定したキーの設定値を更新します。"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # リストや辞書はJSON文字列に変換
    if isinstance(value, (list, dict)):
        val_str = json.dumps(value)
    else:
        val_str = str(value)
        
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_str))
    conn.commit()
    conn.close()
    return True

# ----------------- バッチステータス関連 -----------------

def get_batch_status():
    """現在のバッチ実行ステータスを取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, message, progress, updated_at FROM batch_status LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"status": "idle", "message": "待機中", "progress": 0, "updated_at": ""}

def update_batch_status(status: str, message: str, progress: int):
    """バッチ実行ステータスを更新します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE batch_status SET status = ?, message = ?, progress = ?, updated_at = CURRENT_TIMESTAMP",
        (status, message, progress)
    )
    conn.commit()
    conn.close()

def reset_stuck_batch_status():
    """サーバー起動時に、実行中のままスタックしているバッチステータスをリセットします。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM batch_status LIMIT 1")
    row = cursor.fetchone()
    if row and row["status"] == "running":
        cursor.execute(
            "UPDATE batch_status SET status = ?, message = ?, progress = ?, updated_at = CURRENT_TIMESTAMP",
            ("failed", "システム再起動により処理が中断されました。", 100)
        )
        conn.commit()
    conn.close()

# ----------------- データ登録・クリア関連 -----------------

def clear_scraped_data():
    """スクレイピングした一時データ（Xトレンドとnote記事）をクリアします。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM x_trends")
    cursor.execute("DELETE FROM note_ranking")
    conn.commit()
    conn.close()

def clear_daily_data(date_str: str):
    """指定した日付の分析結果データをクリアします。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keyword_analysis WHERE date = ?", (date_str,))
    conn.commit()
    conn.close()

def insert_x_trend(keyword: str, tweet_count: int, positive_ratio: float, is_filtered_out: bool = False):
    """Xトレンドデータを1件挿入します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO x_trends (keyword, tweet_count_24h, positive_ratio, is_filtered_out) VALUES (?, ?, ?, ?)",
        (keyword, tweet_count, positive_ratio, 1 if is_filtered_out else 0)
    )
    conn.commit()
    conn.close()

def insert_note_ranking(article_id: str, title: str, tags: list, like_count: int, category: str):
    """note上位記事データを1件挿入します。"""
    conn = get_connection()
    cursor = conn.cursor()
    tags_str = ",".join(tags) if tags else ""
    cursor.execute(
        "INSERT INTO note_ranking (article_id, title, tags, like_count, category) VALUES (?, ?, ?, ?, ?)",
        (article_id, title, tags_str, like_count, category)
    )
    conn.commit()
    conn.close()

def insert_keyword_analysis(date_str: str, keyword: str, x_score: float, note_score: float, total_score: float, status: str):
    """突合・分析結果データを1件挿入します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO keyword_analysis (date, keyword, x_score, note_score, total_score, status) VALUES (?, ?, ?, ?, ?, ?)",
        (date_str, keyword, x_score, note_score, total_score, status)
    )
    conn.commit()
    conn.close()

def get_keyword_analysis(date_str: str = None):
    """突合・分析結果を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    if date_str:
        cursor.execute("SELECT id, date, keyword, x_score, note_score, total_score, status FROM keyword_analysis WHERE date = ? ORDER BY total_score DESC", (date_str,))
    else:
        cursor.execute("SELECT id, date, keyword, x_score, note_score, total_score, status FROM keyword_analysis ORDER BY date DESC, total_score DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# モジュールのインポート時に初期化を実行
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

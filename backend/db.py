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
        supply_count INTEGER DEFAULT 0,
        priority_score REAL DEFAULT 0,
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

    # 6. noteハッシュタグボリュームテーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS note_hashtags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hashtag TEXT NOT NULL UNIQUE,
        post_count INTEGER DEFAULT 0,
        related_tags TEXT, -- カンマ区切りの文字列
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 7. ハッシュタグ履歴スナップショット
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS note_hashtag_history (
        hashtag TEXT NOT NULL,
        post_count INTEGER DEFAULT 0,
        related_tags TEXT,
        batch_date TEXT NOT NULL,
        PRIMARY KEY (hashtag, batch_date)
    )
    """)

    # 8. 共起タグ履歴スナップショット
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS note_cooccurrence_history (
        seed TEXT NOT NULL,
        tag TEXT NOT NULL,
        weighted_demand INTEGER DEFAULT 0,
        article_count INTEGER DEFAULT 0,
        batch_date TEXT NOT NULL,
        PRIMARY KEY (seed, tag, batch_date)
    )
    """)

    # デフォルト設定値の投入
    default_settings = {
        "seed_keywords": json.dumps(["ツール", "AI", "効率化", "開発"]),
        "target_themes": json.dumps([
            "プログラミング、ソフトウェア開発、システム設計、コーディング、ソースコード、アルゴリズム",
            "AI、人工知能、機械学習、ディープラーニング、LLM、ChatGPT、画像生成、自動化、自然言語処理",
            "ITツール、業務効率化、生産性向上、DX、自動化スクリプト、SaaS、ソフトウェア、アプリケーション",
            "Web開発、アプリ開発、クラウド、データベース、インフラ、フロントエンド、バックエンド"
        ]),
        "negative_themes": json.dumps([
            "スポーツ、自転車レース、ツールドフランス、ツールド、ロードバイク、陸上、野球、サッカー、運動、大会",
            "店舗、中古買取、リサイクルショップ、中古ツール、工具、ツールオフ、販売、オークション、一般雑貨",
            "行政、土木工事、都市計画、開発局、開発行為、開発許可、道路、インフラ整備、土地開発、宅地開発",
            "日常生活、雑談、挨拶、感情、天気、旅行、京都、鹿児島、地域名、観光地、修学旅行、学校行事",
            "エンタメ、芸能人、テレビ、音楽、映画、アニメ、アイドル、ゲーム、バズワード、キャラクター、声優"
        ]),
        "ng_keywords": json.dumps(["地震", "プレゼント", "懸賞", "キャンペーン", "公式", "無料", "中止", "逮捕", "火事", "ツールド", "開発局", "開発行為", "開発許可", "開発道路", "ツールオフ", "ツールボックス", "鹿児島", "修学旅行", "onej"]),
        "similarity_threshold": "0.81",
        "note_category": "tech",
        "quadrant_mode": "fixed",
        "quadrant_fixed_threshold": "0.5",
    }

    for key, val in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    # バッチ初期ステータスの投入
    cursor.execute("SELECT COUNT(*) FROM batch_status")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO batch_status (status, message, progress) VALUES (?, ?, ?)", ("idle", "待機中", 0))

    # 既存DBへのカラム追加（マイグレーション）
    _migrate_keyword_analysis_columns(cursor)

    conn.commit()
    conn.close()

def _migrate_keyword_analysis_columns(cursor):
    """keyword_analysis テーブルに新カラムを追加します（既存DB互換）。"""
    cursor.execute("PRAGMA table_info(keyword_analysis)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if "supply_count" not in existing_cols:
        cursor.execute("ALTER TABLE keyword_analysis ADD COLUMN supply_count INTEGER DEFAULT 0")
    if "priority_score" not in existing_cols:
        cursor.execute("ALTER TABLE keyword_analysis ADD COLUMN priority_score REAL DEFAULT 0")

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

def insert_keyword_analysis(date_str: str, keyword: str, x_score: float, note_score: float, total_score: float, status: str, supply_count: int = 0, priority_score: float = 0.0):
    """突合・分析結果データを1件挿入します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO keyword_analysis (date, keyword, x_score, note_score, total_score, status, supply_count, priority_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (date_str, keyword, x_score, note_score, total_score, status, supply_count, priority_score)
    )
    conn.commit()
    conn.close()

def get_keyword_analysis(date_str: str = None):
    """突合・分析結果を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    if date_str:
        cursor.execute("SELECT id, date, keyword, x_score, note_score, total_score, status, supply_count, priority_score FROM keyword_analysis WHERE date = ? ORDER BY total_score DESC", (date_str,))
    else:
        cursor.execute("SELECT id, date, keyword, x_score, note_score, total_score, status, supply_count, priority_score FROM keyword_analysis ORDER BY date DESC, total_score DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def insert_note_hashtag(hashtag: str, post_count: int, related_tags: list):
    """noteのハッシュタグ情報（投稿件数・関連タグ）を登録または更新します。"""
    conn = get_connection()
    cursor = conn.cursor()
    related_tags_str = ",".join(related_tags) if related_tags else ""
    clean_tag = hashtag.replace("#", "").strip()
    cursor.execute(
        """
        INSERT OR REPLACE INTO note_hashtags (hashtag, post_count, related_tags, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (clean_tag, post_count, related_tags_str)
    )
    conn.commit()
    conn.close()

def get_note_hashtag(hashtag: str):
    """特定のハッシュタグ情報を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    clean_tag = hashtag.replace("#", "").strip()
    cursor.execute("SELECT hashtag, post_count, related_tags, updated_at FROM note_hashtags WHERE hashtag = ?", (clean_tag,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        data["related_tags"] = data["related_tags"].split(",") if data["related_tags"] else []
        return data
    return None

def get_all_note_hashtags():
    """登録されているすべてのハッシュタグ情報を取得します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT hashtag, post_count, related_tags, updated_at FROM note_hashtags ORDER BY post_count DESC")
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        data = dict(row)
        data["related_tags"] = data["related_tags"].split(",") if data["related_tags"] else []
        results.append(data)
    return results

# ----------------- ハッシュタグ履歴・共起分析 -----------------

def insert_note_hashtag_history(hashtag: str, post_count: int, related_tags: list, batch_date: str):
    """バッチ実行ごとのハッシュタグスナップショットを保存します。"""
    conn = get_connection()
    cursor = conn.cursor()
    clean_tag = hashtag.replace("#", "").strip()
    related_tags_str = ",".join(related_tags) if related_tags else ""
    cursor.execute("""
        INSERT OR REPLACE INTO note_hashtag_history (hashtag, post_count, related_tags, batch_date)
        VALUES (?, ?, ?, ?)
    """, (clean_tag, post_count, related_tags_str, batch_date))
    conn.commit()
    conn.close()

def get_hashtag_history(hashtag: str, limit: int = 10) -> list:
    """指定ハッシュタグの投稿件数推移を返します（新しい順）。"""
    conn = get_connection()
    cursor = conn.cursor()
    clean_tag = hashtag.replace("#", "").strip()
    cursor.execute("""
        SELECT batch_date, post_count, related_tags
        FROM note_hashtag_history
        WHERE hashtag = ?
        ORDER BY batch_date DESC LIMIT ?
    """, (clean_tag, limit))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["related_tags"] = d["related_tags"].split(",") if d["related_tags"] else []
        result.append(d)
    return result

def get_related_tags_diff(hashtag: str) -> dict:
    """直近2回のバッチ間での related_tags の差分を返します。"""
    history = get_hashtag_history(hashtag, limit=2)
    if len(history) < 2:
        return {
            "new": [],
            "removed": [],
            "stable": history[0]["related_tags"] if history else [],
            "post_count_delta": 0,
            "post_count_delta_pct": 0.0,
        }
    current_tags = set(history[0]["related_tags"])
    prev_tags = set(history[1]["related_tags"])
    return {
        "new": sorted(current_tags - prev_tags),
        "removed": sorted(prev_tags - current_tags),
        "stable": sorted(current_tags & prev_tags),
        "post_count_delta": history[0]["post_count"] - history[1]["post_count"],
        "post_count_delta_pct": round(
            (history[0]["post_count"] - history[1]["post_count"])
            / max(history[1]["post_count"], 1) * 100, 1
        ),
    }

def get_cooccurrence_tags(seed: str, top_n: int = 20) -> list:
    """note_ranking から、シードタグと共起するタグを like_count 重み付きで返します。"""
    from collections import defaultdict
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tags, like_count FROM note_ranking")
    rows = cursor.fetchall()
    conn.close()

    weights: dict = defaultdict(float)
    counts: dict = defaultdict(int)

    for row in rows:
        tags = [t.strip() for t in (row["tags"] or "").split(",") if t.strip()]
        lower_tags = [t.lower() for t in tags]
        if seed.lower() not in lower_tags:
            continue
        likes = max(row["like_count"] or 0, 1)
        for tag in tags:
            if tag.lower() != seed.lower():
                weights[tag] += likes
                counts[tag] += 1

    results = sorted(
        [{"tag": t, "weighted_demand": round(w), "article_count": counts[t]} for t, w in weights.items()],
        key=lambda x: x["weighted_demand"],
        reverse=True,
    )
    return results[:top_n]

def insert_cooccurrence_history(seed: str, tag: str, weighted_demand: int, article_count: int, batch_date: str):
    """共起タグのスナップショットを1件保存します。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO note_cooccurrence_history (seed, tag, weighted_demand, article_count, batch_date)
        VALUES (?, ?, ?, ?, ?)
    """, (seed, tag, weighted_demand, article_count, batch_date))
    conn.commit()
    conn.close()

def save_cooccurrence_snapshot(batch_date: str):
    """全シードの共起タグ分析結果を履歴テーブルに保存します。"""
    seeds = get_settings().get("seed_keywords", [])
    for seed in seeds:
        tags = get_cooccurrence_tags(seed, top_n=50)
        for t in tags:
            insert_cooccurrence_history(
                seed=seed,
                tag=t["tag"],
                weighted_demand=t["weighted_demand"],
                article_count=t["article_count"],
                batch_date=batch_date,
            )

def get_cooccurrence_tags_with_status(seed: str, top_n: int = 20, batch_date: str = None) -> list:
    """共起タグに前回バッチ比の状態バッジ情報を付与して返します。"""
    from datetime import date as _date
    if not batch_date:
        batch_date = _date.today().strftime("%Y-%m-%d")

    current = get_cooccurrence_tags(seed, top_n=top_n)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT batch_date FROM note_cooccurrence_history
        WHERE seed = ? AND batch_date < ?
        ORDER BY batch_date DESC LIMIT 1
    """, (seed, batch_date))
    prev_row = cursor.fetchone()

    prev_demands: dict = {}
    if prev_row:
        prev_date = prev_row["batch_date"]
        cursor.execute("""
            SELECT tag, weighted_demand FROM note_cooccurrence_history
            WHERE seed = ? AND batch_date = ?
        """, (seed, prev_date))
        for row in cursor.fetchall():
            prev_demands[row["tag"]] = row["weighted_demand"]
    conn.close()

    results = []
    for item in current:
        tag = item["tag"]
        demand = item["weighted_demand"]
        prev = prev_demands.get(tag)
        if prev is None:
            status = "new"
        elif demand >= prev * 1.2:
            status = "up"
        elif demand <= prev * 0.8:
            status = "down"
        else:
            status = "stable"
        results.append({**item, "seed": seed, "status": status})
    return results

# モジュールのインポート時に初期化を実行
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

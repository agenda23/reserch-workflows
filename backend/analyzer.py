import sqlite3
from datetime import datetime
import numpy as np
import db
import local_filter

def calculate_x_buzz_score(tweet_count: int, positive_ratio: float) -> float:
    """Xバズスコアを算出します。"""
    # ツイート数に感情比率を掛け合わせる（ネガティブすぎるものはスコアが下がる）
    return float(tweet_count) * positive_ratio

def analyze_and_score_trends(date_str: str = None):
    """Xトレンドとnote記事データを突合し、スコアリングと4象限判定を行って保存します。"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    db.init_db()
    
    # 既存の同日データをクリア
    db.clear_daily_data(date_str)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # 1. 有効なXトレンドキーワード（NGワードや類似度判定前の全キーワード）の取得
    # ここで一度すべてのキーワードを取り出して、NLPフィルターにかける
    cursor.execute("SELECT keyword, tweet_count_24h, positive_ratio FROM x_trends")
    x_rows = cursor.fetchall()
    
    if not x_rows:
        print("Xトレンドデータが見つかりません。分析をスキップします。")
        conn.close()
        return
        
    # 有効なキーワードの選定（NLPフィルタリング）
    valid_keywords = []
    for row in x_rows:
        kw = row["keyword"]
        # NLP判定
        if local_filter.check_keyword_relevance(kw):
            valid_keywords.append({
                "keyword": kw,
                "tweet_count": row["tweet_count_24h"],
                "positive_ratio": row["positive_ratio"],
                "x_raw_score": calculate_x_buzz_score(row["tweet_count_24h"], row["positive_ratio"])
            })
        else:
            # データベースのis_filtered_outを更新
            cursor.execute("UPDATE x_trends SET is_filtered_out = 1 WHERE keyword = ?", (kw,))
    conn.commit()
    
    if not valid_keywords:
        print("NLPフィルターを通過した有効なキーワードがありません。")
        conn.close()
        return
        
    # 2. note記事（人気ランキング）データの取得
    cursor.execute("SELECT title, tags, like_count FROM note_ranking")
    note_rows = cursor.fetchall()
    
    # 各キーワードについて、note需要スコアを計算
    analysis_results = []
    for item in valid_keywords:
        kw = item["keyword"]
        note_raw_score = 0.0
        match_count = 0
        
        for note in note_rows:
            title = note["title"]
            tags = note["tags"].split(",") if note["tags"] else []
            likes = note["like_count"] or 0
            
            # 部分一致マッチング（タイトルに含まれる、またはハッシュタグに完全一致）
            is_match = (kw.lower() in title.lower()) or (any(kw.lower() == tag.lower() for tag in tags))
            
            if is_match:
                # 該当キーワードを含むnote記事のスキ数を加算（最低でも1スキ分の加点）
                note_raw_score += max(likes, 1)
                match_count += 1
                
        # 1件もマッチしなかった場合は、需要スコアは0（あるいは微小な初期値）
        analysis_results.append({
            "keyword": kw,
            "x_raw_score": item["x_raw_score"],
            "note_raw_score": note_raw_score,
            "match_count": match_count
        })
        
    conn.close()
    
    # 3. スコアの正規化 (0.0 〜 1.0) と総合スコア算出
    x_scores = [r["x_raw_score"] for r in analysis_results]
    note_scores = [r["note_raw_score"] for r in analysis_results]
    
    max_x = max(x_scores) if x_scores and max(x_scores) > 0 else 1.0
    max_note = max(note_scores) if note_scores and max(note_scores) > 0 else 1.0
    
    # 4象限分類のためのしきい値（平均値）
    # スコアが0より大きいものの平均値を境界値とする
    x_positives = [s for s in x_scores if s > 0]
    note_positives = [s for s in note_scores if s > 0]
    
    threshold_x = np.mean(x_positives) / max_x if x_positives else 0.5
    threshold_note = np.mean(note_positives) / max_note if note_positives else 0.5
    
    # デフォルトで0.5を下回る場合は補正
    threshold_x = max(min(threshold_x, 0.7), 0.3)
    threshold_note = max(min(threshold_note, 0.7), 0.3)
    
    for r in analysis_results:
        # 正規化
        norm_x = r["x_raw_score"] / max_x
        norm_note = r["note_raw_score"] / max_note
        
        # 総合スコア (乗算ベース。両方で高い値を持つ「お宝キーワード」が上位に来る)
        # どちらかが0でも最低限の片方スコアが寄与するように (norm_x + 0.1) * (norm_note + 0.1) などに調整
        total_score = (norm_x * 0.7) + (norm_note * 0.3) # ハイブリッド加算（Xバズ多め）、あるいは乗算
        # 仕様書の「(X_Buzz_Scoreの正規化値) × (note_Demand_Scoreの正規化値)」を採用
        # ただし片方が0の時に完全に0になってしまうのを避けるため、加算も少し織り交ぜるか、乗算にするか
        # 4象限の性質上、乗算は第1象限（両方高）を最も強く引き上げるため、仕様どおりの乗算を採用
        total_score = norm_x * norm_note
        
        # 4象限の決定
        is_x_high = norm_x >= threshold_x
        is_note_high = norm_note >= threshold_note
        
        if is_x_high and is_note_high:
            status = "第1象限:超お宝"
        elif not is_x_high and is_note_high:
            status = "第2象限:ストック需要"
        elif not is_x_high and not is_note_high:
            status = "第3象限:対象外"
        else:
            status = "第4象限:急上昇トレンド"
            
        # データベースへ書き込み
        db.insert_keyword_analysis(
            date_str=date_str,
            keyword=r["keyword"],
            x_score=round(norm_x, 4),
            note_score=round(norm_note, 4),
            total_score=round(total_score, 4),
            status=status
        )
        
    print(f"分析完了: {len(analysis_results)} 件のデータを処理し、データベースに保存しました。")

def run_analysis_pipeline():
    """バッチ実行全体（データ収集 -> フィルタリング -> 突合・分析）を管理します。"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    db.update_batch_status("running", "突合・分析処理を実行中...", 95)
    try:
        analyze_and_score_trends(date_str)
        db.update_batch_status("success", "分析処理が正常に完了しました。", 100)
    except Exception as e:
        print(f"分析プロセス中にエラーが発生しました: {e}")
        db.update_batch_status("failed", f"エラー発生: {str(e)}", 100)
        raise e

if __name__ == "__main__":
    analyze_and_score_trends()

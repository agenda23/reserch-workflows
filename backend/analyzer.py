import sqlite3
from datetime import datetime
import asyncio
import math
import numpy as np
import db
import local_filter
import scraper

def calculate_x_buzz_score(tweet_count: int, positive_ratio: float) -> float:
    """Xバズスコアを算出します。"""
    # ツイート数に感情比率を掛け合わせる（ネガティブすぎるものはスコアが下がる）
    return float(tweet_count) * positive_ratio

def calculate_priority_score(demand_score: float, supply_count: int) -> float:
    """需要スコアと供給量からブルーオーシャン度（執筆優先度）を算出します。"""
    SUPPLY_BASELINE = 50
    if demand_score <= 0:
        return 0.0
    effective_supply = supply_count if supply_count > 0 else SUPPLY_BASELINE
    return demand_score / math.log10(effective_supply + 2)

async def _fetch_supply_counts(keywords: list) -> dict:
    """キーワードごとの供給量（競合記事数）を非同期で取得します。"""
    counts = {}
    for idx, kw in enumerate(keywords):
        db.update_batch_status("running", f"供給量調査中 ({idx+1}/{len(keywords)}): {kw}", 92 + int((idx / max(len(keywords), 1)) * 3))
        counts[kw] = await scraper.fetch_supply_count(kw)
    return counts

async def _prepare_dynamic_negatives():
    """分析前に時事ニュースRSSから動的ネガティブテーマを取得します。"""
    headlines = await scraper.fetch_news_headlines(30)
    local_filter.set_dynamic_negative_headlines(headlines)

async def analyze_and_score_trends(date_str: str = None, supply_counts: dict = None):
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
            tweet_count = row["tweet_count_24h"] or 0
            valid_keywords.append({
                "keyword": kw,
                "tweet_count": tweet_count,
                "positive_ratio": row["positive_ratio"],
                "x_raw_score": calculate_x_buzz_score(tweet_count, row["positive_ratio"])
            })
        else:
            # データベースのis_filtered_outを更新
            cursor.execute("UPDATE x_trends SET is_filtered_out = 1 WHERE keyword = ?", (kw,))
    conn.commit()
    
    if not valid_keywords:
        print("NLPフィルターを通過した有効なキーワードがありません。")
        conn.close()
        return
        
    # local_filter から SentenceTransformer モデルを取得
    model = local_filter.get_model()
    
    # 2. note記事（人気ランキング）データの取得
    cursor.execute("SELECT title, tags, like_count FROM note_ranking")
    note_rows = cursor.fetchall()
    
    if note_rows:
        # あらかじめ note のタイトル群をエンコードしておく（高速化のため）
        note_titles = [f"passage: {row['title']}" for row in note_rows]
        note_embeddings = model.encode(note_titles, convert_to_tensor=True)
    
    # 各キーワードについて、note需要スコアを計算
    analysis_results = []
    settings = local_filter.db.get_settings()
    settings_seeds = settings.get("seed_keywords", [])

    # シードキーワードの埋め込みを事前計算
    if settings_seeds:
        seed_embeddings = model.encode(
            [f"passage: {s}" for s in settings_seeds],
            convert_to_tensor=True
        )
    else:
        seed_embeddings = None
    
    for item in valid_keywords:
        kw = item["keyword"]
        note_raw_score = 0.0
        match_count = 0
        
        if note_rows:
            # キーワードのエンコード
            query_text = f"query: {kw}"
            query_embedding = model.encode(query_text, convert_to_tensor=True)
            
            # 各 note タイトルとの類似度を計算
            cos_scores = local_filter.util.cos_sim(query_embedding, note_embeddings)[0]
            
            for idx, note in enumerate(note_rows):
                score = float(cos_scores[idx].cpu().item())
                likes = note["like_count"] or 0
                
                # 類似度0.78以上でマッチと判定（NLP意味マッチング）
                if score >= 0.78:
                    # 類似度スコアが高いほど、スキ数の影響が大きくなるようにする (自乗重み付け)
                    note_raw_score += max(likes, 1) * (score ** 2)
                    match_count += 1

            # ハッシュタグボーナス：NLP類似度ベース
            if seed_embeddings is not None:
                seed_sims = local_filter.util.cos_sim(query_embedding, seed_embeddings)[0]
                for idx, seed in enumerate(settings_seeds):
                    sim = float(seed_sims[idx].cpu().item())
                    if sim >= 0.80:
                        hashtag_data = db.get_note_hashtag(seed)
                        if hashtag_data and hashtag_data["post_count"] > 0:
                            bonus = float(np.log10(hashtag_data["post_count"])) * 2.0 * sim
                            note_raw_score += bonus
        elif seed_embeddings is not None:
            query_embedding = model.encode(f"query: {kw}", convert_to_tensor=True)
            seed_sims = local_filter.util.cos_sim(query_embedding, seed_embeddings)[0]
            for idx, seed in enumerate(settings_seeds):
                sim = float(seed_sims[idx].cpu().item())
                if sim >= 0.80:
                    hashtag_data = db.get_note_hashtag(seed)
                    if hashtag_data and hashtag_data["post_count"] > 0:
                        bonus = float(np.log10(hashtag_data["post_count"])) * 2.0 * sim
                        note_raw_score += bonus
                        
        analysis_results.append({
            "keyword": kw,
            "x_raw_score": item["x_raw_score"],
            "note_raw_score": note_raw_score,
            "match_count": match_count
        })
        
    conn.close()
    
    if not analysis_results:
        print("分析対象のキーワードがありません。")
        return

    # 供給量（競合記事数）の取得
    if supply_counts is None:
        keywords = [r["keyword"] for r in analysis_results]
        supply_counts = await _fetch_supply_counts(keywords)
    
    # 3. スコアの正規化 と総合スコア算出
    x_scores = [r["x_raw_score"] for r in analysis_results]
    note_scores = [r["note_raw_score"] for r in analysis_results]
    
    max_x = max(x_scores) if x_scores and max(x_scores) > 0 else 1.0
    max_note = max(note_scores) if note_scores and max(note_scores) > 0 else 1.0
    
    # 4象限分類のためのしきい値
    quadrant_mode = settings.get("quadrant_mode", "fixed")
    fixed_thr = float(settings.get("quadrant_fixed_threshold", 0.5))

    if quadrant_mode == "dynamic":
        x_positives = [s for s in x_scores if s > 0]
        note_positives = [s for s in note_scores if s > 0]
        threshold_x = np.mean(x_positives) / max_x if x_positives else 0.5
        threshold_note = np.mean(note_positives) / max_note if note_positives else 0.5
        threshold_x = max(min(threshold_x, 0.7), 0.3)
        threshold_note = max(min(threshold_note, 0.7), 0.3)
    else:
        threshold_x = fixed_thr
        threshold_note = fixed_thr
    
    for r in analysis_results:
        # 正規化に最低下限値 0.05 を設けて 0 へばりつきを防ぐ
        norm_x = max(r["x_raw_score"] / max_x, 0.05)
        norm_note = max(r["note_raw_score"] / max_note, 0.05)
        
        # 総合スコア (仕様通りの乗算)
        total_score = norm_x * norm_note
        
        # 需要スコア（生データの合算）と Priority Score
        demand_score = r["x_raw_score"] + r["note_raw_score"]
        supply = (supply_counts or {}).get(r["keyword"], 0)
        priority_score = calculate_priority_score(demand_score, supply)
        
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
            status=status,
            supply_count=supply,
            priority_score=round(priority_score, 4)
        )
        
    print(f"分析完了: {len(analysis_results)} 件のデータを処理し、データベースに保存しました。")

async def run_analysis_pipeline():
    """バッチ実行全体（データ収集 -> フィルタリング -> 突合・分析）を管理します。"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    db.update_batch_status("running", "突合・分析処理を実行中...", 91)
    try:
        await _prepare_dynamic_negatives()
        await analyze_and_score_trends(date_str)
        db.save_cooccurrence_snapshot(date_str)
        db.update_batch_status("success", "分析処理が正常に完了しました。", 100)
    except Exception as e:
        print(f"分析プロセス中にエラーが発生しました: {e}")
        db.update_batch_status("failed", f"エラー発生: {str(e)}", 100)
        raise e

if __name__ == "__main__":
    asyncio.run(run_analysis_pipeline())

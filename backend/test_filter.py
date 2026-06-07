import asyncio
from sentence_transformers import SentenceTransformer, util
import db

async def test():
    db.init_db()
    
    # 改善されたターゲットテーマ（IT技術キーワード凝縮）
    target_themes = [
        "プログラミング、ソフトウェア開発、システム設計、コーディング、ソースコード、アルゴリズム",
        "AI、人工知能、機械学習、ディープラーニング、LLM、ChatGPT、画像生成、自動化、自然言語処理",
        "ITツール、業務効率化、生産性向上、DX、自動化スクリプト、SaaS、ソフトウェア、アプリケーション",
        "Web開発、アプリ開発、クラウド、データベース、インフラ、フロントエンド、バックエンド"
    ]
    
    # さらに強化されたネガティブテーマ（ノイズを吸い取るための設定）
    negative_themes = [
        "スポーツ、自転車レース、ツールドフランス、ツールド、ロードバイク、陸上、野球、サッカー、運動、大会",
        "店舗、中古買取、リサイクルショップ、中古ツール、工具、ツールオフ、販売、オークション、一般雑貨",
        "行政、土木工事、都市計画、開発局、開発行為、開発許可、道路、インフラ整備、土地開発、宅地開発",
        "日常生活、雑談、挨拶、感情、天気、旅行、京都、鹿児島、地域名、観光地、修学旅行、学校行事",
        "エンタメ、芸能人、テレビ、音楽、映画、アニメ、アイドル、ゲーム、バズワード、キャラクター、声優"
    ]
    
    keywords = [
        "ツールドフランス", # ノイズ
        "ツールオフ",       # ノイズ
        "ツールド福島",     # ノイズ
        "開発行為",         # ノイズ
        "開発局",           # ノイズ
        "ツールボックス",   # ノイズ
        "鹿児島市内",       # ノイズ
        "修学旅行回",       # ノイズ
        "ai 画像生成",      # 意図したデータ
        "aiチェッカー",     # 意図したデータ
        "効率化を図る",     # 意図したデータ
        "プログラミングツール", # 意図したデータ
        "Python自動化",     # 意図したデータ
        "開発言語"          # 意図したデータ
    ]
    
    model = SentenceTransformer("intfloat/multilingual-e5-small")
    
    print("--- 改善ロジック案4 (凝縮テーマ + 強化ネガティブテーマ + マージン付き相対比較) ---")
    
    passage_targets = [f"passage: {t}" for t in target_themes]
    passage_negatives = [f"passage: {t}" for t in negative_themes]
    
    target_embeddings = model.encode(passage_targets, convert_to_tensor=True)
    negative_embeddings = model.encode(passage_negatives, convert_to_tensor=True)
    
    for kw in keywords:
        query_text = f"query: {kw}"
        query_embedding = model.encode(query_text, convert_to_tensor=True)
        
        # ターゲット類似度
        target_scores = util.cos_sim(query_embedding, target_embeddings)[0]
        max_target_score = float(target_scores.max().cpu().item())
        
        # ネガティブ類似度
        negative_scores = util.cos_sim(query_embedding, negative_embeddings)[0]
        max_negative_score = float(negative_scores.max().cpu().item())
        
        diff = max_target_score - max_negative_score
        
        # 判定基準: ターゲット類似度が高く、かつネガティブよりも一定マージン(0.02)以上高いこと
        # かつ最低しきい値(0.80)を超えていること
        is_relevant = (diff >= 0.02) and (max_target_score >= 0.81)
        
        print(f"[{kw}]")
        print(f"  Target Score  : {max_target_score:.4f}")
        print(f"  Negative Score: {max_negative_score:.4f}")
        print(f"  Diff (T - N)  : {diff:.4f}")
        print(f"  Decision      : {'採用 (True)' if is_relevant else '除外 (False)'}")

if __name__ == "__main__":
    asyncio.run(test())

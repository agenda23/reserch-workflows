import os
from sentence_transformers import SentenceTransformer, util
import db

# グローバル変数でモデルを保持（シングルトンパターン）
_MODEL_INSTANCE = None
_DYNAMIC_NEGATIVE_HEADLINES = None

def get_model():
    """SentenceTransformerモデルのシングルトンインスタンスを取得します。"""
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        model_name = "intfloat/multilingual-e5-small"
        print(f"NLPモデル ({model_name}) をロードしています...")
        
        # Docker環境内でモデルキャッシュディレクトリを明示的にマウントできるようにする
        # デフォルトは ~/.cache/huggingface/hub/
        _MODEL_INSTANCE = SentenceTransformer(model_name)
        print("NLPモデルのロードが完了しました。")
    return _MODEL_INSTANCE

def calculate_similarity(keyword: str, themes: list) -> float:
    """キーワードとターゲットテーマ群の間の最大コサイン類似度を算出します。"""
    if not themes:
        return 0.0
        
    model = get_model()
    
    # multilingual-e5-small の推奨フォーマット (query: と passage: を付与)
    query_text = f"query: {keyword}"
    passage_texts = [f"passage: {theme}" for theme in themes]
    
    # ベクトル化
    query_embedding = model.encode(query_text, convert_to_tensor=True)
    passage_embeddings = model.encode(passage_texts, convert_to_tensor=True)
    
    # コサイン類似度の計算
    cos_scores = util.cos_sim(query_embedding, passage_embeddings)[0]
    
    # 最大類似度スコアを取得
    max_score = float(cos_scores.max().cpu().item())
    return max_score

def set_dynamic_negative_headlines(headlines: list):
    """バッチ実行時に取得した時事ニュースヘッドラインをキャッシュします。"""
    global _DYNAMIC_NEGATIVE_HEADLINES
    _DYNAMIC_NEGATIVE_HEADLINES = headlines if headlines else None

def get_dynamic_negative_headlines() -> list:
    """キャッシュされた動的ネガティブヘッドラインを返します。"""
    return _DYNAMIC_NEGATIVE_HEADLINES or []

def check_keyword_relevance(keyword: str) -> bool:
    """キーワードが現在のシステム設定にあるターゲットテーマに合致するか判定します（相対比較ロジック）。"""
    settings = db.get_settings()
    themes = settings.get("target_themes", [])
    negatives = list(settings.get("negative_themes", [
        "スポーツ、自転車レース、ツールドフランス、ツールド、ロードバイク、陸上、野球、サッカー、運動、大会",
        "店舗、中古買取、リサイクルショップ、中古ツール、工具、ツールオフ、販売、オークション、一般雑貨",
        "行政、土木工事、都市計画、開発局、開発行為、開発許可、道路、インフラ整備、土地開発、宅地開発",
        "日常生活、雑談、挨拶、感情、天気、旅行、京都、鹿児島、地域名、観光地、修学旅行、学校行事",
        "エンタメ、芸能人、テレビ、音楽、映画、アニメ、アイドル、ゲーム、バズワード、キャラクター、声優"
    ]))
    threshold = float(settings.get("similarity_threshold", 0.81))
    
    # NGワードによる簡易前処理フィルタリング（部分一致）
    ng_words = settings.get("ng_keywords", [])
    for ng in ng_words:
        if ng in keyword:
            print(f"NGワード検知により除外: [{keyword}] -> NG: {ng}")
            return False
            
    # NLPによる意味類似度判定 (ターゲット vs ネガティブ)
    max_target_score = calculate_similarity(keyword, themes)
    max_negative_score = calculate_similarity(keyword, negatives)

    # 動的ネガティブテーマ（当日の時事ニュース）との類似度も加味
    dynamic_headlines = get_dynamic_negative_headlines()
    max_dynamic_score = 0.0
    if dynamic_headlines:
        max_dynamic_score = calculate_similarity(keyword, dynamic_headlines)
        max_negative_score = max(max_negative_score, max_dynamic_score)
    
    diff = max_target_score - max_negative_score
    
    # ターゲット類似度がネガティブよりも一定マージン(0.02)以上高く、かつ閾値を超えていること
    is_relevant = (diff >= 0.02) and (max_target_score >= threshold)
    
    dynamic_info = f", Dynamic: {max_dynamic_score:.4f}" if dynamic_headlines else ""
    print(f"NLP判定結果: [{keyword}] -> Target: {max_target_score:.4f}, Negative: {max_negative_score:.4f}{dynamic_info}, Diff: {diff:.4f} (しきい値: {threshold}) -> 採用: {is_relevant}")
    return is_relevant

# UIシミュレータ用のヘルパー
def test_similarity_simulator(keyword: str, themes: list) -> dict:
    """設定画面テスト用に、各テーマごとの類似度内訳を算出します。"""
    if not themes:
        return {"max_score": 0.0, "details": []}
        
    model = get_model()
    query_text = f"query: {keyword}"
    passage_texts = [f"passage: {theme}" for theme in themes]
    
    query_embedding = model.encode(query_text, convert_to_tensor=True)
    passage_embeddings = model.encode(passage_texts, convert_to_tensor=True)
    
    cos_scores = util.cos_sim(query_embedding, passage_embeddings)[0]
    
    details = []
    for theme, score_tensor in zip(themes, cos_scores):
        score = float(score_tensor.cpu().item())
        details.append({
            "theme": theme,
            "score": round(score, 4)
        })
        
    # スコアの高い順にソート
    details = sorted(details, key=lambda x: x["score"], reverse=True)
    max_score = details[0]["score"] if details else 0.0
    
    return {
        "max_score": max_score,
        "details": details
    }

if __name__ == "__main__":
    # 単体動作テスト
    db.init_db()
    test_kw = "PythonでExcel自動化"
    test_themes = ["ソフトウェア開発", "業務効率化", "料理レシピ"]
    print(f"テスト実行: '{test_kw}' vs {test_themes}")
    result = test_similarity_simulator(test_kw, test_themes)
    print(result)

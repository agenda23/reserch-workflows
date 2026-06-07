from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import db
import scraper
import analyzer
import local_filter

app = FastAPI(title="トレンドキーワード自動抽出・分析システム API")

# CORSの設定 (Viteアプリからの接続用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境のためすべて許可。本番では制限が望ましい
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 起動時にデータベースと初期設定を登録
@app.on_event("startup")
def startup_event():
    db.init_db()
    db.reset_stuck_batch_status()

# ----------------- Pydantic モデル -----------------

class SettingsModel(BaseModel):
    seed_keywords: List[str]
    target_themes: List[str]
    ng_keywords: List[str]
    similarity_threshold: float
    note_category: str
    quadrant_mode: str = "fixed"
    quadrant_fixed_threshold: float = 0.5

class SimilarityTestRequest(BaseModel):
    keyword: str

# ----------------- エンドポイント -----------------

@app.get("/")
def read_root():
    return {"message": "Trend Keywords Analysis API is running."}

@app.get("/api/trends")
def get_trends(date: Optional[str] = None):
    """分析結果のデータを取得します。日付指定がない場合は全件を取得します。"""
    try:
        results = db.get_keyword_analysis(date)
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データの取得に失敗しました: {str(e)}")

@app.get("/api/note-hashtags")
async def get_note_hashtags(with_diff: bool = False):
    """収集されたnoteハッシュタグ統計データを取得します。"""
    try:
        results = db.get_all_note_hashtags()
        if with_diff:
            for h in results:
                h["diff"] = db.get_related_tags_diff(h["hashtag"])
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ハッシュタグデータの取得に失敗しました: {str(e)}")

@app.get("/api/hashtag-cooccurrence")
def get_hashtag_cooccurrence(seeds: str = ""):
    """シードタグと共起するキーワードを like_count 重み付きで返します。"""
    try:
        if seeds:
            seed_list = [s.strip() for s in seeds.split(",") if s.strip()]
        else:
            seed_list = db.get_settings().get("seed_keywords", [])

        result = {}
        for seed in seed_list:
            result[seed] = db.get_cooccurrence_tags_with_status(seed, top_n=20)

        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"共起タグデータの取得に失敗しました: {str(e)}")

@app.get("/api/hashtag-history/{hashtag}")
def get_hashtag_history_api(hashtag: str, limit: int = 10):
    """指定ハッシュタグの投稿件数推移履歴を返します。"""
    try:
        history = db.get_hashtag_history(hashtag, limit=limit)
        return {"status": "success", "data": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ハッシュタグ履歴の取得に失敗しました: {str(e)}")

@app.get("/api/settings", response_model=SettingsModel)
def get_settings():
    """現在のシステム設定を取得します。"""
    try:
        settings = db.get_settings()
        return {
            "seed_keywords": settings.get("seed_keywords", []),
            "target_themes": settings.get("target_themes", []),
            "ng_keywords": settings.get("ng_keywords", []),
            "similarity_threshold": float(settings.get("similarity_threshold", 0.81)),
            "note_category": settings.get("note_category", "technology"),
            "quadrant_mode": settings.get("quadrant_mode", "fixed"),
            "quadrant_fixed_threshold": float(settings.get("quadrant_fixed_threshold", 0.5)),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定の取得に失敗しました: {str(e)}")

@app.post("/api/settings")
def update_settings(settings: SettingsModel):
    """システム設定を更新します。"""
    try:
        db.update_setting("seed_keywords", settings.seed_keywords)
        db.update_setting("target_themes", settings.target_themes)
        db.update_setting("ng_keywords", settings.ng_keywords)
        db.update_setting("similarity_threshold", settings.similarity_threshold)
        db.update_setting("note_category", settings.note_category)
        db.update_setting("quadrant_mode", settings.quadrant_mode)
        db.update_setting("quadrant_fixed_threshold", settings.quadrant_fixed_threshold)
        return {"status": "success", "message": "設定を保存しました。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定の保存に失敗しました: {str(e)}")

@app.post("/api/settings/test-similarity")
def test_similarity(payload: SimilarityTestRequest):
    """設定されたターゲットテーマと入力された単語の類似度を計算しテストします。"""
    try:
        settings = db.get_settings()
        themes = settings.get("target_themes", [])
        
        # 類似度計算
        result = local_filter.test_similarity_simulator(payload.keyword, themes)
        
        # ネガティブ類似度も計算
        negatives = settings.get("negative_themes", [])
        neg_result = local_filter.test_similarity_simulator(payload.keyword, negatives)
        
        # しきい値との比較判定（相対比較）
        threshold = float(settings.get("similarity_threshold", 0.81))
        diff = result["max_score"] - neg_result["max_score"]
        is_relevant = (diff >= 0.02) and (result["max_score"] >= threshold)
        
        # NGワードに引っかかっていないかチェック
        ng_keywords = settings.get("ng_keywords", [])
        is_ng = any(ng in payload.keyword for ng in ng_keywords)
        
        return {
            "keyword": payload.keyword,
            "max_score": result["max_score"],
            "is_relevant": is_relevant and not is_ng,
            "is_ng_word": is_ng,
            "details": result["details"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"類似度テストの実行に失敗しました: {str(e)}")

# ----------------- バックグラウンドバッチ処理 -----------------

async def execute_batch_task():
    """非同期で実行するデータ収集・分析タスク。"""
    try:
        print("バックグラウンド収集・分析バッチを開始します。")
        # 1. 収集タスクの実行
        await scraper.run_collection()
        # 2. 分析タスクの実行
        await analyzer.run_analysis_pipeline()
        print("バックグラウンドバッチ処理がすべて完了しました。")
    except Exception as e:
        print(f"バックグラウンドバッチ処理中にエラーが発生しました: {e}")
        db.update_batch_status("failed", f"エラーにより停止: {str(e)}", 100)

@app.post("/api/run-batch")
def run_batch(background_tasks: BackgroundTasks):
    """データ収集・分析バッチを手動で実行します（非同期処理）。"""
    status = db.get_batch_status()
    if status["status"] == "running":
        return {"status": "error", "message": "現在、別の収集バッチが実行中です。"}
        
    # バックグラウンドで非同期タスクとして実行
    background_tasks.add_task(execute_batch_task)
    
    # 即座にレスポンスを返す（処理自体は非同期で動く）
    db.update_batch_status("running", "バッチ実行をスケジュール中...", 5)
    return {"status": "success", "message": "データ収集・分析バッチを開始しました。"}

@app.get("/api/batch-status")
def get_batch_status():
    """バッチ実行の進捗と状況を取得します。"""
    try:
        status = db.get_batch_status()
        return {"status": "success", "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ステータスの取得に失敗しました: {str(e)}")

# トレンドキーワード自動抽出・分析システム タスクリスト

本システムの開発におけるタスクリストです。実装中に進捗を随時アップデートします。

## 進捗ステータス凡例
- `[ ]` 未着手 (Uncompleted)
- `[/]` 進行中 (In progress)
- `[x]` 完了 (Completed)

---

## タスク一覧

### 1. Dockerインフラ構成
- [x] `backend/requirements.txt` の作成
- [x] `backend/Dockerfile` の作成
- [x] `docker-compose.yml` の作成
- [x] `frontend/Dockerfile` の作成
- [x] コンテナの初期ビルドテスト

### 2. データベースと収集モジュールの実装
- [x] `backend/db.py` の実装（SQLiteテーブル初期化・CRUD関数、`settings` / `batch_status` テーブルの追加）
- [x] `backend/scraper.py` の実装（Yahoo!リアルタイムトレンド検索およびnoteカテゴリ別人気記事の収集、シードワード・Bot対策対応）

### 3. フィルタリングと分析モジュールの実装
- [x] `backend/local_filter.py` の実装（Sentence Transformersによる類似度フィルタリング。DB設定テーマとしきい値の動的反映）
- [x] `backend/analyzer.py` の実装（データ突合・スコアリング・4象限分類）

### 4. APIサーバーの実装
- [x] `backend/main.py` の実装（FastAPIによるデータ取得API、設定取得・保存API、類似度シミュレータAPI、非同期バッチ実行・詳細進捗ステータスAPI。CORS設定の適用）

### 5. フロントエンドダッシュボード・設定UIの実装
- [x] `frontend/` の作成とVite + React + TypeScriptプロジェクトの初期化
- [x] `frontend/vite.config.ts` のプロキシ設定（backend:8000への転送）
- [x] Tailwind CSS および `shadcn/ui` の初期化と設定（`tailwind.config.js`, `postcss.config.js`）
- [x] `shadcn/ui` 必要コンポーネントのインストール（`button`, `card`, `table`, `tabs`, `slider`, `toast` の手動配置）
- [x] `frontend/src/App.tsx` の実装（メインレイアウト・タブ制御）
- [x] `frontend/src/components/Dashboard.tsx` の実装（Rechartsマトリクス, キーワードテーブル, グラフ連携スクロール, バッチ進捗プログレス表示）
- [x] `frontend/src/components/Settings.tsx` の実装（各種設定管理フォーム, 類似度テストシミュレータUI）

### 6. 全体検証
- [x] `docker compose up` での全コンテナ起動テスト
- [x] Web UIからの設定保存テスト
- [x] 類似度シミュレータの動作確認
- [x] Web UIからのバッチ手動実行と詳細進捗（ログ）のリアルタイム更新、およびデータ再読込の連携検証

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

### 7. プラットフォーム機能の拡張とアプローチ変更
- [x] noteハッシュタグ統計機能のデータベース設計およびCRUD実装
- [x] note API v2 経由でのハッシュタグ統計（投稿件数・関連ハッシュタグ）取得機能の実装
- [x] フロントエンド「ハッシュタグ調査」UI画面の新規作成とApp.tsxへの統合
- [x] note先行・X話題性突合アプローチへの設計変更とスクレイパー・分析処理の刷新
- [x] 新アルゴリズムによる動作検証と全ドキュメントのアップデート

### 8. 改善実装計画（Playwrightステルス・実用性強化版）
- [x] フェーズ1: Playwrightステルス化 & 収集ソース拡張（Qiita/Zenn/Brain/Tips）
- [x] フェーズ2: 動的ネガティブテーマ自動生成（時事RSS + E5類似度減算）
- [x] フェーズ3: 供給数調査 & Priority Score実装（DBスキーマ拡張 + analyzer）
- [x] フェーズ4: UI改善（優先推奨ランキング、供給数/優先度列、クロスメディア比較）

### 9. 修正方針書対応（方法論的問題の解消）
- [x] P1: 候補キーワードの優先度マップベース選定（`scraper.py`）
- [x] P2: 動的ネガティブRSSの非テック限定 + 技術用語プリフィルタ（`scraper.py`）
- [x] P4: 固定閾値モードの追加（`db.py` + `analyzer.py` + `Settings.tsx`）
- [x] P6: Yahoo!サジェストへの stealth 適用（`scraper.py`）
- [x] P3-段階1: SUPPLY_BASELINE=50 による最小ベースライン導入（`analyzer.py`）
- [x] P5: ハッシュタグボーナスのNLP類似度ベース化（`analyzer.py`）
- [x] P3-段階2: Qiita検索APIによる近似供給数取得（`scraper.py`）
- [x] supply_count=0 時の Priority Score `~` プレフィックス表示（`Dashboard.tsx`）

### 10. ハッシュタグ調査機能 強化
- [x] フェーズ1: `note_hashtag_history` / `note_cooccurrence_history` テーブルと CRUD
- [x] フェーズ1: バッチ処理への履歴スナップショット保存（`scraper.py` / `analyzer.py`）
- [x] フェーズ1: API拡張（`with_diff` / `/api/hashtag-cooccurrence` / `/api/hashtag-history/{hashtag}`）
- [x] フェーズ2-4: `HashtagResearch.tsx` 3タブ構成（浮上ワード / タグ統計 / 変化ログ + Sparkline）


# トレンドキーワード自動抽出・分析システム (Trend Keyword Auto-Extraction & Analysis System)

X（旧Twitter / Yahoo!リアルタイムトレンド）のバズワードと、note（techカテゴリ人気記事）の需要データを自動収集・突合し、ローカルNLP（意味分析）を用いて「今、技術トレンドとして本当に注目すべきキーワード」を抽出・分類するダッシュボードシステムです。

---

## 🚀 主な機能

1.  **マルチデータソース収集**:
    *   **X (Yahoo!リアルタイムトレンド)**: Playwrightを使用し、トレンドワードと詳細なポスト数を自動スクレイピング。
    *   **note (人気記事)**: v1 APIを活用して、特定カテゴリ（デフォルト: `tech`）の人気記事タイトルとスキ数を収集。
2.  **完全無料のローカルNLPフィルタリング**:
    *   有料LLM APIを使用せず、軽量かつ高性能な多言語埋め込みモデル `intfloat/multilingual-e5-small` をローカルCPU上で実行。
    *   「ターゲットテーマ」との文脈類似度を判定し、エンタメ情報や日常ニュースなどの無関係なトレンドを完全自動排除。
3.  **4象限マトリクス分析 (Recharts)**:
    *   Xの「拡散度 (X Score)」とnoteの「実需 (note Score)」を掛け合わせ、キーワードを4つの象限に自動マッピング。
        *   **第1象限（スター候補）**: Xバズ・note需要ともに高い最強のトレンド。
        *   **第2象限（安定需要）**: noteで安定して読まれている実需系テーマ。
        *   **第3象限（対象外）**: 類似度が低く、技術トレンドから外れるもの。
        *   **第4象限（急上昇トレンド）**: Xで急上昇しているが、まだnoteでの発信が少ない先行者利益エリア。
4.  **直感的なWeb UI設定 & シミュレーター**:
    *   「しきい値」「ターゲットテーマ」「NGワード」「収集カテゴリ」をダッシュボード上から随時調整可能。
    *   現在の設定値で特定のキーワードがフィルタリングを通過するかテストできる「類似度シミュレーター」を同梱。

---

## 🛠 テクノロジースタック

*   **インフラ**: Docker / Docker Compose
*   **バックエンド**: Python 3.11 / FastAPI / SQLite / Playwright (スクレイピング) / PyTorch / Sentence Transformers (`multilingual-e5-small`)
*   **フロントエンド**: Vite / React / TypeScript / Tailwind CSS / `shadcn/ui` / Recharts

---

## 📦 ディレクトリ構成

```text
.
├── backend/                  # FastAPIバックエンド
│   ├── Dockerfile
│   ├── requirements.txt      # 依存パッケージ
│   ├── main.py               # APIエントリーポイント & ルーティング
│   ├── db.py                 # SQLiteデータベース操作・CRUD
│   ├── scraper.py            # Playwrightスクレイピング & note API連携
│   ├── local_filter.py       # E5モデルによる類似度計算
│   └── analyzer.py           # スコア計算 & 4象限判定ロジック
├── frontend/                 # Reactフロントエンド
│   ├── Dockerfile
│   ├── vite.config.ts        # バックエンドへのAPIプロキシ設定
│   ├── src/
│   │   ├── App.tsx           # メインコンポーネント (Tabs構成)
│   │   ├── components/       # ダッシュボード & 設定画面UI
│   │   └── ui/               # shadcn/uiベースのUIコンポーネント
├── docs/                     # 仕様書・設計書・マニュアル
└── docker-compose.yml        # Docker Compose設定
```

---

## ⚙️ セットアップ & 起動手順

### 前提条件
*   **Docker** および **Docker Compose** がインストールされていること。

### 1. アプリケーションの起動
リポジトリのルートディレクトリで以下のコマンドを実行します。
```bash
docker compose up -d --build
```
*※初回起動時は、約300MBのNLPモデルのダウンロードやブラウザエンジンのインストールが行われるため、起動まで数分かかる場合があります。*

### 2. UIへのアクセス
起動後、ブラウザで以下のURLにアクセスします。
*   **Web UI (ダッシュボード)**: [http://localhost:5173/](http://localhost:5173/)
*   **API ドキュメント (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. アプリケーションの停止
```bash
docker compose down
```

---

## 📘 各種ドキュメント

より詳細な情報や仕様については、以下のドキュメントを参照してください。

*   **ユーザーマニュアル**: [docs/トレンドキーワード自動抽出・分析システム ユーザーマニュアル.md](docs/%E3%83%88%E3%83%AC%E3%83%B3%E3%83%89%E3%82%AD%E3%83%BC%E3%83%AF%E3%83%BC%E3%83%89%E8%87%AA%E5%8B%95%E6%8A%BD%E5%87%BA%E3%83%BB%E5%88%86%E6%9E%90%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%20%E3%83%A6%E3%83%BC%E3%82%B6%E3%83%BC%E3%83%9E%E3%83%8B%E3%83%A5%E3%82%A2%E3%83%AB.md)
*   **要件定義・仕様書**: [docs/トレンドキーワード自動抽出・分析システム 要件定義・仕様書.md](docs/%E3%83%88%E3%83%AC%E3%83%B3%E3%83%89%E3%82%AD%E3%83%BC%E3%83%AF%E3%83%BC%E3%83%89%E8%87%AA%E5%8B%95%E6%8A%BD%E5%87%BA%E3%83%BB%E5%88%86%E6%9E%90%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%20%E3%85%E4%BB%B6%E5%AE%9A%E7%BE%A9%E3%83%BB%E4%BB%95%E6%A7%23%E6%9B%B8.md)
*   **実装計画書**: [docs/トレンドキーワード自動抽出・分析システム 実装計画書.md](docs/%E3%83%88%E3%83%AC%E3%83%B3%E3%83%89%E3%82%AD%E3%83%BC%E3%83%AF%E3%83%BC%E3%83%89%E8%87%AA%E5%8B%95%E6%8A%BD%E5%87%BA%E3%83%BB%E5%88%86%E6%9E%90%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%20%E5%AE%9F%E8%A3%85%E8%A8%88%E7%94%BB%E6%9B%B8.md)

---

## 📄 ライセンス

本プロジェクトは [MIT ライセンス](LICENSE) の下で提供されています。

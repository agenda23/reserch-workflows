import asyncio
import re
import urllib.parse
import httpx
from playwright.async_api import async_playwright
import db

# ユーザーエージェント一覧（ランダムに偽装するため）
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
]

def clean_tweet_count(count_str: str) -> int:
    """ツイート数文字列（例: '12,345件', '5,000 tweets'）を数値に変換します。"""
    if not count_str:
        return 0
    # 数字部分だけを抽出
    nums = re.findall(r'\d+', count_str.replace(',', ''))
    if nums:
        return int(nums[0])
    return 0

async def scrape_yahoo_trends():
    """Yahoo!リアルタイム検索からトレンドランキングと感情分析比率をスクレイピングします。"""
    print("Yahoo!リアルタイムトレンドのスクレイピングを開始します...")
    trends = []

    async with async_playwright() as p:
        # ブラウザをヘッドレスモードで起動
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        # コンテキストにUAとロケールを設定して人間らしくみせる
        context = await browser.new_context(
            user_agent=USER_AGENTS[0],
            locale="ja-JP",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        try:
            # Yahoo!リアルタイム検索トップへ遷移
            await page.goto("https://search.yahoo.co.jp/realtime", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000) # 念のためのウェイト
            
            # トレンドリスト要素の取得
            # Yahoo!リアルタイム検索のトレンドは通常「.Trend_item」または「#trend」などの中にある
            # セレクタを広めに指定し、ヒットした要素からキーワードとツイート数を抽出
            # 2026年現在のYahoo!リアルタイム検索は、通常「ol」または「ul」でトレンドが並ぶ
            trend_elements = await page.query_selector_all("xpath=//a[contains(@href, 'realtime/search')]/ancestor::li")
            
            seen_keywords = set()
            rank = 1
            for element in trend_elements:
                text = await element.inner_text()
                if not text:
                    continue
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if not lines:
                    continue
                
                # 通常「1」「キーワード名」「ツイート数」のような複数行になっている
                keyword = ""
                tweet_count = 0
                
                if len(lines) >= 2:
                    # 1行目が順位の場合、2行目がキーワード
                    if lines[0].isdigit():
                        keyword = lines[1]
                        if len(lines) >= 3:
                            tweet_count = clean_tweet_count(lines[2])
                    else:
                        keyword = lines[0]
                        tweet_count = clean_tweet_count(lines[1])
                else:
                    keyword = lines[0]

                # 余計な記号や空文字、重複を排除
                keyword = keyword.replace("#", "").strip()
                if not keyword or keyword in seen_keywords or len(keyword) < 2:
                    continue
                if keyword.isdigit(): # 数字のみは除外
                    continue

                seen_keywords.add(keyword)
                trends.append({
                    "rank": rank,
                    "keyword": keyword,
                    "tweet_count": tweet_count,
                    "positive_ratio": 0.5 # デフォルト値
                })
                rank += 1
                if len(trends) >= 30: # 上位30件に制限
                    break
            
            print(f"トレンドキーワードを {len(trends)} 件抽出しました。感情比率を収集します...")
            
            # 上位10件について、詳細ページに遷移して感情比率を取得する
            # アクセス過多を防ぐため、1件ごとにランダムウェイトを入れる
            for i in range(min(10, len(trends))):
                item = trends[i]
                kw = item["keyword"]
                encoded_kw = urllib.parse.quote(kw)
                detail_url = f"https://search.yahoo.co.jp/realtime/search?p={encoded_kw}"
                
                try:
                    await page.goto(detail_url, wait_until="networkidle", timeout=20000)
                    await page.wait_for_timeout(1000)
                    
                    # 感情割合（ポジティブ比率）の取得
                    sentiment_element = await page.query_selector(".Sentiment")
                    if sentiment_element:
                        sentiment_text = await sentiment_element.inner_text()
                        # 'ポジティブ 80%' のようなテキストを抽出
                        match = re.search(r'ポジティブ\s*(\d+)%', sentiment_text)
                        if match:
                            item["positive_ratio"] = float(match.group(1)) / 100.0
                            print(f"感情分析成功: [{kw}] -> ポジティブ {match.group(1)}%")
                            
                    # ツイート数の取得
                    tweet_element = await page.query_selector("xpath=//*[contains(text(), '件のポスト')]")
                    if not tweet_element:
                        tweet_element = await page.query_selector("xpath=//*[contains(text(), '件のツイート')]")
                    if tweet_element:
                        tweet_text = await tweet_element.inner_text()
                        nums = re.findall(r'[\d,]+', tweet_text)
                        if nums:
                            val = int(nums[0].replace(',', ''))
                            item["tweet_count"] = val
                            print(f"ツイート数詳細パース成功: [{kw}] -> {val}件")
                except Exception as e:
                    print(f"詳細情報（感情・ツイート数）取得失敗（スキップ）: {kw} - {e}")
                
                # 負荷軽減のためのウェイト
                await asyncio.sleep(1.5)

        except Exception as e:
            print(f"Yahoo!リアルタイムトレンドの取得中にエラーが発生しました: {e}")
        finally:
            await browser.close()
            
    return trends

async def scrape_yahoo_suggests(seed_keywords: list):
    """シードワードの検索サジェストワードを取得します。"""
    print(f"シードワード {seed_keywords} のサジェスト収集を開始します...")
    suggests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENTS[1], locale="ja-JP")
        page = await context.new_page()

        for seed in seed_keywords:
            try:
                # Yahoo!検索（またはリアルタイム検索）のトップでサジェストを取得
                # 通常のYahooトップページでインプットボックスに入力してサジェストを抜き出す
                await page.goto("https://www.yahoo.co.jp/", wait_until="networkidle", timeout=20000)
                
                # 検索窓に入力
                search_input = await page.query_selector("input[type='search']")
                if not search_input:
                    # 別の一般的なセレクタ
                    search_input = await page.query_selector("input[name='p']")
                
                if search_input:
                    await search_input.fill(seed)
                    await page.wait_for_timeout(1500) # サジェスト表示を待つ
                    
                    # サジェスト候補の取得 (Yahoo!のサジェスト要素は通常 '.SearchBox_suggestList' や 'ul' など)
                    suggest_elements = await page.query_selector_all("[role='option']")
                    for elem in suggest_elements:
                        text = await elem.inner_text()
                        text = text.strip()
                        # シードワード自体を含み、かつシードワードと同一でないサジェストワードを抽出
                        if text and text != seed and seed in text:
                            # タブや改行をスペースに置換
                            cleaned_text = " ".join(text.split())
                            suggests.append({
                                "keyword": cleaned_text,
                                "tweet_count": 0, # サジェストはツイート数不明のため0
                                "positive_ratio": 0.5
                            })
                print(f"シードワード [{seed}] から {len(suggests)} 件のサジェストを取得しました。")
            except Exception as e:
                print(f"シードワード [{seed}] のサジェスト取得中にエラーが発生しました: {e}")
            
            await asyncio.sleep(2.0)
            
        await browser.close()
        
    return suggests

async def fetch_note_ranking(category: str = "technology"):
    """noteのカテゴリ別人気記事ランキングをAPI経由で取得します。"""
    print(f"note人気記事（カテゴリ: {category}）の取得を開始します...")
    articles = []
    
    # カテゴリキーのエイリアス変換 (technology -> tech等)
    category_map = {
        "tech": "tech",
        "technology": "tech",
        "business": "tech", # ビジネスAPIが現在利用できない場合のフォールバックとしてtechを指定
        "money": "money",
        "work": "work"
    }
    cat_key = category_map.get(category.lower(), "tech")
    
    # note非公式人気記事API v1 エンドポイント
    url = f"https://note.com/api/v1/categories/{cat_key}?note_intro_only=true"
    
    headers = {
        "User-Agent": USER_AGENTS[2],
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("notes", [])
                
                for item in items:
                    # ハッシュタグのパース
                    hashtags = []
                    hashtag_notes = item.get("hashtag_notes", [])
                    for hn in hashtag_notes:
                        tag_name = hn.get("hashtag", {}).get("name")
                        if tag_name:
                            hashtags.append(tag_name)
                    
                    articles.append({
                        "article_id": str(item.get("id")),
                        "title": item.get("name", ""),
                        "tags": hashtags,
                        "like_count": item.get("like_count", 0),
                        "category": cat_key
                    })
                print(f"noteから {len(articles)} 件の記事を取得しました。")
            else:
                print(f"note APIがエラーステータスを返しました: {response.status_code}")
                
    except Exception as e:
        print(f"noteデータの取得中にエラーが発生しました: {e}")
        
    return articles

async def run_collection():
    """データ収集プロセスを統合実行し、データベースへ保存します。"""
    # データベース初期化（まだされてない場合）
    db.init_db()
    
    # 既存の古いスクレイピングデータをクリア
    db.clear_scraped_data()
    
    # 設定の取得
    settings = db.get_settings()
    seed_keywords = settings.get("seed_keywords", ["ツール", "AI"])
    note_cat = settings.get("note_category", "technology")
    
    db.update_batch_status("running", "データ収集を開始...", 10)
    
    # 1. Yahoo!トレンドスクレイピング
    db.update_batch_status("running", "Yahoo!リアルタイムトレンドを収集中...", 20)
    yahoo_trends = await scrape_yahoo_trends()
    
    # 2. Yahoo!サジェストスクレイピング
    db.update_batch_status("running", "シードワードのサジェストを収集中...", 50)
    suggest_trends = await scrape_yahoo_suggests(seed_keywords)
    
    # 収集データをデータベースに保存
    db.update_batch_status("running", "収集データをデータベースに保存中...", 70)
    
    # 重複防止を考慮してトレンドデータを登録
    all_x_keywords = {}
    for item in (yahoo_trends + suggest_trends):
        kw = item["keyword"]
        # 重複した場合はツイート数が多い方を優先
        if kw not in all_x_keywords or item["tweet_count"] > all_x_keywords[kw]["tweet_count"]:
            all_x_keywords[kw] = item
            
    for item in all_x_keywords.values():
        db.insert_x_trend(
            keyword=item["keyword"],
            tweet_count=item["tweet_count"],
            positive_ratio=item["positive_ratio"]
        )
        
    # 3. note人気記事の取得
    db.update_batch_status("running", "note人気記事を取得中...", 80)
    note_articles = await fetch_note_ranking(note_cat)
    
    for article in note_articles:
        db.insert_note_ranking(
            article_id=article["article_id"],
            title=article["title"],
            tags=article["tags"],
            like_count=article["like_count"],
            category=article["category"]
        )
        
    db.update_batch_status("running", "データ収集完了", 90)
    print("データ収集プロセスが正常に完了しました。")

if __name__ == "__main__":
    # 単体実行時のテスト
    asyncio.run(run_collection())

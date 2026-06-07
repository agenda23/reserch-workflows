import asyncio
import re
import urllib.parse
import httpx
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
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

async def scrape_single_x_detail(page, keyword: str):
    """指定したキーワードについて、Yahoo!リアルタイム検索から詳細情報（ポスト数・感情比率）をスクレイピングします。"""
    # '#'を除去し、URLエンコード
    clean_kw = keyword.replace("#", "").strip()
    encoded_kw = urllib.parse.quote(clean_kw)
    detail_url = f"https://search.yahoo.co.jp/realtime/search?p={encoded_kw}"
    
    result = {
        "keyword": clean_kw,
        "tweet_count": 0,
        "positive_ratio": 0.5
    }
    
    try:
        print(f"X話題性突合中: [{clean_kw}] (URL: {detail_url})")
        await page.goto(detail_url, wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(1000) # 念のためのウェイト
        
        # 感情割合（ポジティブ比率）の取得
        sentiment_element = await page.query_selector(".Sentiment")
        if sentiment_element:
            sentiment_text = await sentiment_element.inner_text()
            match = re.search(r'ポジティブ\s*(\d+)%', sentiment_text)
            if match:
                result["positive_ratio"] = float(match.group(1)) / 100.0
                
        # ポスト数の取得
        tweet_element = await page.query_selector("xpath=//*[contains(text(), '件のポスト')]")
        if not tweet_element:
            tweet_element = await page.query_selector("xpath=//*[contains(text(), '件のツイート')]")
        if tweet_element:
            tweet_text = await tweet_element.inner_text()
            nums = re.findall(r'[\d,]+', tweet_text)
            if nums:
                result["tweet_count"] = int(nums[0].replace(',', ''))
                
        print(f"➔ 突合成功: [{clean_kw}] ➔ ポスト数: {result['tweet_count']}, ポジティブ: {result['positive_ratio']*100:.1f}%")
    except Exception as e:
        print(f"➔ 突合失敗: [{clean_kw}] - {str(e)}")
        
    return result

async def scrape_yahoo_suggests(seed_keywords: list):
    """シードワードの検索サジェストワードを取得します。"""
    print(f"シードワード {seed_keywords} のサジェスト収集を開始します...")
    suggests = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await create_stealth_page(browser)

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
                    
                    # サジェスト候補の取得 (Yahoo!のサジェスト要素は 'ul[aria-label="キーワード入力補助"] a' や '[role="option"]' など)
                    suggest_elements = await page.query_selector_all('ul[aria-label="キーワード入力補助"] a')
                    if not suggest_elements:
                        suggest_elements = await page.query_selector_all("[role='option']")
                    
                    seed_added = 0
                    for elem in suggest_elements:
                        text = await elem.inner_text()
                        text = text.strip()
                        # シードワード自体を含み、かつシードワードと同一でないサジェストワードを抽出 (大文字小文字無視)
                        if text and text.lower() != seed.lower() and (seed.lower() in text.lower()):
                            # タブや改行をスペースに置換
                            cleaned_text = " ".join(text.split())
                            # すでに suggests に入っているか確認（重複防止）
                            if not any(s["keyword"] == cleaned_text for s in suggests):
                                suggests.append({
                                    "keyword": cleaned_text,
                                    "tweet_count": 0, # サジェストはツイート数不明のため0
                                    "positive_ratio": 0.5
                                })
                                seed_added += 1
                print(f"シードワード [{seed}] から {seed_added} 件のサジェストを取得しました。")
            except Exception as e:
                print(f"シードワード [{seed}] のサジェスト取得中にエラーが発生しました: {e}")
            
            await asyncio.sleep(2.0)
            
        await browser.close()
        
    return suggests

async def create_stealth_page(browser, user_agent=None):
    """Stealthプラグインを適用してボット検知を回避したページを作成します。"""
    context = await browser.new_context(
        user_agent=user_agent or random.choice(USER_AGENTS),
        locale="ja-JP",
        viewport={"width": 1280, "height": 800}
    )
    page = await context.new_page()
    await stealth_async(page)
    return page, context

def clean_content_title(title: str) -> str:
    """記事タイトルから不要な装飾や長すぎる文字列をクレンジングし、キーワード候補を返します。"""
    if not title or len(title) < 4 or len(title) > 60:
        return ""
    # 記号や不要な文言を除外
    title = re.sub(r'【.*?】|\[.*?\]|（.*?）|\(.*?\)', '', title)
    title = re.sub(r'[!！?？★☆◇◆■□●○◎✔]', '', title)
    title = " ".join(title.split())
    title = title.strip()
    
    if len(title) > 20:
        parts = re.split(r'[,，、\s]', title)
        for part in parts:
            if 3 <= len(part) <= 15:
                return part
    return title if 3 <= len(title) <= 20 else ""

async def fetch_zenn_trends():
    """ZennのRSSフィードから最新記事のトレンドキーワードを取得します。"""
    print("Zenn RSSフィードの取得を開始します...")
    topics = []
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/xml"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://zenn.dev/feed", headers=headers, timeout=15)
            if response.status_code == 200:
                # BeautifulSoupでHTMLとしてパース (lxml等のxmlパーサー不在対応)
                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.find_all("item")
                for item in items:
                    title_elem = item.find("title")
                    if title_elem:
                        cleaned = clean_content_title(title_elem.get_text())
                        if cleaned and cleaned not in topics:
                            topics.append(cleaned)
            print(f"➔ Zenn RSSから {len(topics)} 件のトレンドキーワードを取得しました。")
    except Exception as e:
        print(f"Zenn RSS取得中にエラーが発生しました: {e}")
    return topics

async def fetch_brain_trends():
    """Brainのトップページから人気・おすすめコンテンツのキーワードを取得します。"""
    print("Brainコンテンツタイトルの取得を開始します...")
    keywords = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await create_stealth_page(browser)
        try:
            # wait_untilをdomcontentloadedにし、タイムアウトを短縮（15秒）して待機を安定化
            await page.goto("https://brain-market.com/", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000) # コンテンツ読み込みのバッファ
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # クラス名にtitleやnameが含まれるか、特定のカード要素に含まれるテキストを幅広くパース
            title_elems = soup.find_all(class_=lambda c: c and ("title" in c or "name" in c or "card__txt" in c))
            for elem in title_elems:
                text = elem.get_text(strip=True)
                cleaned = clean_content_title(text)
                if cleaned and cleaned not in keywords:
                    keywords.append(cleaned)
                    
            # 補助的に a タグ内のテキストや見出しを取得
            for tag in ["h3", "h4", "a"]:
                for elem in soup.find_all(tag):
                    # aタグの場合は一定の長さと、IT・副業的な文脈の簡易フィルタ
                    if tag == "a":
                        href = elem.get("href", "")
                        if not href or "/u/" not in href: # Brainの記事詳細URLは/u/を含む傾向
                            continue
                    text = elem.get_text(strip=True)
                    cleaned = clean_content_title(text)
                    if cleaned and cleaned not in keywords:
                        keywords.append(cleaned)
            print(f"➔ Brainから {len(keywords)} 件のコンテンツタイトル候補を取得しました。")
        except Exception as e:
            print(f"Brainトレンド取得中にエラーが発生しました: {e}")
        finally:
            await browser.close()
    return keywords

async def fetch_tips_trends():
    """Tipsの人気ランキングからコンテンツのキーワードを取得します。"""
    print("Tipsコンテンツタイトルの取得を開始します...")
    keywords = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await create_stealth_page(browser)
        try:
            # タイムアウト対策とバッファ追加 (URLを rankings に修正)
            await page.goto("https://tips.jp/rankings", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(3000)
            
            page_title = await page.title()
            print(f"Tips page title: '{page_title}'")
            
            # 404エラーの場合はトップページへフォールバック
            if "404" in page_title or "NOT FOUND" in page_title.upper():
                print("Tips rankings URLが404のため、トップページにフォールバックして収集します...")
                await page.goto("https://tips.jp/", wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)
                
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Tipsのランキングタイトル要素の収集
            title_elems = soup.find_all(class_=lambda c: c and ("title" in c or "name" in c or "ranking-item" in c or "card" in c))
            for elem in title_elems:
                text = elem.get_text(strip=True)
                cleaned = clean_content_title(text)
                if cleaned and cleaned not in keywords:
                    keywords.append(cleaned)
                    
            for tag in ["h3", "h4", "a"]:
                for elem in soup.find_all(tag):
                    if tag == "a":
                        href = elem.get("href", "")
                        if not href or "/post/" not in href: # Tipsの記事詳細URLは/post/を含む
                            continue
                    text = elem.get_text(strip=True)
                    cleaned = clean_content_title(text)
                    if cleaned and cleaned not in keywords:
                        keywords.append(cleaned)
            print(f"➔ Tipsから {len(keywords)} 件のコンテンツタイトル候補を取得しました。")
        except Exception as e:
            print(f"Tipsトレンド取得中にエラーが発生しました: {e}")
        finally:
            await browser.close()
    return keywords

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

NEWS_RSS_FEEDS = [
    "https://news.yahoo.co.jp/rss/topics/sports.xml",
    "https://news.yahoo.co.jp/rss/topics/entertainment.xml",
    "https://news.yahoo.co.jp/rss/topics/domestic.xml",
]

TECH_INDICATORS = {
    "AI", "クラウド", "プログラミング", "エンジニア", "サービス", "リリース",
    "アプリ", "スマートフォン", "API", "データ", "システム", "DX", "ITシステム",
}

def _is_tech_headline(headline: str) -> bool:
    """技術系ニュース見出しを動的ネガティブから除外します。"""
    return any(word in headline for word in TECH_INDICATORS)

async def fetch_news_headlines(max_items: int = 30) -> list:
    """時事ニュースRSSからヘッドラインを取得し、動的ネガティブテーマ候補とします。"""
    print("時事ニュースRSSヘッドラインの取得を開始します...")
    raw_headlines = []
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/xml, text/xml, */*",
    }
    try:
        async with httpx.AsyncClient() as client:
            for feed_url in NEWS_RSS_FEEDS:
                if len(raw_headlines) >= max_items:
                    break
                try:
                    response = await client.get(feed_url, headers=headers, timeout=10)
                    if response.status_code != 200:
                        continue
                    soup = BeautifulSoup(response.text, "html.parser")
                    for item in soup.find_all("item"):
                        if len(raw_headlines) >= max_items:
                            break
                        title_elem = item.find("title")
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if title and title not in raw_headlines:
                                raw_headlines.append(title)
                except Exception as e:
                    print(f"RSS取得エラー ({feed_url}): {e}")
        headlines = [h for h in raw_headlines if not _is_tech_headline(h)]
        print(f"➔ 時事ニュースから {len(headlines)} 件のヘッドラインを取得しました（技術系除外: {len(raw_headlines) - len(headlines)} 件）。")
        return headlines
    except Exception as e:
        print(f"時事ニュースRSS取得中にエラーが発生しました: {e}")
    return []

async def fetch_supply_count(keyword: str) -> int:
    """noteの既存コンテンツ数（ハッシュタグ投稿件数）を供給量として返します。"""
    clean_kw = keyword.replace("#", "").strip()
    total = 0

    cached = db.get_note_hashtag(clean_kw)
    if cached:
        total += cached.get("post_count", 0)
    else:
        hashtag_data = await fetch_note_hashtag_volume(clean_kw)
        if hashtag_data:
            total += hashtag_data.get("post_count", 0)

    return total

async def fetch_note_hashtag_volume(hashtag: str):
    """noteハッシュタグボリュームAPIから指定ハッシュタグの投稿件数と関連タグを取得します。"""
    clean_tag = hashtag.replace("#", "").strip()
    encoded_tag = urllib.parse.quote(clean_tag)
    url = f"https://note.com/api/v2/hashtags/{encoded_tag}"
    
    headers = {
        "User-Agent": USER_AGENTS[2],
        "Accept": "application/json"
    }
    
    # 負荷対策：1〜3秒のランダムスリープ
    sleep_time = random.uniform(1.0, 3.0)
    await asyncio.sleep(sleep_time)
    
    try:
        print(f"noteハッシュタグボリューム取得中: {clean_tag} (URL: {url})")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                name = data.get("name", "").replace("#", "").strip()
                count = data.get("count", 0)
                
                # 関連ハッシュタグの抽出
                related_tags = []
                for rh in data.get("relatedHashtags", []):
                    r_name = rh.get("name", "").replace("#", "").strip()
                    if r_name:
                        related_tags.append(r_name)
                        
                print(f"noteハッシュタグ取得成功: [{clean_tag}] -> 件数: {count}, 関連タグ: {len(related_tags)}件")
                return {
                    "hashtag": name or clean_tag,
                    "post_count": count,
                    "related_tags": related_tags
                }
            elif response.status_code == 404:
                print(f"noteハッシュタグが存在しません (404): {clean_tag}")
                return None
            else:
                print(f"noteハッシュタグAPIエラー (ステータス: {response.status_code}): {clean_tag}")
                return None
    except Exception as e:
        print(f"noteハッシュタグAPI例外発生: {clean_tag} - {str(e)}")
        return None

async def run_collection():
    """note先行・X突合アプローチによるデータ収集・突合プロセスを実行します。"""
    # データベース初期化（まだされてない場合）
    db.init_db()
    
    # 既存の古いスクレイピングデータをクリア
    db.clear_scraped_data()
    
    # 設定の取得
    settings = db.get_settings()
    seed_keywords = settings.get("seed_keywords", ["ツール", "AI"])
    note_cat = settings.get("note_category", "technology")
    
    # 1. note先行収集：カテゴリ人気記事の取得
    db.update_batch_status("running", "note人気記事を取得中...", 10)
    note_articles = await fetch_note_ranking(note_cat)
    for article in note_articles:
        db.insert_note_ranking(
            article_id=article["article_id"],
            title=article["title"],
            tags=article["tags"],
            like_count=article["like_count"],
            category=article["category"]
        )
        
    # 2. note先行収集：シードハッシュタグ統計の取得
    db.update_batch_status("running", "noteハッシュタグ統計を取得中...", 20)
    note_hashtags_data = []
    from datetime import date as _date
    batch_date = _date.today().strftime("%Y-%m-%d")
    for seed in seed_keywords:
        hashtag_data = await fetch_note_hashtag_volume(seed)
        if hashtag_data:
            db.insert_note_hashtag(
                hashtag=hashtag_data["hashtag"],
                post_count=hashtag_data["post_count"],
                related_tags=hashtag_data["related_tags"]
            )
            db.insert_note_hashtag_history(
                hashtag=hashtag_data["hashtag"],
                post_count=hashtag_data["post_count"],
                related_tags=hashtag_data["related_tags"],
                batch_date=batch_date,
            )
            note_hashtags_data.append(hashtag_data)
            
    # 3. Zenn トレンドの取得
    db.update_batch_status("running", "Zenn のトレンドを取得中...", 30)
    zenn_trends = await fetch_zenn_trends()
    
    # 4. Brain & Tips のランキングトレンドの取得
    db.update_batch_status("running", "Brain & Tips の売れ筋トレンドを取得中...", 40)
    brain_trends = await fetch_brain_trends()
    tips_trends = await fetch_tips_trends()
            
    # 5. Yahoo!サジェストスクレイピング (需要検索候補)
    db.update_batch_status("running", "シードワードのサジェストを収集中...", 50)
    suggest_trends = await scrape_yahoo_suggests(seed_keywords)
    
    # 6. 実需キーワードリストの抽出・マージ（優先度マップベース）
    db.update_batch_status("running", "実需キーワードを抽出・マージ中...", 60)
    candidate_map: dict[str, int] = {}

    def _add_candidate(kw: str, priority: int):
        if len(kw) >= 2 and not kw.isdigit():
            candidate_map[kw] = max(candidate_map.get(kw, 0), priority)

    for article in note_articles:
        for tag in article["tags"]:
            _add_candidate(tag, priority=5)

    for h_data in note_hashtags_data:
        for tag in h_data["related_tags"]:
            _add_candidate(tag, priority=4)

    for tag in zenn_trends:
        _add_candidate(tag, priority=3)

    for item in suggest_trends:
        _add_candidate(item["keyword"], priority=2)

    for tag in brain_trends:
        _add_candidate(tag, priority=2)
    for tag in tips_trends:
        _add_candidate(tag, priority=2)

    candidate_list = sorted(candidate_map, key=lambda k: candidate_map[k], reverse=True)[:40]
    print(f"候補キーワード {len(candidate_list)} 件を優先度順に選定しました。")
    
    # 7. Xでの話題性突合 (実需キーワードに対してX検索を順次実行)
    db.update_batch_status("running", f"実需キーワード ({len(candidate_list)}件) のX話題性を突合中...", 70)
    
    if candidate_list:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            # Stealthページを作成して利用
            page, context = await create_stealth_page(browser)
            
            for idx, kw in enumerate(candidate_list):
                # バッチの進捗表示を動的に更新
                progress = 70 + int((idx / len(candidate_list)) * 20)
                db.update_batch_status("running", f"X話題性突合中 ({idx+1}/{len(candidate_list)}): {kw}", progress)
                
                # 個別キーワードのX突合
                x_detail = await scrape_single_x_detail(page, kw)
                
                # データベースに登録
                db.insert_x_trend(
                    keyword=x_detail["keyword"],
                    tweet_count=x_detail["tweet_count"],
                    positive_ratio=x_detail["positive_ratio"]
                )
                
                # 負荷軽減のためのウェイト (1.5秒)
                await asyncio.sleep(1.5)
                
            await browser.close()
            
    db.update_batch_status("running", "データ収集・突合完了", 90)
    print("データ収集・突合プロセスが正常に完了しました。")

if __name__ == "__main__":
    # 単体実行時のテスト
    asyncio.run(run_collection())

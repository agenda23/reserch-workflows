import asyncio
import urllib.parse
from playwright.async_api import async_playwright

async def run():
    p = await async_playwright().start()
    b = await p.chromium.launch(headless=True)
    pg = await b.new_page()
    
    kw = "ゴウエモン"
    encoded_kw = urllib.parse.quote(kw)
    detail_url = f"https://search.yahoo.co.jp/realtime/search?p={encoded_kw}"
    await pg.goto(detail_url, wait_until="networkidle", timeout=30000)
    await pg.wait_for_timeout(3000)
    
    # xpath で「件のポスト」を含む要素をクエリ
    elem = await pg.query_selector("xpath=//*[contains(text(), '件のポスト')]")
    if elem:
        print("FOUND ELEMENT:", repr(await elem.inner_text()))
    else:
        # 別の可能性を考慮
        all_spans = await pg.query_selector_all("span")
        print("=== Checking first 20 spans for numbers ===")
        count = 0
        for span in all_spans:
            text = await span.inner_text()
            if text and ("件" in text or "ポスト" in text or any(c.isdigit() for c in text)):
                print(repr(text))
                count += 1
                if count >= 20:
                    break
        
    await b.close()

if __name__ == "__main__":
    asyncio.run(run())

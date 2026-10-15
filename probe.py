import asyncio, json
from pathlib import Path
from datetime import datetime, timezone
from playwright.async_api import async_playwright

URL = "https://reserve.489ban.net/client/notoyaryokan/0/plan/availability/room/stay"
OUT = Path("artifacts")
OUT.mkdir(exist_ok=True)

async def main():
    data = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "url": URL, "page_loaded": False, "room_inventory_confirmed": False}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(locale="ja-JP", viewport={"width": 1280, "height": 900})
        try:
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(6000)
            body = await page.locator("body").inner_text(timeout=10000)
            data["http_status"] = response.status if response else None
            data["title"] = await page.title()
            data["page_loaded"] = bool(response and response.ok and ("能登屋" in body or "notoya" in body.lower()))
            data["legend_found"] = all(w in body for w in ("空室あり", "満室", "受付できません"))
            data["room_names_found"] = [r for r in ("本館川側10畳", "本館川側7.5畳", "本館川側2間") if r in body]
            data["excerpt"] = body[:1500]
            await page.screenshot(path=str(OUT / "calendar.png"), full_page=True)
        except Exception as e:
            data["error"] = str(e)[:500]
        finally:
            await browser.close()
    (OUT / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not data["page_loaded"]:
        raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())

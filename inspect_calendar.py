import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://reserve.489ban.net/client/notoyaryokan/0/plan/availability/room/stay"
OUT = Path("artifacts")
OUT.mkdir(exist_ok=True)
ROOMS = ["本館川側10畳客室", "本館川側7.5畳和室", "本館川側2間客室"]

async def main():
    report = {"url": URL, "rooms": {}, "note": "DOM inspection only; does not infer vacancies or submit reservations"}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(locale="ja-JP", viewport={"width": 1400, "height": 1000})
        try:
            resp = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(7000)
            report["http_status"] = resp.status if resp else None
            report["title"] = await page.title()
            report["inputs"] = await page.locator("input").evaluate_all("""els => els.slice(0,40).map(e=>({tag:e.tagName,type:e.type,name:e.name,id:e.id,value:e.value,outerHTML:e.outerHTML.slice(0,800)}))""")
            for room in ROOMS:
                loc=page.get_by_text(room, exact=False).first
                n=await loc.count()
                if not n:
                    report["rooms"][room]={"found":False}
                    continue
                report["rooms"][room]=await loc.evaluate("""el => {
                  let a=el; const chain=[];
                  for(let i=0;i<6 && a;i++,a=a.parentElement){
                    chain.push({tag:a.tagName,cls:a.className,id:a.id,html:a.outerHTML.slice(0,18000)})
                  }
                  return {found:true,ancestors:chain}
                }""")
            report["calendar_symbols_in_visible_text"] = await page.locator("body").inner_text()
            report["calendar_symbols_in_visible_text"] = report["calendar_symbols_in_visible_text"][:3500]
            await page.screenshot(path=str(OUT / "dom-diagnostic.png"), full_page=True)
        except Exception as e:
            report["error"]=str(e)[:700]
        finally:
            await browser.close()
    (OUT/"dom-diagnostic.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("HTTP:",report.get("http_status"),"rooms:",[(k,v.get("found")) for k,v in report["rooms"].items()],"error:",report.get("error"))
    if report.get("http_status") != 200 or not all(v.get("found") for v in report["rooms"].values()):
        raise SystemExit(1)

if __name__=="__main__":
    asyncio.run(main())

import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
URL="https://reserve.489ban.net/client/notoyaryokan/0/plan/availability/room/stay"
TARGETS=[("2026-12-01",2026,12,1),("2027-01-01",2027,1,1),("2027-02-01",2027,2,1)]
ROOM_IDS=["room_38492","room_38586","room_38585"]
OUT=Path("artifacts");OUT.mkdir(exist_ok=True)
async def main():
    result={"url":URL,"months":{},"safety":"diagnostic only; no booking and no notifications"}
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page(locale="ja-JP",viewport={"width":1440,"height":960})
        try:
            response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
            result["http_status"]=response.status if response else None
            await page.wait_for_timeout(5000)
            for date,year,month,day in TARGETS:
                d={"target":date}
                try:
                    picker=page.locator("#datePicker")
                    if not await picker.count(): raise RuntimeError("datePicker missing")
                    await picker.click()
                    for attempt in range(18):
                        selector=f'#ui-datepicker-div td[data-year="{year}"][data-month="{month-1}"][data-handler="selectDay"] a'
                        links=page.locator(selector)
                        if await links.count():
                            await links.first.click()
                            break
                        next_button=page.locator("#ui-datepicker-div .ui-datepicker-next")
                        if not await next_button.is_visible():raise RuntimeError("datepicker next button unavailable")
                        await next_button.click()
                        await page.wait_for_timeout(250)
                    else:raise RuntimeError("target date unreachable")
                    await page.wait_for_timeout(4500)
                    d["picker_value"]=await picker.input_value()
                    d["page_url"]=page.url
                    d["room_id_presence"]={r:await page.locator("#"+r).count() for r in ROOM_IDS}
                    d["room_like_ids"]=await page.locator('[id*="room"]').evaluate_all("els=>els.slice(0,80).map(e=>({id:e.id,text:e.innerText.slice(0,120)}))")
                    d["tables"]=await page.locator("table").evaluate_all("els=>els.slice(0,12).map(e=>({id:e.id,html:e.outerHTML.slice(0,5000)}))")
                    d["body_excerpt"]=(await page.locator("body").inner_text())[:5000]
                    await page.screenshot(path=str(OUT/("screen-"+date+".png")),full_page=True)
                except Exception as e:d["error"]=str(e)[:700]
                result["months"][date]=d
        except Exception as e:result["error"]=str(e)[:700]
        finally:await browser.close()
    (OUT/"diagnostic-v2.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:{"picker":v.get("picker_value"),"room_ids":v.get("room_id_presence"),"error":v.get("error")} for k,v in result["months"].items()},ensure_ascii=False))
    if result.get("http_status")!=200:raise SystemExit(1)
if __name__=="__main__":asyncio.run(main())

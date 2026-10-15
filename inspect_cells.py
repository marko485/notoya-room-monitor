import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://reserve.489ban.net/client/notoyaryokan/0/plan/availability/room/stay"
ROOMS={"本館川側10畳客室":"room_38492","本館川側7.5畳和室":"room_38586","本館川側2間客室":"room_38585"}
OUT=Path("artifacts"); OUT.mkdir(exist_ok=True)

async def main():
    result={"purpose":"diagnostic only, never books or claims availability"}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(locale="ja-JP", viewport={"width":1400,"height":1000})
        try:
            response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
            await page.wait_for_timeout(6000)
            result["http_status"]=response.status if response else None
            result["calendar_dates"]=await page.locator("#datePicker").input_value()
            result["tables"]={}
            for name,room_id in ROOMS.items():
                room=page.locator("#"+room_id)
                result["tables"][name]=await room.evaluate("""el => ({
                  text:el.innerText.slice(-2200),
                  tableRows:[...el.querySelectorAll('table tr')].map(tr=>({
                    html:tr.outerHTML.slice(0,14000),
                    cells:[...tr.querySelectorAll('th,td')].map(c=>({
                      tag:c.tagName, text:c.innerText.trim(), html:c.outerHTML.slice(0,1500),
                      className:c.className, href:c.querySelector('a')?.getAttribute('href')||null
                    }))
                  }))
                })""")
            await page.locator("#datePicker").click()
            await page.wait_for_timeout(500)
            result["date_picker_html"]=await page.locator("#ui-datepicker-div").evaluate("(el)=>el.outerHTML.slice(0,16000)") if await page.locator("#ui-datepicker-div").count() else "not found"
            await page.screenshot(path=str(OUT/"datepicker.png"),full_page=True)
        except Exception as e:result["error"]=str(e)[:800]
        finally:await browser.close()
    (OUT/"calendar-cells.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("HTTP",result.get("http_status"),"date",result.get("calendar_dates"),"tables",[(k,len(v.get("tableRows",[]))) for k,v in result.get("tables",{}).items()],"error",result.get("error"))
    if result.get("http_status")!=200 or len(result.get("tables",{}))!=3: raise SystemExit(1)

if __name__=="__main__":asyncio.run(main())

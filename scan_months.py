import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://reserve.489ban.net/client/notoyaryokan/0/plan/availability/room/stay"
ROOMS={"本館川側10畳客室":"room_38492","本館川側7.5畳和室":"room_38586","本館川側2間客室":"room_38585"}
TARGETS=["2026-12-01","2027-01-01","2027-02-01"]
OUT=Path("artifacts"); OUT.mkdir(exist_ok=True)

async def select_date(page, iso):
    year,month,day=map(int,iso.split("-"))
    await page.locator("#datePicker").click()
    cell=page.locator(f'#ui-datepicker-div td[data-handler="selectDay"][data-year="{year}"][data-month="{month-1}"] a').filter(has_text=re.compile(r"^"+str(day)+r"$"))
    for _ in range(15):
        if await cell.count() and await cell.first.is_visible():
            await cell.first.click()
            await page.wait_for_timeout(5500)
            return
        nxt=page.locator("#ui-datepicker-div .ui-datepicker-next")
        if not await nxt.count() or not await nxt.is_visible():
            raise RuntimeError(f"Cannot navigate calendar to {iso}")
        await nxt.click()
        await page.wait_for_timeout(250)
    raise RuntimeError(f"Date not found: {iso}")

async def extract(page):
    result={}
    for name,room_id in ROOMS.items():
        result[name]=await page.locator("#"+room_id).evaluate("""el => {
            let rows=[...el.querySelectorAll('table tr')];
            if(rows.length<2) return {error:'No date/status rows'};
            let dates=[...rows[0].querySelectorAll('th,td')].map(x=>x.innerText.trim().replace(/\\s+/g,' '));
            let cells=[...rows[1].querySelectorAll('td')];
            if(dates.length!==cells.length) return {error:'Length mismatch', date_count:dates.length, status_count:cells.length};
            return dates.map((date,i)=>{
                let c=cells[i], classes=[...c.querySelectorAll('i')].map(x=>x.className);
                let state=classes.some(x=>x.includes('fa-xmark'))?'SOLD_OUT':classes.some(x=>x.includes('fa-minus'))?'UNAVAILABLE':'UNKNOWN_REQUIRES_VERIFICATION';
                return {date, state, icon_classes:classes, link:c.querySelector('a')?.getAttribute('href')||null};
            });
        }""")
    return result

async def main():
    report={"official_url":URL,"targets":{},"safety":"read only: no booking, no email, no availability alerts"}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(locale="ja-JP", viewport={"width":1400,"height":1000})
        try:
            response=await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            report["http_status"]=response.status if response else None
            await page.wait_for_timeout(5000)
            for date in TARGETS:
                try:
                    await select_date(page,date)
                    report["targets"][date]={"picker_value":await page.locator("#datePicker").input_value(),"rooms":await extract(page)}
                    await page.screenshot(path=str(OUT/f"calendar-{date}.png"),full_page=True)
                except Exception as e:
                    report["targets"][date]={"error":str(e)}
        except Exception as e:report["error"]=str(e)
        finally: await browser.close()
    (OUT/"month-scan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"http_status":report.get("http_status"),"targets":{k:{"picker":v.get("picker_value"),"error":v.get("error"),"room_counts":{r:len(c) if isinstance(c,list) else 0 for r,c in v.get("rooms",{}).items()}} for k,v in report["targets"].items()}},ensure_ascii=False))
    if report.get("http_status")!=200 or any("rooms" not in v for v in report["targets"].values()):raise SystemExit(1)

if __name__=="__main__":asyncio.run(main())

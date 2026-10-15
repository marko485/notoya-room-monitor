import asyncio, json, re
from pathlib import Path
from datetime import datetime, timezone
from playwright.async_api import async_playwright

BASE="https://reserve.489ban.net/client/notoyaryokan/0/plan/availability/room/stay"
TARGETS=["2026-12-01","2026-12-15","2027-01-01","2027-01-15","2027-02-01","2027-02-15"]
ROOMS={"room_38492":"本館川側10畳客室","room_38586":"本館川側7.5畳和室","room_38585":"本館川側2間客室"}
OUT=Path("artifacts");OUT.mkdir(exist_ok=True)

async def extract_room(page, rid, room):
    el=page.locator("#"+rid)
    if await el.count()==0: return {"room":room,"state":"NOT_DISPLAYED","dates":[]}
    return await el.evaluate("""(node) => {
       const table=node.querySelector('table');
       if (!table) return {state:'NO_TABLE',dates:[]};
       const heads=[...table.querySelectorAll('thead th')];
       const cells=[...table.querySelectorAll('tbody td')];
       return {state:'PRESENT',head_count:heads.length,cell_count:cells.length,
         dates:heads.map((h,i)=>{
           const c=cells[i],html=c?.outerHTML||'';
           const icons=c?[...c.querySelectorAll('i,svg')].map(e=>(e.getAttribute('class')||'')):[];
           let status='UNKNOWN';
           if(/fa-xmark|fa-times|fa-close/.test(html))status='SOLD_OUT';
           else if(/fa-minus/.test(html))status='UNAVAILABLE';
           else if(/\\b(?:残室|vacanc|available)\\b|fa-circle/.test(html))status='POSSIBLY_AVAILABLE';
           return {header:h.innerText.trim().replace(/\\s+/g,' '),status,icons,
             cell_html:html.slice(0,1200),link:c?.querySelector('a')?.getAttribute('href')||null};
         })};
    }""")

async def main():
    report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),"source":BASE,
      "purpose":"READ_ONLY_DIAGNOSTIC","months":{},"verified_bookable_dates":[]}
    async with async_playwright() as p:
       browser=await p.chromium.launch(headless=True)
       page=await browser.new_page(locale="ja-JP",viewport={"width":1280,"height":900})
       for target in TARGETS:
         record={}
         try:
            response=await page.goto(BASE+"?date="+target+"#calForm",wait_until="domcontentloaded",timeout=45000)
            await page.wait_for_timeout(5000)
            record["http_status"]=response.status if response else None
            record["picker"]=await page.locator("#datePicker").input_value(timeout=10000)
            record["url"]=page.url
            record["rooms"]={}
            for rid,name in ROOMS.items():
                record["rooms"][name]=await extract_room(page,rid,name)
            await page.screenshot(path=str(OUT/("screen-"+target+".png")),full_page=True)
            record["valid_date_change"]=record["picker"].replace("/","-")==target
         except Exception as e:record["error"]=str(e)[:650]
         report["months"][target]=record
       await browser.close()
    (OUT/"six-windows.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    for date,item in report["months"].items():
       print(date,"picker",item.get("picker"),"valid",item.get("valid_date_change"),"error",item.get("error"),
         "rooms",{k:v.get("state") for k,v in item.get("rooms",{}).items()})
    if any(not x.get("valid_date_change") for x in report["months"].values()): raise SystemExit(1)

if __name__=="__main__": asyncio.run(main())

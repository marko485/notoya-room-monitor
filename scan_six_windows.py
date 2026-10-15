"""Read-only official calendar monitor. No booking and no vacancy notifications."""
import asyncio, json, os, re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from playwright.async_api import async_playwright

BASE = "https://reserve.489ban.net/client/notoyaryokan/0/plan/availability/room/stay"
ROOMS = {"room_38492": "本館川側10畳客室", "room_38586": "本館川側7.5畳和室", "room_38585": "本館川側2間客室"}
OUT=Path("artifacts")
OUT.mkdir(exist_ok=True)
# Explicit bounded horizon, never claim to have checked dates beyond it.
HORIZON_DAYS=min(max(int(os.getenv("NOTOYA_HORIZON_DAYS","365")),14),548)
WINDOW_DAYS=14

async def extract(page, rid):
    item=page.locator("#"+rid)
    if not await item.count():
        return {"state":"NOT_DISPLAYED","cells":[]}
    return await item.evaluate("""node=>{
       const table=node.querySelector('table');
       if(!table)return {state:'NO_TABLE',cells:[]};
       const headers=[...table.querySelectorAll('thead th')];
       const cells=[...table.querySelectorAll('tbody td')];
       return {state:'PRESENT',header_count:headers.length,cell_count:cells.length,
         cells:headers.map((h,i)=>{
           const c=cells[i]; const html=c?.outerHTML||'';
           const icons=c?[...c.querySelectorAll('i,svg')].map(e=>e.getAttribute('class')||''):[];
           let status='UNKNOWN';
           if(/fa-xmark|fa-times|fa-close/.test(html))status='SOLD_OUT';
           else if(/fa-minus/.test(html))status='UNAVAILABLE';
           else if(/fa-circle/.test(html))status='POSSIBLY_AVAILABLE';
           return {header:h.innerText.trim().replace(/\\s+/g,' '),status,icons,
             link:c?.querySelector('a')?.getAttribute('href')||null};
         })};
    }""")

async def main():
    today=datetime.now(timezone(timedelta(hours=9))).date()
    end=today+timedelta(days=HORIZON_DAYS-1)
    starts=[today+timedelta(days=n) for n in range(0,HORIZON_DAYS,WINDOW_DAYS)]
    report={"checked_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":BASE,"purpose":"READ_ONLY_CALENDAR_SCAN",
        "range_start":str(today),"range_end":str(end),
        "horizon_days":HORIZON_DAYS,"windows":{},
        "note":"Calendar icons alone do NOT verify a bookable 2-adult plan. NO automatic alerts."}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page(locale="ja-JP",viewport={"width":1280,"height":900})
        for start in starts:
            key=start.isoformat()
            rec={"window_start":key,"window_end":str(min(end,start+timedelta(days=13)))}
            try:
                resp=await page.goto(BASE+"?date="+key+"#calForm",wait_until="domcontentloaded",timeout=45000)
                await page.wait_for_timeout(2000)
                rec["http_status"]=resp.status if resp else None
                rec["picker"]=await page.locator("#datePicker").input_value(timeout=10000)
                rec["picker_matches"]=rec["picker"].replace("/","-")==key
                rec["rooms"]={}
                for rid,room in ROOMS.items():
                    raw=await extract(page,rid)
                    # Map cell positions to actual ISO dates ONLY if date headers are coherent.
                    valid=raw.get("state")=="PRESENT" and raw.get("header_count")==raw.get("cell_count") and len(raw.get("cells",[]))>=14
                    raw["date_alignment_valid"]=valid
                    if valid:
                        for idx,cell in enumerate(raw["cells"]):
                            cell["date"]=str(start+timedelta(days=idx))
                    rec["rooms"][room]=raw
                if not rec["picker_matches"]:rec["error"]="Date picker mismatch: window not verified"
            except Exception as e:
                rec["error"]=str(e)[:600]
            report["windows"][key]=rec
        await browser.close()
    # Exclude unverified, missing and misaligned cells from covered dates.
    covered=set()
    candidates=[]
    for win in report["windows"].values():
        if win.get("error") or not win.get("picker_matches") or win.get("http_status")!=200:continue
        for room,raw in win.get("rooms",{}).items():
            if not raw.get("date_alignment_valid"):continue
            for cell in raw["cells"]:
                d=cell["date"]
                if str(today)<=d<=str(end):
                    covered.add(d)
                    if cell["status"]=="POSSIBLY_AVAILABLE":
                        candidates.append({"date":d,"room":room,"status":"UNVERIFIED_CALENDAR_SIGNAL"})
    report["calendar_covered_days"]=len(covered)
    report["calendar_expected_days"]=HORIZON_DAYS
    report["calendar_candidates"]=candidates
    report["verified_bookable_dates"]=[]
    (OUT/"availability-scan.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"range":[str(today),str(end)],"windows":len(starts),
       "covered_days":len(covered),"expected_days":HORIZON_DAYS,
       "unverified_candidates":len(candidates),"bookable_verified":0},ensure_ascii=False))
    if len(covered)!=HORIZON_DAYS:raise SystemExit("Incomplete calendar coverage; do not infer unavailable dates")

if __name__=="__main__":asyncio.run(main())

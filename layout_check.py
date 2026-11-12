#!/usr/bin/env python3
"""版面鎖定：python3 layout_check.py [--update]
對 5 個分頁（首頁/學習/金句/延伸/設定）在 340/360/390 寬度量各區塊的位置與大小，
與 layout/manifest.json 比對；--update 只在「大修／小修」時重建基準。
微調版（V-x.xx#）只准改資料，區塊尺寸差超過 2px 就視為版面被動到。"""
import json, os, sys
from playwright.sync_api import sync_playwright
here = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(here, "layout"); os.makedirs(OUT, exist_ok=True)
PAGES = ["home", "learn", "gold", "media", "set"]
WIDTHS = [340, 360, 390]
JS = """(id)=>{const root=document.getElementById('pg-'+id);if(!root)return null;
const r0=root.getBoundingClientRect();
const kids=[...root.querySelectorAll(':scope > *, :scope > * > *')].filter(e=>e.getBoundingClientRect().height>0);
return {h:Math.round(root.scrollHeight),w:Math.round(r0.width),
 blocks:kids.map(e=>{const r=e.getBoundingClientRect();return [e.tagName.toLowerCase()+(e.className?'.'+String(e.className).split(' ')[0]:''),Math.round(r.left-r0.left),Math.round(r.top-r0.top),Math.round(r.width),Math.round(r.height)]})}}"""
def measure(shots=False):
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for w in WIDTHS:
            c = b.new_context(viewport={"width": w, "height": 740}, color_scheme="light")
            pg = c.new_page()
            pg.add_init_script("try{localStorage.setItem('dhp2-about','1');localStorage.setItem('dhp2-intro','1');localStorage.setItem('dhp2-set',JSON.stringify({rem:'off'}))}catch(e){}")
            pg.goto("file://" + os.path.join(here, "index.html")); pg.wait_for_timeout(1200)
            for pid in PAGES:
                pg.click('#tb button[data-p="%s"]' % pid); pg.wait_for_timeout(500)
                pg.evaluate("(()=>{const t=document.getElementById('toc');if(t)t.remove();document.querySelectorAll('.hlp').forEach(e=>e.remove())})()")
                res["%s@%d" % (pid, w)] = pg.evaluate(JS, pid)
                if shots:
                    el = pg.query_selector("#pg-" + pid)
                    el.screenshot(path=os.path.join(OUT, "%s_%d.png" % (pid, w)))
            c.close()
        b.close()
    return res
def main():
    mf = os.path.join(OUT, "manifest.json")
    if "--update" in sys.argv:
        json.dump(measure(True), open(mf, "w"), ensure_ascii=False, indent=0); print("基準已建立：", mf); return
    base = json.load(open(mf)); cur = measure(); bad = 0
    for k, b in base.items():
        c = cur.get(k)
        if not c: print("  !!  缺少", k); bad += 1; continue
        if abs(c["h"] - b["h"]) > 2: print("  !!  %s 頁高 %d→%d" % (k, b["h"], c["h"])); bad += 1
        if len(c["blocks"]) != len(b["blocks"]): print("  !!  %s 區塊數 %d→%d" % (k, len(b["blocks"]), len(c["blocks"]))); bad += 1; continue
        for i, (x, y) in enumerate(zip(b["blocks"], c["blocks"])):
            if any(abs(x[j] - y[j]) > 2 for j in range(1, 5)): print("  !!  %s 第%d塊 %s %s→%s" % (k, i, x[0], x[1:], y[1:])); bad += 1
    print("版面與基準一致" if not bad else "版面有 %d 處不同" % bad); sys.exit(1 if bad else 0)
main()

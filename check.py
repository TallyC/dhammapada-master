#!/usr/bin/env python3
"""推出前的檢查：python3 check.py
檢查「有新版」通知所依賴的文字格式、離線檔與程式語法。全部通過才算可以推出。
不會修改任何檔案。"""
import json
import os
import re
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
errs = []


def ok(msg):
    print("  OK  " + msg)


def bad(msg):
    errs.append(msg)
    print("  !!  " + msg)


def read(name):
    with open(os.path.join(here, name), encoding="utf8") as f:
        return f.read()


html = read("index.html")
sw = read("sw.js")

# 1. 更新通知：app 以這些「文字比對」判斷有沒有新版（見 index.html 的更新檢查）
m = re.findall(r'<meta name="app-ver" content="([^"]+)"', html)
if len(m) == 1:
    ok("版本標記 app-ver 剛好一個：" + m[0])
else:
    bad("app-ver 版本標記應該剛好出現 1 次，目前 %d 次" % len(m))

# app 是用「整頁文字第一個符合的位置」來讀版本標記，所以第一個符合的必須就是 <meta> 那個
first_hit = re.search(r'name="app-ver" content="([^"]+)"', html)
if m and first_hit and first_hit.group(1) == m[0]:
    ok("app 讀到的版本標記就是 <meta> 那一個")
else:
    bad("app 以文字比對讀到的第一個 app-ver 不是 <meta> 標記（程式碼裡的同樣字串跑到 <meta> 前面了？）")

a = re.findall(r'var APPV="(V-\d+\.\d\d\d)";', html)
if len(a) == 1:
    ok("顯示版號 APPV：" + a[0])
else:
    bad("APPV 應該剛好出現 1 次且格式為 V-N.NNN，目前 %d 次" % len(a))

# 與 app 內相同的規則：\nvar CHG=[ ... ];\n，且必須在同一行
c = re.search(r"\nvar CHG=(\[.*\]);\n", html)
chg = None
if not c:
    bad("找不到版本記錄 CHG 行（格式必須是單獨一行 var CHG=[...];），更新通知會失效")
else:
    try:
        chg = json.loads(c.group(1))
        ok("版本記錄 CHG 可解析，共 %d 筆" % len(chg))
    except Exception as e:
        bad("版本記錄 CHG 不是合法 JSON：%s" % e)

if chg:
    first = chg[0]
    if a and first.get("v") == a[0]:
        ok("版本記錄最新一筆與 APPV 一致")
    else:
        bad("版本記錄最新一筆（%s）與 APPV（%s）不一致" % (first.get("v"), a[0] if a else "?"))
    for i, e in enumerate(chg[:5]):
        if not all(k in e for k in ("v", "d", "t")):
            bad("版本記錄第 %d 筆缺少 v/d/t 欄位" % (i + 1))
            break
    else:
        ok("最近 5 筆版本記錄欄位完整")

# 2. 離線檔：更新檢查的網址帶 ?v=，離線程式必須放行不快取
if "'?v='" in html or '"?v="' in html or "?v='+" in html:
    if "searchParams.has('v')" in sw:
        ok("sw.js 會放行 ?v= 的更新檢查，不存快取")
    else:
        bad("index.html 的更新檢查帶 ?v=，但 sw.js 沒有放行，快取會越積越多")

# 3. 語法檢查（需要 node）
def node_check(label, text):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf8") as t:
        t.write(text)
        path = t.name
    try:
        r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        if r.returncode == 0:
            ok(label + " 語法正確")
        else:
            bad(label + " 語法錯誤：" + r.stderr.strip().splitlines()[0] if r.stderr.strip() else label + " 語法錯誤")
    finally:
        os.unlink(path)


try:
    subprocess.run(["node", "--version"], capture_output=True, check=True)
    have_node = True
except Exception:
    have_node = False
    bad("找不到 node，無法做語法檢查")

if have_node:
    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, flags=re.S)
    for i, s in enumerate(scripts):
        if s.strip():
            node_check("index.html 內嵌程式 #%d" % (i + 1), s)
    node_check("sw.js", sw)

# 版面鎖定：微調版（末兩碼不是 00）只准改資料，區塊尺寸不得變動；大修／小修請先確認再 layout_check.py --update
_v = re.findall(r'var APPV="V-(\d+)\.(\d)(\d\d)";', html)
if _v and _v[0][2] != "00" and os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout", "manifest.json")):
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "layout_check.py")], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        bad("微調版動到版面（見上）。若是刻意改版面，請升為小修並重建基準。")

print()
if errs:
    print("未通過（%d 項）：先修正再推出。" % len(errs))
    sys.exit(1)
print("全部通過。")

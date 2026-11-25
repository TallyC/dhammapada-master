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

# 1b. version.json（輕量更新檢查）必須與 index.html 同步；README 版號也要一致
vj_path = os.path.join(here, "version.json")
if not os.path.exists(vj_path):
    bad("找不到 version.json，請執行 python3 bump.py 產生")
else:
    try:
        vj = json.loads(read("version.json"))
        if m and a and vj.get("app-ver") == m[0] and vj.get("APPV") == a[0] and chg and vj.get("CHG") == chg[:3]:
            ok("version.json 與 index.html 的 app-ver／APPV／CHG 一致")
        else:
            bad("version.json 與 index.html 不同步，請執行 python3 bump.py")
    except Exception as e:
        bad("version.json 不是合法 JSON：%s" % e)
readme = read("README.md")
rv = re.search(r"本文件對應程式 (V-\d+\.\d\d\d)", readme)
if rv and a and rv.group(1) == a[0]:
    ok("README 版號與程式一致：" + rv.group(1))
else:
    bad("README 的「本文件對應程式」版號（%s）與 APPV（%s）不一致" % (rv.group(1) if rv else "?", a[0] if a else "?"))

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

# 4. 資料完整性（需要 node）：FULL 偈數與連號、漢譯偈是否都收進導讀、巴利 1–423 號、梵巴欄位標示
def load_data():
    lines = html.split("\n")
    a = next(i for i, l in enumerate(lines) if l.startswith("var BOOKS="))
    d = next(i for i, l in enumerate(lines) if l.startswith("var DAILY="))
    parts = lines[a:d] + [l for l in lines if l.startswith("BOOKS.push(") or l.startswith("var FULL=")]
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "data.json")
        code = "\n".join(parts) + "\nrequire('fs').writeFileSync(%s,JSON.stringify({BOOKS:BOOKS,FULL:FULL}));" % json.dumps(out)
        js = os.path.join(tmp, "ext.js")
        with open(js, "w", encoding="utf8") as f:
            f.write(code)
        r = subprocess.run(["node", js], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr.strip().splitlines()[0] if r.stderr.strip() else "node 執行失敗")
        with open(out, encoding="utf8") as f:
            return json.load(f)


if have_node:
    try:
        data = load_data()
    except Exception as e:
        data = None
        bad("無法載入 BOOKS／FULL 資料：%s" % e)
    if data:
        BOOKS, FULL = data["BOOKS"], data["FULL"]
        # 4a. FULL：39 品、758 偈、各品 vn 連號
        chs = [FULL[str(i)] for i in range(1, 40) if str(i) in FULL]
        total = sum(len(c["t"]) for c in chs)
        if len(chs) == 39 and total == 758:
            ok("FULL：39 品、%d 偈" % total)
        else:
            bad("FULL 應為 39 品、758 偈，目前 %d 品、%d 偈" % (len(chs), total))
        badvn = [c["n"] for c in chs if c.get("vn") and list(c["vn"]) != list(range(1, len(c["t"]) + 1))]
        if badvn:
            bad("這些品的 vn 不是 1..N 連號：" + "、".join(badvn))
        else:
            ok("FULL 各品 vn 為連號")

        # 4b. 漢譯每一偈的每個分句，都要出現在導讀的 h 欄位（偈可跨單元，故逐分句比對）
        strip = re.compile(r"[\s，。、；：？！「」『』（）,.;:|]")
        blob = "".join(strip.sub("", "".join(k.get("h") or [])) for b in BOOKS for u in b["u"] for k in u["k"])
        miss = []
        for i in range(1, 40):
            c = FULL.get(str(i))
            if not c:
                continue
            for n, t in enumerate(c["t"], 1):
                for seg in re.split(r"[，。、；：？！|]", t):
                    seg = strip.sub("", seg)
                    if seg and seg not in blob:
                        miss.append("%s 第 %d 偈「%s」" % (c["n"], n, seg))
                        break
        if miss:
            bad("導讀漏收漢譯偈（共 %d）：" % len(miss) + "；".join(miss[:8]))
        else:
            ok("FULL 758 偈的每個分句都已收進導讀")

        # 4c. 巴利 1–423：只看巴利 26 品；同一巴利號出現在兩則時，後者必須宣告為交叉引用（有 hr）
        seen = {}
        dup_bad = []
        pno = re.search(r"PNO=\{([^}]*)\}", html)
        pali_ids = set(re.findall(r"(\w+):\d+", pno.group(1))) if pno else set()
        if len(pali_ids) != 26:
            bad("找不到 PNO（巴利 26 品對照）或數量不是 26：%d" % len(pali_ids))
        for b in BOOKS:
            if b["id"] not in pali_ids:
                continue
            for u in b["u"]:
                for k in u["k"]:
                    n = str(k.get("n"))
                    if not n.isdigit():
                        continue
                    n = int(n)
                    if not 1 <= n <= 423:
                        dup_bad.append("%s %s 偈號 %d 超出 1–423" % (b["n"], u["id"], n))
                    elif n in seen and not k.get("hr"):
                        dup_bad.append("巴利 %d 重複（%s 與 %s）且後者未標交叉引用 hr" % (n, seen[n], u["id"]))
                    seen.setdefault(n, u["id"])
        lacking = [n for n in range(1, 424) if n not in seen]
        if lacking:
            bad("巴利偈缺號：" + "、".join(map(str, lacking[:10])))
        elif dup_bad:
            bad("巴利偈號問題：" + "；".join(dup_bad[:6]))
        else:
            ok("巴利 1–423 偈完整，號碼唯一（交叉引用者除外）")

        # 4d. k.p／k.pl 一致：含梵文專用字母（ś ṣ ṛ ḥ）的偈，k.pl 必須以「梵文」開頭（有些梵文偈不含這些字母，故反過來不強制）
        skt = re.compile("[śṣṛḥ]")
        pl_bad = []
        for b in BOOKS:
            for u in b["u"]:
                for k in u["k"]:
                    if not k.get("p"):
                        continue
                    is_skt_text = bool(skt.search("".join(k["p"])))
                    is_skt_label = str(k.get("pl", "")).startswith("梵文")
                    if is_skt_text and not is_skt_label:
                        pl_bad.append("%s %s 偈 %s" % (b["n"], u["id"], k.get("n")))
        if pl_bad:
            bad("k.p 內容與 k.pl 標示（梵文／巴利）不一致：" + "；".join(pl_bad[:6]))
        else:
            ok("k.p 與 k.pl 的梵文／巴利標示一致")

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

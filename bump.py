#!/usr/bin/env python3
"""每次更新前執行：python3 bump.py
換新版標記（app-ver），並產生輕量的 version.json（手機只下載這個小檔判斷有沒有新版）。
取代舊的 bump.sh 內的 sed，Linux／macOS 都能用。"""
import datetime
import json
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(here, "index.html")
s = open(p, encoding="utf8").read()
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
s, n = re.subn(r'(<meta name="app-ver" content=")[^"]*(")', r"\g<1>" + stamp + r"\g<2>", s, count=1)
if n != 1:
    raise SystemExit("找不到 app-ver 標記")
open(p, "w", encoding="utf8").write(s)
appv = re.search(r'var APPV="(V-\d+\.\d\d\d)";', s).group(1)
chg = json.loads(re.search(r"\nvar CHG=(\[.*\]);\n", s).group(1))[:3]
with open(os.path.join(here, "version.json"), "w", encoding="utf8") as f:
    json.dump({"app-ver": stamp, "APPV": appv, "CHG": chg}, f, ensure_ascii=False, separators=(",", ":"))
    f.write("\n")
print(stamp, appv)

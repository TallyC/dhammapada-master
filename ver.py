#!/usr/bin/env python3
"""每次推出前執行：python3 ver.py <big|minor|micro> "這一版改了什麼" ["新增 N 偈"]
版號 V-4.903：4 大修、9 小修、03 微調（最多 99）。big 大修；minor 小修；micro 微調。
會改 index.html 裡的版本號 APPV，並在版本記錄 CHG 最前面加一筆。"""
import re,sys,json,datetime
kind,text=sys.argv[1],sys.argv[2];add=sys.argv[3] if len(sys.argv)>3 else ""
p="index.html";s=open(p,encoding="utf8").read()
m=re.search(r'var APPV="V-(\d+)\.(\d)(\d\d)";',s);a,b,c=map(int,m.groups())
if kind=="big":a,b,c=a+1,0,0
elif kind=="minor":b,c=b+1,0
else:c+=1
if c>99:b,c=b+1,0
if b>9:a,b,c=a+1,0,0
v="V-%d.%d%02d"%(a,b,c)
s=s.replace(m.group(0),'var APPV="%s";'%v)
e={"v":v,"d":datetime.date.today().isoformat(),"t":text}
if add:e["a"]=add
s=s.replace("\nvar CHG=[","\nvar CHG=["+json.dumps(e,ensure_ascii=False,separators=(",",":"))+",",1)
open(p,"w",encoding="utf8").write(s);print(v)

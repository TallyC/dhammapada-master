// 網路優先：有網路時永遠抓最新版，離線才用快取
const C='dhp-v1';
// 安裝時先把頁面與圖示存起來，第一次安裝後就能離線開啟；失敗不影響安裝
const PRE=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','apple-touch-icon.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>Promise.all(PRE.map(u=>fetch(u,{cache:'reload'}).then(r=>{if(r&&r.ok&&r.type==='basic')return c.put(u,r)}).catch(()=>{})))).catch(()=>{}).then(()=>self.skipWaiting()))});
// 啟用時：刪掉舊名稱的快取，並清掉過去累積的「更新檢查」快取（網址帶 ?v=）
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C&&x!=='dhp-font').map(x=>caches.delete(x)))).then(()=>caches.open(C)).then(c=>c.keys().then(rs=>Promise.all(rs.filter(r=>new URL(r.url).searchParams.has('v')).map(r=>c.delete(r))))).catch(()=>{}).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
 const r=e.request;if(r.method!=='GET')return;const u=new URL(r.url);
 if(u.hostname==='fonts.googleapis.com'||u.hostname==='fonts.gstatic.com'){e.respondWith(caches.open('dhp-font').then(c=>c.match(r).then(m=>m||fetch(r).then(res=>{if(res&&(res.ok||res.type==='opaque'))c.put(r,res.clone());return res}))));return}
 if(u.origin!==location.origin)return;
 if(u.searchParams.has('v'))return; // 更新檢查（?v=時間）：直接連線，不經過也不存入快取
 e.respondWith(fetch(r,{cache:'no-store'}).then(res=>{if(res&&res.ok&&res.type==='basic'){const c=res.clone();caches.open(C).then(x=>x.put(r,c)).catch(()=>{})}return res}).catch(()=>caches.match(r).then(m=>m||caches.match('./'))));
});

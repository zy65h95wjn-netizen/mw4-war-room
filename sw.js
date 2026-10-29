/* War Room v0.4.4 artwork review: loadout navigation fix; network-first verified-site cache with offline fallback.
   Editorial validation is performed in the app, before saving the last-good JSON.
*/
const CACHE='mw4-warroom-armory-2026-10-28-icon1';
const CORE=['./armory.css?v=armory-20261028-1','./armory-ui.js?v=armory-20261028-1','./art/armory-room.png','./','./index.html','./logic.js?v=armory-20261028-1','./store.js?v=armory-20261028-1','./app.js?v=armory-20261028-1','./arsenal.js?v=armory-20261028-1','./esports-mobile.css','./arsenal.css?v=armory-20261028-1','./art/featured/full-arsenal-atlas.webp','./art/featured/han-86.webp','./art/featured/axion.webp','./art/featured/vel-46.webp','./art/featured/iso-nightshade.webp','./art/featured/kg-7-vulcan.webp','./art/featured/hyeon-burst.webp','./art/featured/m4.webp','./art/featured/kastov-762.webp','./art/featured/x-58-nyx.webp','./art/featured/ppsh-41.webp','./data/intel.json','./data/store.json','./manifest.webmanifest?v=mw4-gold-1','./icon-mw4-gold-32.png','./icon-mw4-gold-180.png','./icon-mw4-gold-192.png','./icon-mw4-gold-512.png'];
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const cache=await caches.open(CACHE);
 await cache.addAll(CORE);
 await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 const keys=await caches.keys();
 await Promise.all(keys.filter(k=>k.startsWith('mw4-warroom-')&&k!==CACHE).map(k=>caches.delete(k)));
 await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 if(event.request.method!=='GET')return;
 const url=new URL(event.request.url);
 if(url.origin!==self.location.origin)return;
 const critical=event.request.mode==='navigate'||/\/(?:intel\.json|app\.js|armory-ui\.js|armory\.css|logic\.js|store\.js|arsenal\.js|arsenal\.css|index\.html)$/.test(url.pathname);
 if(critical){
  event.respondWith((async()=>{
   try{
    const response=await fetch(event.request);
    if(!response.ok)throw Error('HTTP '+response.status);
    const cache=await caches.open(CACHE);
    await cache.put(event.request,response.clone());
    return response;
   }catch(_error){
    const cached=await caches.match(event.request);
    if(cached){const headers=new Headers(cached.headers);headers.set('X-WarRoom-Saved','true');return new Response(cached.body,{status:cached.status,statusText:cached.statusText,headers});}
    if(event.request.mode==='navigate'){
     const shell=await caches.match('./index.html');
     if(shell)return shell;
    }
    return new Response('War Room offline and no saved response available',{status:503,headers:{'Content-Type':'text/plain'}});
   }
  })());
 }else{
  event.respondWith((async()=>{
   const cached=await caches.match(event.request);
   if(cached)return cached;
   const response=await fetch(event.request);
   if(response.ok){const cache=await caches.open(CACHE);await cache.put(event.request,response.clone());}
   return response;
  })());
 }
});
/* War Room v0.2.1: network-first verified-site cache with offline fallback.
   Editorial validation is performed in the app, before saving the last-good JSON.
*/
const CACHE='mw4-warroom-v021-20261027';
const CORE=['./','./index.html','./app.js','./data/intel.json','./manifest.webmanifest','./icon-180.png','./icon-192.png','./icon-512.png'];
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
 const critical=event.request.mode==='navigate'||/\/(?:intel\.json|app\.js|index\.html)$/.test(url.pathname);
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
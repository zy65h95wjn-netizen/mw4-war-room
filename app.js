/* MW4 War Room UI v0.4: public MW4 Store preview, Store section, and credential-free client. */
'use strict';
const $=id=>document.getElementById(id);
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeURL=s=>typeof s==='string'&&s.startsWith('https://')?s:'#';
const tabs=[['brief','⌂','Overview'],['weapons','⌖','Weapons'],['updates','≡','Updates'],['events','◉','Events'],['pass','▤','Pass'],['store','▣','Store']];
const state={page:'brief',source:'cod',category:'All',featuredCategory:'All',weapon:'HAN 86',buildId:'han-iron',ironOnly:true,search:'',feed:null,offlineCopy:false,store:{data:null,origin:'loading'}};
const prefKey='mw4-warroom-prefs-v02';
try{const p=JSON.parse(localStorage.getItem(prefKey)||'{}');if(typeof p.ironOnly==='boolean')state.ironOnly=p.ironOnly;if(p.source==='cod'||p.source==='wz')state.source=p.source}catch(_e){}
const settingsSave=()=>{try{localStorage.setItem(prefKey,JSON.stringify({ironOnly:state.ironOnly,source:state.source}))}catch(_e){}};
function source(id){return state.feed?.sources.find(s=>s.id===id)||{id,name:'Unspecified source',url:'#',class:'Unknown'}}
function anchor(id,label){const s=source(id);return `<a class="source-link" href="${escapeHTML(safeURL(s.url))}" target="_blank" rel="noopener noreferrer">${escapeHTML(label||s.name)} <span aria-hidden="true">↗</span></a>`}
function tag(text,tone=''){return `<span class="badge ${tone}">${escapeHTML(text)}</span>`}
function dateVal(value){if(!value)return null;const s=value.split('-').map(Number);return new Date(s[0],s[1]-1,s[2])}
function pretty(value,options={}){const d=dateVal(value);return d?d.toLocaleDateString('en-US',{month:'short',day:'numeric',...options}):'Date unverified'}
function snapshotAge(section){const stamp=(section&&state.feed.reviewedSections?.[section])||state.feed.reviewed,d=dateVal(stamp),n=new Date();return d?Math.max(0,Math.floor((new Date(n.getFullYear(),n.getMonth(),n.getDate())-d)/86400000)):999}
function isReviewDue(section){return snapshotAge(section)>(state.feed.reviewLimitsDays?.[section]??7)}
function freshness(section){const age=snapshotAge(section),stamp=(section&&state.feed.reviewedSections?.[section])||state.feed.reviewed;
 return age>(state.feed.reviewLimitsDays?.[section]??7)?tag('Review overdue · '+age+'d','red'):tag('Reviewed '+pretty(stamp),'amber')}
function dataNotice(){return (state.offlineCopy||navigator.onLine===false)?'<p class="detail" role="status" style="margin-bottom:14px">Offline or previously saved briefing. Verify dates and source links when online; no live-source checks occurred.</p>':''}

function headline(title,sub,label='GAME INFO'){return `<div class="heading"><div class="kicker">${escapeHTML(label)}</div><h1>${escapeHTML(title)}</h1><p>${escapeHTML(sub)}</p></div>`}
function section(title,right=''){return `<div class="section-line"><h2>${escapeHTML(title)}</h2>${right}</div>`}
function btnTo(page,label,style='secondary'){return `<button class="cta ${style}" data-page="${page}" type="button">${escapeHTML(label)}</button>`}
function sourcePanelFooter(ids){return `<div class="small-rule"></div><div class="spread" style="flex-wrap:wrap">${ids.map(id=>anchor(id,source(id).name)).join('')}</div>`}
const navIcons={
 brief:'<svg viewBox="0 0 24 24"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></svg>',
 weapons:'<svg viewBox="0 0 24 24"><path d="M3 11h18M12 3v18M5.4 5.4l13.2 13.2M18.6 5.4 5.4 18.6"/><circle cx="12" cy="12" r="5.5"/><circle cx="12" cy="12" r="1.4"/></svg>',
 updates:'<svg viewBox="0 0 24 24"><path d="M5 3h11l3 3v15H5zM8 10h8M8 14h8M8 18h6M16 3v4h3"/></svg>',
 events:'<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/><path d="m12 13 1.1 2.2 2.4.4-1.8 1.7.5 2.3-2.2-1.1-2.2 1.1.5-2.3-1.8-1.7 2.4-.4z"/></svg>',
 pass:'<svg viewBox="0 0 24 24"><path d="m12 2 8 4v6c0 5-4 8-8 10-4-2-8-5-8-10V6z"/><path d="m12 7 1.5 3.2 3.5.5-2.5 2.4.6 3.5-3.1-1.7-3.1 1.7.6-3.5L7 10.7l3.5-.5z"/></svg>',
 store:'<svg viewBox="0 0 24 24"><path d="M5 9h14l-1 12H6zM9 10V7a3 3 0 0 1 6 0v3M4 9h16"/></svg>'
};
function nav(){const wrap=$('bottomNav');wrap.innerHTML=tabs.map(([p,ic,l])=>`<button type="button" data-page="${p}" aria-label="${l}" ${state.page===p?'aria-current="page"':''} class="${state.page===p?'active':''}"><span class="symbol" aria-hidden="true">${navIcons[p]||ic}</span>${l}</button>`).join('')}
function showToast(msg){const el=$('toast');el.textContent=msg;el.classList.add('show');clearTimeout(showToast.t);showToast.t=setTimeout(()=>el.classList.remove('show'),2400)}
function go(page){state.page=(page==='builds'||page==='meta')?'weapons':page;window.scrollTo(0,0);render()}
function featured(){return state.feed.builds.find(b=>b.id==='han-iron')}
function leaderCard(board,entry){
 if(!entry)return `<div class="leader-card leader-card--empty" role="status"><span class="leader-card__source">${escapeHTML(board.name)}</span><span class="leader-card__description">No ranked weapon in this category in the current reviewed snapshot.</span></div>`;
 const overall=board.rankingType==='Overall editorial top five';
 const scope=overall?'Overall':entry.category==='AR'?'Assault Rifle':entry.category;
 const description=overall?'Overall multiplayer ranking':`${entry.category==='AR'?'Assault rifle':entry.category} ranking`;
 return `<button type="button" class="leader-card leader-card--${escapeHTML(board.id)}" data-source="${escapeHTML(board.id)}" data-page="weapons" data-weapon="${escapeHTML(entry.weapon)}" data-reveal="loadout" data-weapon-group="${escapeHTML(entry.category)}" aria-label="View ${escapeHTML(entry.weapon)} rankings and loadouts from ${escapeHTML(board.name)}">
 <span class="leader-card__top"><span class="leader-card__source">${escapeHTML(board.name)}</span><span class="leader-card__index">#${entry.rank} ${escapeHTML(scope)}</span></span>
 <span class="leader-card__weapon">${escapeHTML(entry.weapon)}</span>
 <span class="leader-card__description">${escapeHTML(description)}</span>
 <span class="leader-card__bottom"><span>${escapeHTML(pretty(board.updated))}</span><span class="leader-card__action">VIEW LOADOUT <span aria-hidden="true">↗</span></span></span>
 </button>`;
}

const storeCacheKey='mw4-warroom-store-v1';
const storePublicFeed='https://raw.githubusercontent.com/zy65h95wjn-netizen/mw4-war-room/store-feed/data/store.json';
function storeProviderLink(feed){
 const url=WarRoomStore.safeLink(feed?.attribution?.url,new Set(['itemshop.gg']))||WarRoomStore.STORE_URL;
 return `<a class="source-link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">Data from itemshop.gg <span aria-hidden="true">↗</span></a>`;
}
function storeNotice(feed){
 if(!feed)return 'Checking public Store information…';
 if(feed.status==='sample')return 'Example from October 27 · live Store updates not connected yet.';
 const when=new Date(feed.checkedAt).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
 if(feed.stale)return 'Provider reports outdated Store data · checked '+when+'.';
 if(!WarRoomStore.isFresh(feed))return 'Last checked '+when+' · may be outdated.';
 return 'Public web-store listing checked '+when+'.';
}
function storeArt(item){
 const image=WarRoomStore.safeLink(item.image,new Set(['cdn.source.gs','itemshop.gg','mw4.source.gs']));
 return image?`<img loading="lazy" decoding="async" src="${escapeHTML(image)}" alt="${escapeHTML(item.name)} bundle artwork">`:'<div class="store-art-fallback" aria-hidden="true">MW4</div>';
}
function storeCard(item,{compact=false,sample=false}={}){
 const price=WarRoomStore.displayPrice(item.price);
 const link=WarRoomStore.safeLink(item.officialUrl,new Set(['callofduty.com','www.callofduty.com']))||WarRoomStore.STORE_URL;
 const c=item.contents||[];
 const label=item.upcoming?'UPCOMING':sample?'EXAMPLE · NOT LIVE':item.badge||'MW4 WEB STORE';
 return `<article class="store-card ${compact?'store-card--compact':''}">
  <div class="store-card__art">${storeArt(item)}</div>
  <div class="store-card__info">
   <div class="store-card__label">${escapeHTML(label)}</div>
   <h3>${escapeHTML(item.name)}</h3>
   <div class="store-card__type">${escapeHTML(item.type||'Bundle')}</div>
   <div class="store-card__price">${escapeHTML(price)}</div>
   ${!compact&&c.length?`<details class="store-contents"><summary>What's included (${c.length}${sample?' shown':''})</summary><ul>${c.map(v=>`<li>${escapeHTML(v.name)} <span>${escapeHTML(v.type)}</span></li>`).join('')}</ul></details>`:''}
   <a class="store-card__link" target="_blank" rel="noopener noreferrer" href="${escapeHTML(link)}">${item.officialUrl?'Official bundle details':'View source listing'} <span aria-hidden="true">↗</span></a>
  </div>
 </article>`;
}
function storePreview(){
 const feed=state.store.data,example=feed?.status==='sample',item=feed?.items?.[0];
 return `${section('New in Store',tag(feed?.status==='synced'&&!feed.stale?'PUBLIC STORE':'NOT LIVE','muted'))}
 <div class="store-preview">
  <div class="store-preview__header"><span>${escapeHTML(storeNotice(feed))}</span>${storeProviderLink(feed)}</div>
  ${item?storeCard(item,{compact:true,sample:example}):`<p class="subtext" style="padding:15px 0">${feed?'No MW4 bundles appear in this source snapshot.':'Loading Store details…'}</p>`}
  <div class="store-preview__footer"><span>Public web listings only · in-game offers may differ.</span><button type="button" class="cta secondary" data-page="store">Browse Store</button></div>
 </div>`;
}
function storePage(){
 const feed=state.store.data,items=feed?.items||[],sample=feed?.status==='sample';
 return `${headline('Store','MW4 bundles, blueprints and cosmetics from the public web store.','STORE & BUNDLES')}
 <section class="panel flat">
  <div class="spread" style="flex-wrap:wrap;gap:8px"><strong>${sample?'Dated Example':feed?.status==='synced'?'Public MW4 Listings':'Store Connection'}</strong>${tag(sample?'NOT LIVE':feed?.stale?'SOURCE STALE':feed?.status==='synced'?'SYNCED':'NOT CONNECTED',sample||feed?.stale?'amber':'muted')}</div>
  <p class="subtext" style="margin:9px 0">${escapeHTML(storeNotice(feed))}</p>
  <div class="spread" style="flex-wrap:wrap">${storeProviderLink(feed)}<a class="source-link" href="https://www.callofduty.com/en/store" target="_blank" rel="noopener noreferrer">Official Call of Duty Store ↗</a></div>
 </section>
 ${items.length?`<div class="store-list">${items.map(item=>storeCard(item,{sample})).join('')}</div>`:`<div class="panel flat"><h2>${feed?'No MW4 bundles listed':'Store data not available yet'}</h2><p class="subtext" style="margin-top:8px">${feed?'The source has no MW4 web-store listings in the latest available snapshot.':'The public Store feed has not been connected yet. No personal account sign-in is needed.'}</p></div>`}
 <div class="detail">This is not your personal in-game Store. Offers and prices can differ by platform or account. A missing price does not mean an item is free; verify the official store before purchasing.</div>`;
}

function briefingDesktop(){
 const p=state.feed.patches[0],b=state.feed.battlePass;
 const metaA=state.feed.meta.find(s=>s.id==='cod'),metaB=state.feed.meta.find(s=>s.id==='wz');
 const leaders=category=>[metaA,metaB].map(board=>({board,entry:board.entries.filter(e=>e.category===category).sort((a,b)=>a.rank-b.rank)[0]||null}));
 const today=new Date();today.setHours(0,0,0,0);
 const next=state.feed.events.filter(e=>dateVal(e.starts)>=today).sort((a,b)=>a.starts.localeCompare(b.starts))[0];
 return `
 ${dataNotice()}
 <section class="brief-mast" aria-labelledby="brief-title">
   <div class="brief-mast__top"><div class="brief-mast__label"><span class="brief-signal" aria-hidden="true"></span><span>MW4 MULTIPLAYER</span></div><span class="brief-mast__mode">GAME UPDATES</span></div>
   <div class="brief-mast__body">
     <div class="brief-mast__identity"><h1 id="brief-title">Overview</h1><p>Weapons, builds, updates, and events.</p></div>
     <div class="brief-mast__stamp"><span>LAST REVIEW</span><strong>${escapeHTML(pretty(state.feed.reviewed,{year:'numeric'}))}</strong></div>
   </div>
 </section>
 ${section('Top Weapons',tag('2 RANKING SOURCES','muted'))}
 <div class="brief-leader-group" aria-label="Assault rifle meta leaders">
   <div class="brief-leader-category"><h3>ASSAULT RIFLES</h3></div>
   <div class="brief-leaders" aria-label="Top assault rifles by publisher">${leaders('AR').map(({board,entry})=>leaderCard(board,entry)).join('')}</div>
 </div>
 <div class="brief-leader-group brief-leader-group--smg" aria-label="Submachine gun meta leaders">
   <div class="brief-leader-category"><h3>SUBMACHINE GUNS</h3></div>
   <div class="brief-leaders" aria-label="Top submachine guns by publisher">${leaders('SMG').map(({board,entry})=>leaderCard(board,entry)).join('')}</div>
 </div>
 <p class="brief-explain">Sources rank weapons differently. Tap a weapon to see its loadouts.</p>
 ${section('Latest Updates',tag('DATED SNAPSHOT','amber'))}
 <div class="intel-grid">
   <button type="button" class="intel-signal intel-signal--patch" data-page="updates" aria-label="View latest reviewed patch notes">
     <span class="intel-signal__eyebrow">PATCH NOTES</span>
     <strong class="intel-signal__title">${escapeHTML(p.title)}</strong>
     <span class="intel-signal__bottom"><span>${escapeHTML(pretty(p.date))}</span><span class="intel-signal__action">VIEW NOTES <span aria-hidden="true">↗</span></span></span>
   </button>
   <button type="button" class="intel-signal intel-signal--events" data-page="events" aria-label="View upcoming event announcements">
     <span class="intel-signal__eyebrow">EVENTS</span>
     <strong class="intel-signal__title">${next?escapeHTML(next.title):'Event calendar'}</strong>
     <span class="intel-signal__bottom"><span>${next?escapeHTML(pretty(next.starts)+' · listed date'):'Check announcements'}</span><span class="intel-signal__action" aria-hidden="true">↗</span></span>
   </button>
   <button type="button" class="intel-signal intel-signal--pass" data-page="pass" aria-label="View Battle Pass information">
     <span class="intel-signal__eyebrow">BATTLE PASS</span>
     <strong class="intel-signal__title">${escapeHTML(b.label)}</strong>
     <span class="intel-signal__bottom"><span>${escapeHTML(pretty(b.start))} · reported</span><span class="intel-signal__action" aria-hidden="true">↗</span></span>
   </button>
 </div>
 <div class="brief-provenance"><span>Source-reviewed info · not live rankings</span>${anchor('officialIndex','Official patch notes')}</div>
 ${storePreview()}`;
}

/* iPhone-first esports Overview. Display order is not an invented combined ranking. */
const originalWeaponArt=Object.freeze({
 'HAN 86':'han-86',
 'Axion':'axion',
 'VEL 46':'vel-46',
 'ISO Nightshade':'iso-nightshade'
});
function mobileWeaponArt(weapon){
 const slug=originalWeaponArt[weapon];
 if(slug)return '<img class="mobile-weapon__illustration" src="./art/featured/'+slug+'.webp" width="260" height="106" loading="lazy" decoding="async" alt="Original illustrative artwork, not an official '+escapeHTML(weapon)+' game render">';
 return '<svg viewBox="0 0 150 55" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false"><path fill="currentColor" stroke="#d6e0e9" stroke-width="1.4" d="M8 22h14v-3h21v-7h18v-4h32v5h29v5h12v5h7v8h-16v4h-14l-5 11H84l-7-11H62l-5 12H45l-4-17H25l-3 8H12l2-12H8z"/><path stroke="#102230" stroke-width="2.4" fill="none" d="M25 23h97m-74-4h31M58 17v15m34-14v14M43 28h29M96 28h30"/><path fill="#e0a659" d="M74 29h5l4 13h-5z"/></svg>';
}
function mobilePicks(){
 const boards=state.feed.meta.filter(board=>board.id==='cod'||board.id==='wz');
 const categories=state.featuredCategory==='All'?['AR','SMG']:[state.featuredCategory];
 const picks=[];
 const seen=new Set();
 for(const category of categories){
  for(const board of boards){
   const entry=board.entries.filter(x=>x.category===category).sort((a,b)=>a.rank-b.rank)[0];
   if(entry&&!seen.has(entry.weapon)){picks.push({board,entry});seen.add(entry.weapon)}
  }
 }
 return picks;
}
function mobileWeaponRow({board,entry}){
 const overall=board.rankingType==='Overall editorial top five';
 const rankType=overall?'Overall':entry.category;
 const rank=String(entry.rank).padStart(2,'0');
 return '<button type="button" class="mobile-weapon mobile-weapon--'+escapeHTML(board.id)+'" data-source="'+escapeHTML(board.id)+'" data-page="weapons" data-weapon="'+escapeHTML(entry.weapon)+'" data-reveal="loadout" aria-label="View '+escapeHTML(entry.weapon)+' loadout: '+escapeHTML(board.name)+', rank '+entry.rank+' '+escapeHTML(rankType)+'">'+
 '<span class="mobile-weapon__rank" aria-hidden="true">'+escapeHTML(rank)+'</span>'+
 '<span class="mobile-weapon__art">'+mobileWeaponArt(entry.weapon)+'</span>'+
 '<span class="mobile-weapon__label"><strong class="mobile-weapon__name">'+escapeHTML(entry.weapon)+'</strong>'+
 '<span class="mobile-weapon__source">'+escapeHTML(board.name)+' · #'+entry.rank+' '+escapeHTML(rankType)+'</span></span>'+
 '<span class="mobile-weapon__arrow" aria-hidden="true">›</span></button>';
}
function mobileUpdateIcon(kind){
 const icons={
  patch:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M8 3h9l3 3v15H5V3h3m2 7h7m-7 4h7m-7 4h5M16 3v4h4"/></svg>',
  event:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18m9 3h2m-2 4h4"/></svg>',
  pass:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="m12 2 8 4v6c0 5-4 8-8 10-4-2-8-5-8-10V6zM9 12l2 2 4-4"/></svg>'
 };
 return icons[kind]||icons.patch;
}
function mobileUpdateRow({page,kind,title,detail,date}){
 return '<button class="mobile-update mobile-update--'+kind+'" type="button" data-page="'+page+'" aria-label="View '+escapeHTML(title)+' in '+(page==='pass'?'Battle Pass':page==='events'?'Events':'Updates')+'">'+
 '<span class="mobile-update__art">'+mobileUpdateIcon(kind)+'</span>'+
 '<span class="mobile-update__body"><strong>'+escapeHTML(title)+'</strong><span>'+escapeHTML(detail)+'</span></span>'+
 '<span class="mobile-update__date">'+escapeHTML(date)+'</span>'+
 '<span class="mobile-update__arrow" aria-hidden="true">›</span></button>';
}
function mobileStorePreview(){
 const feed=state.store.data,item=feed?.items?.[0],sample=feed?.status==='sample';
 return '<section class="mobile-group" aria-labelledby="mobile-store-heading">'+
 '<div class="mobile-group__title"><h2 id="mobile-store-heading">Featured Store</h2>'+
 '<button type="button" data-page="store">View all <span aria-hidden="true">→</span></button></div>'+
 '<div class="mobile-store">'+
 (item?storeCard(item,{compact:true,sample}):
 '<div class="mobile-store__message">'+escapeHTML(feed?'No MW4 bundles appear in this source snapshot.':'Loading Store details…')+'</div>')+
 '<div class="mobile-store__provenance">'+storeProviderLink(feed)+
 '<span>'+escapeHTML(storeNotice(feed))+'</span></div></div></section>';
}
function mobileBriefing(){
 const boards=state.feed.meta.filter(board=>board.id==='cod'||board.id==='wz');
 const choices=['All',...['AR','SMG','Sniper'].filter(category=>boards.some(b=>b.entries.some(e=>e.category===category)))];
 if(!choices.includes(state.featuredCategory))state.featuredCategory='All';
 const picks=mobilePicks();
 const p=state.feed.patches[0],b=state.feed.battlePass;
 const today=new Date();today.setHours(0,0,0,0);
 const next=state.feed.events.filter(e=>dateVal(e.starts)>=today).sort((a,c)=>a.starts.localeCompare(c.starts))[0];
 const rows=[
  {page:'updates',kind:'patch',title:p.title,detail:'Official patch notes · reviewed '+pretty(state.feed.reviewedSections.patches),date:pretty(p.date)},
  {page:'events',kind:'event',title:next?next.title:'Event calendar',detail:next?'Listed '+pretty(next.starts)+' · '+(next.scheduleConfidence==='official'?'announced':'reported'):'Check announced events',date:next?pretty(next.starts):'—'},
  {page:'pass',kind:'pass',title:b.label,detail:'Battle Pass · '+(String(b.startConfidence||'').toLowerCase().includes('reported')?'reported start date':'source-labeled start date'),date:pretty(b.start)}
 ];
 return dataNotice()+'<div class="mobile-briefing"><h1 class="mobile-sr-only">Overview</h1>'+
 '<section class="mobile-group" aria-labelledby="mobile-weapons-heading">'+
 '<div class="mobile-group__title"><h2 id="mobile-weapons-heading">Top Weapons</h2>'+
 '<button type="button" data-page="weapons">View all <span aria-hidden="true">→</span></button></div>'+
 '<div class="mobile-filter" role="group" aria-label="Featured weapon category">'+
 choices.map(c=>'<button type="button" data-featured-category="'+escapeHTML(c)+'" aria-pressed="'+(c===state.featuredCategory)+'">'+escapeHTML(c)+'</button>').join('')+
 '</div><div class="mobile-weapons">'+
 (picks.length?picks.map(mobileWeaponRow).join(''):'<p class="mobile-empty">No ranked weapons in this category in the reviewed sources.</p>')+
 '</div><div class="mobile-microcopy">'+freshness('meta')+
 '<span>Publisher ranks are separate, not one combined leaderboard. Artwork is illustrative.</span></div></section>'+
 '<section class="mobile-group" aria-labelledby="mobile-updates-heading">'+
 '<div class="mobile-group__title"><h2 id="mobile-updates-heading">Latest Updates</h2>'+
 '<button type="button" data-page="updates">View all <span aria-hidden="true">→</span></button></div>'+
 '<div class="mobile-updates">'+rows.map(mobileUpdateRow).join('')+'</div>'+
 '<div class="mobile-microcopy">Reviewed snapshot · verify current announcements in the source pages.</div></section>'+
 mobileStorePreview()+'</div>';
}
function briefing(){
 return '<div class="mobile-overview">'+mobileBriefing()+'</div><div class="desktop-overview">'+briefingDesktop()+'</div>';
}

function weaponHub(){
 const catalog=WarRoomLogic.weaponCatalog(state.feed);
 const board=state.feed.meta.find(m=>m.id===state.source)||state.feed.meta[0];
 const categories=['All',...new Set(catalog.map(w=>w.category))];
 if(!categories.includes(state.category))state.category='All';
 const query=state.search.trim().toLowerCase();
 const visible=catalog.filter(w=>(state.category==='All'||w.category===state.category)&&(!query||w.weapon.toLowerCase().includes(query)));
 const ranked=board.entries.filter(entry=>visible.some(w=>w.weapon===entry.weapon));
 const unranked=visible.filter(w=>!ranked.some(entry=>entry.weapon===w.weapon)&&w.builds.length);
 const selectedRecord=visible.find(w=>w.weapon===state.weapon)||visible.find(w=>w.weapon===ranked[0]?.weapon)||visible[0];
 if(selectedRecord && selectedRecord.weapon!==state.weapon){state.weapon=selectedRecord.weapon;state.buildId=''}
 const allBuilds=selectedRecord?.builds||[];
 const compatibleBuilds=allBuilds.filter(b=>!state.ironOnly||!b.optic);
 const activeBuild=compatibleBuilds.find(b=>b.id===state.buildId)||compatibleBuilds[0];
 return `${headline('Weapons & Loadouts','Compare published multiplayer rankings and find recommended builds for each weapon.','MULTIPLAYER WEAPONS')}
 <div class="horizontal" role="group" aria-label="Ranking publisher">${state.feed.meta.map(m=>`<button class="tab ${board.id===m.id?'active':''}" data-source="${escapeHTML(m.id)}" type="button">${escapeHTML(m.name)}</button>`).join('')}</div>
 <div class="panel flat" style="margin-top:7px"><div class="spread" style="flex-wrap:wrap">${freshness('meta')}${anchor(board.source,'View original rankings')}</div><p class="fine" style="margin-top:9px">${escapeHTML(board.rankingType)} · ${escapeHTML(pretty(board.updated))}</p><p class="source-note" style="margin-top:5px">${escapeHTML(board.note)}. Publisher positions are not combined into one universal ranking.</p></div>
 <div class="horizontal" role="group" aria-label="Weapon category">${categories.map(c=>`<button class="tab ${state.category===c?'active':''}" data-category="${escapeHTML(c)}" type="button">${escapeHTML(c)}</button>`).join('')}</div>
 <div style="margin:10px 0"><input class="input" id="buildSearch" value="${escapeHTML(state.search)}" placeholder="Search weapons…" aria-label="Search weapons"></div>
 <div class="panel flat"><div class="spread"><h2>Rankings & Loadouts</h2>${tag(visible.length+' WEAPONS')}</div><p class="fine" style="margin-top:5px">Select a gun to see its ranking and attachment options below. "Build" means a published recommendation, not your unlocked gear.</p><div class="small-rule" style="margin-bottom:0"></div>
 ${ranked.map(w=>{const info=visible.find(i=>i.weapon===w.weapon);return `<button class="taprow ${selectedRecord?.weapon===w.weapon?'selected':''}" type="button" data-weapon="${escapeHTML(w.weapon)}" aria-pressed="${selectedRecord?.weapon===w.weapon?'true':'false'}"><span class="number">#${w.rank}</span><span><span class="weapon">${escapeHTML(w.weapon)}</span><span class="subtext" style="display:block">${escapeHTML(w.category)} · ${escapeHTML(w.tier)} · ${info.builds.length} sourced build${info.builds.length===1?'':'s'}</span></span><span class="arrow" aria-hidden="true">›</span></button>`}).join('')}
 ${unranked.length?`<div class="fine" style="padding-top:14px">OTHER WEAPONS WITH PUBLISHED BUILDS (UNRANKED IN THIS SNAPSHOT)</div>${unranked.map(w=>`<button class="taprow ${selectedRecord?.weapon===w.weapon?'selected':''}" type="button" data-weapon="${escapeHTML(w.weapon)}"><span class="number cat">—</span><span><span class="weapon">${escapeHTML(w.weapon)}</span><span class="subtext" style="display:block">${escapeHTML(w.category)} · ${w.builds.length} sourced build${w.builds.length===1?'':'s'}</span></span><span class="arrow" aria-hidden="true">›</span></button>`).join('')}`:''}
 ${!visible.length?'<div class="empty">No matching weapons in this curated source selection. Try another category or search term.</div>':''}
 </div>
 ${selectedRecord?`<div id="weaponLoadout" class="panel gold-border" style="scroll-margin-top:16px"><div class="spread" style="align-items:flex-start"><div><div class="eyebrow">${escapeHTML(selectedRecord.category)} · WEAPON DETAILS</div><h2 style="font-size:24px;margin-top:5px">${escapeHTML(selectedRecord.weapon)}</h2></div>${tag(selectedRecord.builds.length+' BUILD'+(selectedRecord.builds.length===1?'':'S'),'amber')}</div>
 <div class="stack" style="margin-top:12px">${selectedRecord.rankings.map(r=>`<div class="spread"><span class="fine">${escapeHTML(r.boardName)} · ${escapeHTML(r.type)}</span><strong>#${r.rank} · ${escapeHTML(r.tier)}</strong></div>`).join('')||'<div class="fine">No published ranking in the two curated excerpts.</div>'}</div>
 <div class="small-rule"></div><div class="spread" style="flex-wrap:wrap"><h2>Recommended attachments</h2>${freshness('builds')}</div>
 <label class="switchwrap" style="margin-top:11px"><input type="checkbox" id="ironSwitch" ${state.ironOnly?'checked':''}><span>Iron sights first <span class="fine" style="display:block">Show only published no-optic builds</span></span>${tag(state.ironOnly?'ON':'OFF',state.ironOnly?'amber':'muted')}</label>
 ${!compatibleBuilds.length?`<div class="empty" style="margin-top:13px">${allBuilds.length?'No no-optic build has been verified in this snapshot. Turn off the iron-sight filter to see available optic builds.':'No verified loadout has been published in this curated snapshot for this weapon. Check the linked ranking source.'}</div>`:
 `<div class="stack" style="margin-top:12px">${compatibleBuilds.map(b=>`<button type="button" class="build-option ${activeBuild?.id===b.id?'active':''}" data-build="${escapeHTML(b.id)}"><span><strong>${escapeHTML(b.style)}</strong><span class="fine" style="display:block">${escapeHTML(source(b.source).name)} · ${escapeHTML(b.optic?'Optic':'Iron sights')}</span></span><span class="chevron">${activeBuild?.id===b.id?'●':'›'}</span></button>`).join('')}</div>
 ${activeBuild?`<p class="subtext" style="margin-top:13px">${escapeHTML(activeBuild.description)}</p>${section('Attachment slots',tag(activeBuild.parts.length+' STANDARD'+(activeBuild.apex?' + APEX':''),'amber'))}<div class="build-layout">${activeBuild.parts.map(([slot,name],i)=>`<div class="attachment"><span class="slotmark">${i+1}</span><span><span class="slot">${escapeHTML(slot)}</span><span class="part" style="display:block">${escapeHTML(name)}</span></span></div>`).join('')}${activeBuild.apex?`<div class="attachment apex"><span class="slotmark">★</span><span><span class="slot">Max-level Apex · separate slot</span><span class="part" style="display:block">${escapeHTML(activeBuild.apex)}</span></span></div>`:''}</div>
 ${activeBuild.extras?`<div class="small-rule"></div><h3>Published class pairing</h3>${Object.entries(activeBuild.extras).map(([k,v])=>`<div class="spread" style="align-items:flex-start;margin-top:8px"><span class="fine">${escapeHTML(k)}</span><strong style="font-size:11px;text-align:right;max-width:65%">${escapeHTML(v)}</strong></div>`).join('')}`:''}
 <div class="small-rule"></div><div class="spread" style="flex-wrap:wrap"><span class="fine">Source: ${escapeHTML(source(activeBuild.source).name)}<br>Published/reviewed ${escapeHTML(pretty(activeBuild.updated))}</span>${anchor(activeBuild.source,'Check original')}</div><div class="spread" style="margin-top:11px">${tag('UNLOCKS UNKNOWN','muted')}<button type="button" class="cta small-cta" data-copy="${escapeHTML(activeBuild.id)}">Copy build</button></div>`:''}`}
 </div><div class="detail">Attachment levels may differ from online databases. War Room does not know your personal unlocks. Rankings and loadouts are dated publisher snapshots, not a live feed.</div>`:''}`;
}
function updatesPage(){return `${headline('Patch Notes','Official multiplayer changes, with links to the full notes.','GAME UPDATES')}
 <div class="panel flat"><div class="spread">${freshness('patches')}${anchor('officialIndex','Full official index')}</div><div class="small-rule"></div><div class="detail">A tier-list ranking change does not prove a weapon buff or nerf. Only official patch notes establish documented balance changes; read the linked source for newer entries.</div></div>
 ${state.feed.patches.map((p,i)=>`<section class="panel"><div class="spread" style="align-items:flex-start"><div><div class="eyebrow">${escapeHTML(pretty(p.date,{year:'numeric'}))} · ${escapeHTML(p.scope)}</div><h2 style="margin-top:5px">${escapeHTML(p.title)}</h2></div>${i===0?tag('LATEST IN SNAPSHOT','amber'):''}</div>${p.bullet.map(s=>`<p class="bullet">${escapeHTML(s)}</p>`).join('')}<div style="margin-top:10px">${anchor(p.source,'Read official notes')}</div></section>`).join('')}
 <div class="panel flat"><h2>Want to check for a new patch?</h2><p class="subtext" style="margin:8px 0 14px">Open the official feed for the latest release. War Room’s summaries update when a new vetted briefing is published.</p>${anchor('officialIndex','All official patch notes')}</div>`}
function eventStatus(event){const state=WarRoomLogic.eventTiming(event);const tone={upcoming:'amber',window:'green',unconfirmed:'muted',ended:'red'}[state.kind]||'muted';return tag(state.label,tone)}
function eventPage(){const events=WarRoomLogic.orderedEvents(state.feed.events);return `${headline('Events','Event dates and rewards, with clear labels for unconfirmed information.','EVENTS & REWARDS')}
 <div class="status-line" style="margin-bottom:12px">${freshness('events')}${tag('MP EVENTS','muted')}</div><p class="source-note" style="margin:9px 0 14px">"Within window" describes published calendar dates, <strong>not verified in-game availability</strong>. Unknown end dates remain unconfirmed. Official and community-reported dates are distinguished.</p>
 ${events.map(e=>`<section class="event-row"><div class="spread" style="align-items:flex-start"><div><div class="eyebrow">${escapeHTML(e.tag)}</div><h3 style="margin-top:5px">${escapeHTML(e.title)}</h3></div>${eventStatus(e)}</div><p>${escapeHTML(e.summary)}</p><div class="spread" style="margin-top:10px;flex-wrap:wrap"><span class="fine">From ${escapeHTML(pretty(e.starts))}${e.ends?' · Through '+escapeHTML(pretty(e.ends)):' · End not verified'}</span>${anchor(e.source,'Details')}</div><div class="fine" style="margin-top:6px">Dates: ${escapeHTML(e.scheduleConfidence==='official'?'official announcement':'community-reported')} ${e.endCertainty?'· End: '+escapeHTML(e.endCertainty):''}</div>${e.rewards.length?`<div class="rewardbox"><div class="eyebrow">Published rewards</div>${e.rewards.map(x=>`<p>· ${escapeHTML(x)}</p>`).join('')}${e.note?`<div class="small-rule"></div><div class="fine">${escapeHTML(e.note)}</div>`:''}</div>`:''}</section>`).join('')}
 <div class="detail">These entries are from the dated reviewed snapshot. If event review is overdue, verify the current game schedule before relying on an announced date.</div>`}
function passPage(){const b=state.feed.battlePass,today=new Date(),start=dateVal(b.start);const hasElapsed=today>=start;return `<div class="panel season-hero"><div class="spread">${tag('SEASON 1','amber')}${freshness('battlePass')}</div><div style="margin-top:16px"><div class="eyebrow">REPORTED START DATE</div><div class="bigdate" style="margin-top:5px">${escapeHTML(pretty(b.start,{year:'numeric'}))}</div><p class="fine" style="margin-top:6px">${escapeHTML(b.startConfidence)}</p></div><div class="divider"></div><p class="source-note">${escapeHTML(b.officialSummary)}</p>${hasElapsed?`<p class="detail" style="margin-top:12px">This date has passed. Verify live season status; War Room has not refreshed this snapshot yet.</p>`:''}</div>
 <div class="panel flat"><h2>What we know about rewards</h2><p class="subtext" style="margin:6px 0 12px">Officially described categories; not a published list of individual tiers.</p><div class="two-col">${b.rewardCategories.map(c=>`<div class="weaponchip" style="justify-content:center;text-align:center;min-height:40px">${escapeHTML(c)}</div>`).join('')}</div><div class="small-rule"></div>${anchor(b.verifiedSource,'Official Battle Pass details')}</div>
 <div class="panel"><div class="spread"><h2>BlackCell at a glance</h2>${tag('Optional paid tier','muted')}</div><div class="two-col" style="margin-top:12px"><div class="mini-metric"><div class="eyebrow">Instant COD Points</div><strong>${escapeHTML(b.blackcell.codPoints.toLocaleString())}</strong><div class="fine">Per official edition offer</div></div><div class="mini-metric"><div class="eyebrow">Tier skips</div><strong>${escapeHTML(b.blackcell.tierSkips)}</strong><div class="fine">Instant unlock</div></div></div><p class="subtext" style="margin-top:12px">${escapeHTML(b.blackcell.exclusive)}. ${escapeHTML(b.blackcell.totalRewards)}.</p><div class="small-rule"></div><p class="fine">This is information, not a purchase recommendation. Regular free Battle Pass rewards are not yet listed individually.</p>${anchor(b.verifiedSource,'View official terms')}</div>
 <div class="detail">Season 1 and Battle Pass details may change. Dates credited to the roadmap report are not independently confirmed as an official start hour.</div>`}
function battlePassPage(){return `${headline('Battle Pass','Season 1 rewards and BlackCell details from published sources.','SEASON DETAILS')}${passPage()}`}
function sourcesSheet(){const list=state.feed.sources.map(s=>`<div class="source-card"><div class="spread">${anchor(s.id,s.name)}${tag(s.class,s.class==='Official'?'green':'muted')}</div></div>`).join('');return `<p class="subtext" style="margin-bottom:12px">${escapeHTML(state.feed.sourcePolicy)}</p><div class="spread" style="margin-bottom:14px">${freshness()}${tag('v'+state.feed.release)}</div><p class="fine" style="margin-bottom:12px">Each section has its own review deadline; dates mean editorial review, not live external syncing.</p><div class="stack" style="margin-bottom:14px">${['meta','builds','patches','events','battlePass'].map(k=>`<div class="spread"><span class="fine">${escapeHTML(k)}</span>${freshness(k)}</div>`).join('')}</div><p class="detail" style="margin-bottom:15px">The site has no login or connection to Activision or Xbox. Previous v0.1 personal entries remain untouched in their old browser storage, but are not read by this version.</p><div class="source-grid">${list}</div><p class="fine" style="margin-top:13px">Publishing an updated snapshot requires a new site data update. Opening a linked publisher page is the way to check its latest independently.</p>`}
function render(){nav();if(!state.feed)return;$('appMain').innerHTML=({brief:briefing,weapons:weaponHub,updates:updatesPage,events:eventPage,pass:battlePassPage,store:storePage}[state.page]||briefing)()}
async function copyBuild(id){const b=state.feed.builds.find(b=>b.id===id);if(!b)return;const s=source(b.source);const txt=[`MW4 MULTIPLAYER — ${b.weapon}`,b.style,...b.parts.map(([slot,part])=>`${slot}: ${part}`),...(b.apex?[`Apex: ${b.apex}`]:[]),...(b.extras?Object.entries(b.extras).map(([slot,v])=>`${slot}: ${v}`):[]),`Source: ${s.name}`,s.url,`Reviewed: ${b.updated}`].join('\n');try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(txt)}else{const ta=document.createElement('textarea');ta.value=txt;document.body.append(ta);ta.select();if(!document.execCommand('copy'))throw Error('No clipboard');ta.remove()}showToast('Build copied to clipboard')}catch(_e){showToast('Copy unavailable — long-press the attachments instead')}}
function bindEvents(){document.addEventListener('click',event=>{
 const button=event.target.closest('button');if(!button)return;
 if(button.id==='sourcesBtn'){ $('sheetContent').innerHTML=sourcesSheet();$('overlay').hidden=false;$('closeSheet').focus();return }
 if(button.id==='closeSheet'){$('overlay').hidden=true;$('sourcesBtn').focus();return}
 if(button.dataset.featuredCategory){state.featuredCategory=button.dataset.featuredCategory;render();return}
 if(button.dataset.source){state.source=button.dataset.source;settingsSave()}
 if(button.dataset.category){state.category=button.dataset.category;render();return}
 // Events and Battle Pass have their own navigation destinations.
 if(button.dataset.weapon){state.weapon=button.dataset.weapon;state.buildId='';state.search='';state.category='All'}
 if(button.dataset.build){state.buildId=button.dataset.build}
 if(button.dataset.copy){copyBuild(button.dataset.copy);return}
 const reveal=button.dataset.reveal==='loadout'||Boolean(button.dataset.weapon)||button.dataset.page==='builds';
 if(button.dataset.page){go(button.dataset.page);if(reveal)$('weaponLoadout')?.scrollIntoView({block:'start'});return}
 render();
 if(reveal)$('weaponLoadout')?.scrollIntoView({block:'start'});
 });
 $('overlay').addEventListener('click',event=>{if(event.target===$('overlay'))$('overlay').hidden=true});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('overlay').hidden)$('overlay').hidden=true});
 document.addEventListener('change',event=>{if(event.target.id==='ironSwitch'){state.ironOnly=event.target.checked;state.buildId='';state.search='';settingsSave();render()}});
 document.addEventListener('input',event=>{if(event.target.id==='buildSearch'){const cursor=event.target.selectionStart;state.search=event.target.value;render();const field=$('buildSearch');field?.focus();try{field?.setSelectionRange(cursor,cursor)}catch(_e){}}});
}
const intelCacheKey='mw4-warroom-last-validated-intel-v021';
function usableIntel(info){
 if(!info||info.schema!==2||!Array.isArray(info.sources)||info.sources.length<5||!Array.isArray(info.builds)||!info.builds.some(b=>b.id==='han-iron')||!Array.isArray(info.meta)||!info.meta.some(m=>m.id==='cod'&&m.entries?.length)||!info.meta.some(m=>m.id==='wz'&&m.entries?.length)||!Array.isArray(info.patches)||!info.patches.length||!Array.isArray(info.events)||!info.events.length||!info.battlePass||!info.battlePass.blackcell)return false;
 if(!/^\d{4}-\d{2}-\d{2}$/.test(info.reviewed))return false;
 for(const k of ['meta','builds','patches','events','battlePass']){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(info.reviewedSections?.[k]||'')||!Number.isInteger(info.reviewLimitsDays?.[k]))return false;
 }
 const ids=new Set(info.sources.map(s=>s.id));return info.builds.every(b=>ids.has(b.source)&&Array.isArray(b.parts)&&b.parts.length>0)&&info.patches.every(p=>ids.has(p.source))&&info.events.every(e=>ids.has(e.source))&&info.meta.every(m=>ids.has(m.source));
}
async function loadStore(){
 let data=null,origin='unavailable';
 try{
  // This is public filtered JSON on our own GitHub branch, not the provider API.
  // No API key or personalized player information ever reaches the browser.
  const url=storePublicFeed+'?cache='+Math.floor(Date.now()/600000);
  const response=await fetch(url,{cache:'no-store'});
  if(response.ok){
   const remote=await response.json();
   if(WarRoomStore.validStore(remote)&&remote.status==='synced'){data=remote;origin='public-feed';
    try{localStorage.setItem(storeCacheKey,JSON.stringify(remote))}catch(_e){}
   }
  }
 }catch(_e){}
 if(!data)try{
  const saved=JSON.parse(localStorage.getItem(storeCacheKey)||'null');
  if(WarRoomStore.validStore(saved)&&saved.status==='synced'){data=saved;origin='saved-copy'}
 }catch(_e){}
 if(!data)try{
  const response=await fetch('./data/store.json',{cache:'no-store'});
  if(response.ok){
   const local=await response.json();
   if(WarRoomStore.validStore(local)){data=local;origin='dated-example'}
  }
 }catch(_e){}
 state.store={data,origin};
 if(state.feed)render();
}
async function boot(){bindEvents();try{
 const response=await fetch('./data/intel.json',{cache:'no-store'});
 if(!response.ok)throw Error('Game information unavailable: HTTP '+response.status);
 const info=await response.json();
 if(!usableIntel(info))throw Error('Rejected unvalidated briefing');
 WarRoomLogic.weaponCatalog(info);
 state.feed=info;state.offlineCopy=navigator.onLine===false||response.headers.get('X-WarRoom-Saved')==='true';
 try{localStorage.setItem(intelCacheKey,JSON.stringify(info))}catch(_e){}
 render();loadStore();
 }catch(error){console.warn('War Room game information unavailable',error);
 try{const saved=JSON.parse(localStorage.getItem(intelCacheKey)||'null');if(usableIntel(saved)){WarRoomLogic.weaponCatalog(saved);state.feed=saved;state.offlineCopy=true;render();loadStore();return}}catch(_e){}
 $('appMain').innerHTML=`<div class="panel"><div class="eyebrow">GAME INFO UNAVAILABLE</div><h1 style="margin:8px 0">Couldn't load game info</h1><p class="subtext">The latest information couldn't be verified, and no saved copy is available. Open War Room online to save a copy for offline use.</p><button class="cta" id="retryBoot" type="button" onclick="location.reload()">Retry loading</button></div>`}}
boot();
if('serviceWorker'in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
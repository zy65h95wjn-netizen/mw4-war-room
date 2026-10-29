'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const arsenal=require('../arsenal.js');
const {weaponCatalog}=require('../logic.js');
const intel=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/intel.json'),'utf8'));
const expectedCounts={AR:8,SMG:5,Shotgun:2,LMG:3,Marksman:3,Sniper:3,Pistol:4,Launcher:4,Melee:1};
const curated=new Set(weaponCatalog(intel).map(x=>x.weapon));
test('official weapon roster has 33 unique entries across all nine launch categories',()=>{
 const all=arsenal.weapons;
 assert.equal(all.length,33);
 assert.equal(new Set(all.map(w=>w.weapon)).size,33);
 for(const [category,count] of Object.entries(expectedCounts)){
   assert.equal(all.filter(w=>w.category===category).length,count,category);
 }
 assert.match(arsenal.source,/^https:\/\/www\.callofduty\.com\/blog\/2026\/10\//);
 assert.equal(arsenal.reviewed,'2026-10-28');
 for(const entry of all){
   assert.deepEqual(Object.keys(entry).sort(),['category','weapon']);
 }
});

test('ten existing curated weapons are present with consistent categories, but no fabricated metadata',()=>{
 const existing=weaponCatalog(intel);
 assert.equal(existing.length,10);
 const lookup=new Map(arsenal.weapons.map(x=>[x.weapon,x.category]));
 for(const item of existing) assert.equal(lookup.get(item.weapon),item.category,item.weapon);
 assert.ok(lookup.has('PILA')&&lookup.has('FSS Carbon Edge 1095'));
 assert.ok(lookup.has('Cronen Squall'));
});

test('all 23 new weapon concepts address unique atlas tiles, existing ten remain separate',()=>{
 const seen=new Set();
 for(const entry of arsenal.weapons){
   const loc=arsenal.spriteLocation(entry.weapon);
   if(curated.has(entry.weapon)){
     assert.equal(loc,null,entry.weapon+' must preserve approved individual WebP');
   }else{
     assert.ok(loc,entry.weapon+' missing atlas position');
     assert.ok([0,25,50,75,100].includes(loc.x));
     assert.ok([0,25,50,75,100].includes(loc.y));
     assert.ok(!seen.has(loc.row+':'+loc.col),'duplicate artwork tile');
     seen.add(loc.row+':'+loc.col);
   }
 }
 assert.equal(seen.size,23);
 assert.equal(arsenal.spriteLocation('Fictional Gun'),null);
 const art=fs.readFileSync(path.join(__dirname,'../art/featured/full-arsenal-atlas.webp'));
 assert.equal(art.toString('ascii',0,4),'RIFF');
 assert.equal(art.toString('ascii',8,12),'WEBP');
 assert.ok(art.length<100000,'atlas must stay lightweight for iPhone');
});

test('arsenal loads with separate stylesheet and no changes to Store credentials',()=>{
 const index=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
 const sw=fs.readFileSync(path.join(__dirname,'../sw.js'),'utf8');
 const css=fs.readFileSync(path.join(__dirname,'../arsenal.css'),'utf8');
 assert.match(index,/src="arsenal\.js\?v=armory-20261028-1" defer/);
 assert.match(index,/href="arsenal\.css\?v=armory-20261028-1"/);
 assert.ok(index.indexOf('src="arsenal.js?v=')<index.indexOf('src="app.js?v='));
 assert.match(sw,/\.\/arsenal\.js/);
 assert.match(sw,/\.\/arsenal\.css/);
 assert.match(sw,/\.\/art\/featured\/full-arsenal-atlas\.webp/);
 assert.match(css,/background-size:500% 500%/);
 assert.match(css,/@media\(max-width:375px\)/);
 assert.doesNotMatch(index,/ITEMSHOP_API_KEY|api\/v1\/shop/);
});

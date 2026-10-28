'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {validStore,displayPrice,isFresh,safeLink,STORE_URL}=require('../store.js');
const sample=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/store.json'),'utf8'));

test('the documented MW4 example is valid but conspicuously not live',()=>{
 assert.equal(validStore(sample),true);
 assert.equal(sample.status,'sample');
 assert.equal(sample.stale,true);
 assert.equal(isFresh(sample),false);
 assert.equal(sample.items.length,1);
 assert.match(sample.note,/Not a live store feed/);
});

test('prices preserve null and never manufacture COD Point or USD amounts',()=>{
 assert.equal(displayPrice(sample.items[0].price),'Platform store');
 assert.equal(displayPrice({amount:null,label:null,currency:'COD Points'}),'Price not published');
 assert.equal(displayPrice({amount:2400,label:null,currency:'COD Points'}),'2,400 CP');
 assert.equal(displayPrice({amount:19.99,label:null,currency:'USD'}),'$19.99');
});

test('only attributed MW4-shaped Store records are accepted',()=>{
 assert.equal(validStore({...sample,game:'black-ops-7'}),false);
 assert.equal(validStore({...sample,provider:'untrusted'}),false);
 assert.equal(validStore({...sample,attribution:{text:'Data from itemshop.gg',url:'https://evil.example'}}),false);
 assert.equal(validStore({...sample,items:[...sample.items,sample.items[0]]}),false);
});

test('Store image and official links are restricted to known provider domains',()=>{
 assert.equal(safeLink('javascript:alert(1)',new Set(['itemshop.gg'])),null);
 assert.equal(safeLink('https://itemshop.gg.evil.example/shop',new Set(['itemshop.gg'])),null);
 assert.equal(safeLink('https://itemshop.gg/call-of-duty',new Set(['itemshop.gg'])),STORE_URL);
 const bad=structuredClone(sample);
 bad.items[0].image='https://untrusted.example/tracker.gif';
 assert.equal(validStore(bad),false);
 const redirected=structuredClone(sample);
 redirected.items[0].officialUrl='https://malicious.example/buy';
 assert.equal(validStore(redirected),false);
});

test('a recent successful projection may be labeled checked while source stale remains stale',()=>{
 const data=structuredClone(sample);
 data.status='synced';
 data.stale=false;
 data.checkedAt='2026-10-27T18:00:00Z';
 assert.equal(validStore(data),true);
 assert.equal(isFresh(data,Date.parse('2026-10-27T19:00:00Z')),true);
 assert.equal(isFresh(data,Date.parse('2026-10-29T19:00:00Z')),false);
 data.stale=true;
 assert.equal(isFresh(data,Date.parse('2026-10-27T19:00:00Z')),false);
});

test('server-side action stores only transformed public records, not credentials',()=>{
 const workflow=fs.readFileSync(path.join(__dirname,'../.github/workflows/store-feed.yml'),'utf8');
 const app=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
 assert.match(workflow,/secrets\.ITEMSHOP_API_KEY/);
 assert.match(workflow,/ref: store-feed/);
 assert.match(workflow,/python3 source\/scripts\/refresh_store\.py/);
 assert.match(workflow,/contents: write/);
 assert.doesNotMatch(app,/Bearer\s+isg_/);
 assert.doesNotMatch(app,/api\/v1\/shop\/call-of-duty/);
});

test('client avoids a false live store when source is an example',()=>{
 const item=sample.items[0];
 assert.match(item.officialUrl,/callofduty.com/);
 assert.equal(item.price.amount,null);
 assert.match(sample.note,/Example|Not a live/);
 const live={...sample,status:'synced',checkedAt:'2026-10-27T18:00:00Z',stale:false};
 assert.equal(validStore(live),true);
});

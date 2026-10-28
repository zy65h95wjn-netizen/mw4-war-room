/* Minimal public Store data helpers. No API credentials are ever read in the browser. */
(function(root){
'use strict';
const IMAGE_HOSTS=new Set(['cdn.source.gs','itemshop.gg','mw4.source.gs']);
const STORE_URL='https://itemshop.gg/call-of-duty';
function safeLink(value,hosts){
 if(typeof value!=='string'||value.length>1500)return null;
 try{
  const url=new URL(value);
  return url.protocol==='https:'&&hosts.has(url.hostname)&&!url.username&&!url.password&&!url.hash?value:null;
 }catch(_e){return null}
}
function validTimestamp(value){
 return typeof value==='string'&&value.length<=36&&/^\d{4}-\d\d-\d\dT/.test(value)&&Number.isFinite(Date.parse(value));
}
function validStore(data){
 if(!data||data.schema!==1||data.provider!=='itemshop.gg'||data.game!=='call-of-duty')return false;
 if(!['sample','synced'].includes(data.status)||!Array.isArray(data.items)||data.items.length>30)return false;
 if(!data.attribution||!safeLink(data.attribution.url,new Set(['itemshop.gg'])))return false;
 if(data.attribution.text!=='Data from itemshop.gg'||!validTimestamp(data.updatedAt))return false;
 if(!/^\d{4}-\d\d-\d\d$/.test(data.shopDate||'')||typeof data.stale!=='boolean')return false;
 if(data.status==='synced'&&!validTimestamp(data.checkedAt))return false;
 const ids=new Set();
 return data.items.every(item=>{
  if(!item||typeof item.id!=='string'||item.id.length>110||!item.id||ids.has(item.id))return false;
  ids.add(item.id);
  if(typeof item.name!=='string'||!item.name.trim()||item.name.length>130)return false;
  if(item.image&&!safeLink(item.image,IMAGE_HOSTS))return false;
  if(item.officialUrl&&!safeLink(item.officialUrl,new Set(['callofduty.com','www.callofduty.com'])))return false;
  if(!item.price||typeof item.price!=='object')return false;
  const amount=item.price.amount;
  if(amount!==null&&(!Number.isFinite(amount)||amount<0||amount>100000))return false;
  if(item.price.label!==null&&typeof item.price.label!=='string')return false;
  if(!Array.isArray(item.contents)||item.contents.length>20)return false;
  return item.contents.every(c=>c&&typeof c.name==='string'&&c.name.length<=100&&typeof c.type==='string');
 });
}
function displayPrice(price){
 if(!price||typeof price!=='object')return 'Price not published';
 if(typeof price.amount==='number'&&Number.isFinite(price.amount)){
  const currency=price.currency||'COD Points';
  if(currency==='COD Points')return price.amount.toLocaleString('en-US')+' CP';
  if(currency==='USD')return '$'+price.amount.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
  return price.amount.toLocaleString('en-US')+' '+currency;
 }
 return price.label||'Price not published';
}
function isFresh(data,now=Date.now()){
 if(!validStore(data)||data.status!=='synced'||data.stale)return false;
 return now-Date.parse(data.checkedAt)>=0&&now-Date.parse(data.checkedAt)<=36*60*60*1000;
}
const exports={validStore,displayPrice,isFresh,safeLink,STORE_URL};
if(typeof module!=='undefined'&&module.exports)module.exports=exports;
else root.WarRoomStore=exports;
})(typeof globalThis!=='undefined'?globalThis:this);

/* MW4 War Room: official launch-weapon roster, not an editorial ranking. 2026-10-19. */
(function(root){
 'use strict';
 const SOURCE='https://www.callofduty.com/blog/2026/10/call-of-duty-modern-warfare-4-launch-multiplayer-operators-weapons-equipment-create-a-class';
 const CATEGORIES=Object.freeze([
  ["AR",["HAN 86","M4","Hyeon Burst","Patriot XMR","Kastov 762","Oden","Axion","Cronen Squall"]],
  ["SMG",["ISO Nightshade","VEL 46","Wz.55 Striga","PPSh-41","X-58 Nyx"]],
  ["Shotgun",["Rezi 12","Warlord"]],
  ["LMG",["FiNN LMG","Type 73","APOC-338"]],
  ["Marksman",["MAR-9","Oris 8.6","Mosin-Nagant"]],
  ["Sniper",["KG-7 Vulcan","Astaroth .57","Signal 50"]],
  ["Pistol",["SANG 9mm","Krait P68",".50 GS","Mojave .357"]],
  ["Launcher",["PILA","RPG-8","JOKR","PM-40 Anvil"]],
  ["Melee",["FSS Carbon Edge 1095"]]
 ]);
 const WEAPONS=Object.freeze(CATEGORIES.flatMap(([category,names])=>names.map(name=>Object.freeze({weapon:name,category}))));
 const ATLAS_NAMES=Object.freeze(["Patriot XMR","Oden","Cronen Squall","Wz.55 Striga","Rezi 12","Warlord","FiNN LMG","Type 73","APOC-338","MAR-9","Oris 8.6","Mosin-Nagant","Astaroth .57","Signal 50","SANG 9mm","Krait P68",".50 GS","Mojave .357","PILA","RPG-8","JOKR","PM-40 Anvil","FSS Carbon Edge 1095"]);
 const ATLAS_INDEX=Object.freeze(Object.fromEntries(ATLAS_NAMES.map((name,i)=>[name,i])));
 function spriteLocation(name){
  const i=ATLAS_INDEX[name];
  if(i===undefined)return null;
  return {col:i%5,row:Math.floor(i/5),x:(i%5)*25,y:Math.floor(i/5)*25};
 }
 if(WEAPONS.length!==33 || new Set(WEAPONS.map(x=>x.weapon)).size!==33 || ATLAS_NAMES.length!==23)
  throw Error('Official arsenal count mismatch');
 const api=Object.freeze({source:SOURCE,reviewed:'2026-10-28',weapons:WEAPONS,categories:Object.freeze(CATEGORIES.map(x=>x[0])),spriteLocation});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.WarRoomArsenal=api;
})(typeof globalThis!=='undefined'?globalThis:this);

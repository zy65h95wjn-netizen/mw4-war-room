#!/usr/bin/env python3
"""Read-only Steam news leads for MW4 editorial review; never publishes game data."""
import argparse, hashlib, html, json, os, re, subprocess, sys
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit

APPID=1938090
API="https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
ISSUE="[War Room] Steam news leads for review"
LEDGER_START="<!-- war-room-steam-seen-v1\n"
LEDGER_END="\n-->"
MAX_SEEN=250
HOSTS={"store.steampowered.com","steamcommunity.com","steamstore-a.akamaihd.net","callofduty.com","www.callofduty.com"}
GAME=re.compile(r"\b(?:modern\s+warfare\s*(?:4|iv)|mw\s*4)\b",re.I)
TOPICS={
 "patches":re.compile(r"\b(?:patch(?:\s*notes?)?|hotfix|balance|balancing|weapon\s*tuning|bug\s*fix(?:es)?|updates?)\b",re.I),
 "events":re.compile(r"\b(?:events?|playlists?|maps?|modes?|infected|possession|shipment|boot\s*camp|haunting)\b",re.I),
 "battlePass":re.compile(r"\b(?:season\s*(?:one|\d+)|battle\s*pass|blackcell|roadmap|tier\s*skips?)\b",re.I)}
ROOT=Path(__file__).resolve().parents[1]

def sanitize(s):
 if not isinstance(s,str):return ""
 s=html.unescape(s)
 s=re.sub(r"[\x00-\x1f\x7f@*_<>{}\[\]|\\]"," ",s).replace(chr(96)," ")
 return re.sub(r"\s+"," ",s).strip()[:160]

def safe_url(s):
 if not isinstance(s,str) or len(s)>1024 or any(c in s for c in "\r\n)"):return None
 try:p=urlsplit(s)
 except ValueError:return None
 return s if p.scheme=="https" and p.hostname in HOSTS and not p.username and not p.password and p.path.startswith("/") else None

def normalize(raw,today=None):
 if not isinstance(raw,dict) or not isinstance(raw.get("appnews"),dict):raise ValueError("missing Steam appnews")
 news=raw["appnews"]
 if news.get("appid")!=APPID or not isinstance(news.get("newsitems"),list) or len(news["newsitems"])>40:
  raise ValueError("unexpected Steam news response")
 today=today or datetime.now(timezone.utc).date()
 limit=int(datetime.combine(today+timedelta(days=2),datetime.min.time(),timezone.utc).timestamp())
 result=[];seen=set()
 for e in news["newsitems"]:
  if not isinstance(e,dict):continue
  gid=e.get("gid");title=sanitize(e.get("title"));url=safe_url(e.get("url"));stamp=e.get("date")
  if not(isinstance(gid,str) and re.fullmatch(r"[a-zA-Z0-9_-]{5,72}",gid) and title and url and isinstance(stamp,int) and not isinstance(stamp,bool) and 1500000000<=stamp<=limit):continue
  if gid in seen:continue
  seen.add(gid)
  when=datetime.fromtimestamp(stamp,timezone.utc)
  result.append({"gid":gid,"title":title,"url":url,"date":when.date().isoformat(),"timestamp":stamp,"publishedAt":when.strftime("%Y-%m-%d %H:%M UTC")})
 return result

def leads(entries,reviewed):
 result=[]
 for e in entries:
  if not GAME.search(e["title"]):continue
  sections=[k for k,p in TOPICS.items() if p.search(e["title"]) and e["date"]>=reviewed[k]]
  if sections:result.append({**e,"sections":sections})
 return sorted(result,key=lambda e:(e["timestamp"],e["gid"]),reverse=True)

def fetch():
 u=API+"?"+urlencode({"appid":APPID,"count":40,"maxlength":100})
 req=Request(u,headers={"Accept":"application/json","User-Agent":"MW4WarRoom/0.3 read-only editorial news monitor"})
 with urlopen(req,timeout=12) as resp:
  if "json" not in resp.headers.get("Content-Type","").lower():raise ValueError("not a JSON response")
  body=resp.read(500001)
  if len(body)>500000:raise ValueError("news response too large")
 return json.loads(body)

def gh(*args):
 return subprocess.check_output(["gh",*args],text=True).strip()

def report(items):
 lines=["# Steam-listed MW4 announcement leads","",
 "**Unverified candidates, not confirmed multiplayer patches or events.**","",
 "Steam public news API, Call of Duty app 1938090; the feed includes multiple COD titles and may omit MW4 announcements.",
 "No announcement is published to War Room automatically. Validate the original official source and game mode first.",""]
 for e in items:
  lines.append("- [ ] "+e["publishedAt"]+" — "+e["title"]+" ("+", ".join(e["sections"])+") — [Steam listing]("+e["url"]+")")
 lines+=["","Only after a genuine source review, update the curated JSON and reviewed dates through a passing PR. Close this issue manually after completion.",""]
 return "\n".join(lines)

def lead_fingerprint(item):
 """Stable identity; timestamp and title detect revised headlines for the same gid."""
 required=("gid","timestamp","title","url","sections")
 if not isinstance(item,dict) or not all(k in item for k in required):
  raise ValueError("announcement missing identity fields")
 if not isinstance(item["timestamp"],int) or isinstance(item["timestamp"],bool):
  raise ValueError("announcement timestamp must be an integer")
 if not isinstance(item["sections"],list) or not all(x in TOPICS for x in item["sections"]):
  raise ValueError("invalid announcement sections")
 material={k:item[k] for k in ("gid","timestamp","title","url")}
 material["sections"]=sorted(set(item["sections"]))
 return hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()

def parse_seen(body):
 """Read a bounded, tamper-evident-shaped ledger from the existing review issue.
 This records what was alerted, not what any publisher actually confirmed.
 """
 if LEDGER_START not in body:
  if "war-room-steam-seen-v1" in body:
   raise ValueError("malformed announcement ledger marker")
  return []
 if body.count(LEDGER_START)!=1:
  raise ValueError("duplicate announcement ledger marker")
 front,marked=body.split(LEDGER_START,1)
 if marked.count(LEDGER_END)!=1:
  raise ValueError("missing/duplicated announcement ledger end marker")
 raw,trailing=marked.split(LEDGER_END,1)
 if trailing.strip():
  raise ValueError("unexpected content after announcement ledger")
 data=json.loads(raw)
 if not isinstance(data,dict) or data.get("schema")!=1 or not isinstance(data.get("seen"),list):
  raise ValueError("invalid announcement ledger format")
 seen=data["seen"]
 if len(seen)>MAX_SEEN:
  raise ValueError("announcement ledger exceeds safe size")
 hashes=set()
 for row in seen:
  if not isinstance(row,dict) or set(row)!={"gid","timestamp","fingerprint"}:
   raise ValueError("invalid announcement ledger item")
  if not isinstance(row["gid"],str) or not re.fullmatch(r"[a-zA-Z0-9_-]{5,72}",row["gid"]):
   raise ValueError("invalid announcement ledger gid")
  if not isinstance(row["timestamp"],int) or isinstance(row["timestamp"],bool):
   raise ValueError("invalid announcement ledger timestamp")
  digest=row["fingerprint"]
  if not isinstance(digest,str) or re.fullmatch(r"[0-9a-f]{64}",digest) is None or digest in hashes:
   raise ValueError("invalid or duplicate announcement fingerprint")
  hashes.add(digest)
 return seen

def render_new_line(e):
 return "- [ ] "+e["publishedAt"]+" — "+e["title"]+" ("+", ".join(e["sections"])+") — [Steam listing]("+e["url"]+")"

def merge_issue_body(existing_body,items,new_issue_body):
 """Preserve prior human checkboxes; add only unseen leads and a bounded ID/timestamp ledger.
 Returns (None, 0) when there is nothing new, so no API writes are performed.
 """
 seen=parse_seen(existing_body)
 recorded={row["fingerprint"] for row in seen}
 fresh=[];new_rows=[]
 for item in items:
  digest=lead_fingerprint(item)
  if digest in recorded:continue
  recorded.add(digest)
  fresh.append(item)
  new_rows.append({"gid":item["gid"],"timestamp":item["timestamp"],"fingerprint":digest})
 if not fresh:return None,0
 rows=(seen+new_rows)[-MAX_SEEN:]
 ledger=LEDGER_START+json.dumps({"schema":1,"seen":rows},separators=(",",":"),sort_keys=True)+LEDGER_END
 if existing_body:
  old_human=existing_body.split(LEDGER_START,1)[0].rstrip()
  body=old_human+"\n\n## Additional unverified leads\n\n"+"\n".join(map(render_new_line,fresh))
 else:body=new_issue_body.strip()
 result=body+"\n\n"+ledger+"\n"
 if len(result)>60000:
  raise ValueError("announcement issue reached maximum size; review/archive before continuing")
 return result,len(fresh)

def sync(items,body):
 if not items:
  print("No candidate announcements; no issue changes.")
  return
 repo=os.getenv("GITHUB_REPOSITORY")
 if not repo or not os.getenv("GH_TOKEN"):
  raise RuntimeError("Actions GitHub token unavailable")
 matches=[x for x in json.loads(gh("issue","list","--repo",repo,"--state","all","--limit","100","--json","number,title,state")) if x["title"]==ISSUE]
 if len(matches)>1:raise RuntimeError("Duplicate review issues; refusing ambiguous edit")
 existing=matches[0] if matches else None
 previous=""
 if existing:
  previous_data=json.loads(gh("issue","view",str(existing["number"]),"--repo",repo,"--json","body"))
  previous=previous_data["body"]
  if not isinstance(previous,str):raise ValueError("review issue body unavailable")
 updated,count=merge_issue_body(previous,items,body)
 if updated is None:
  print("All matching announcements already recorded; no issue writes.")
  return
 with NamedTemporaryFile("w",suffix=".md",encoding="utf-8",delete=False) as f:
  f.write(updated);path=f.name
 try:
  if existing:
   number=str(existing["number"])
   gh("issue","edit",number,"--repo",repo,"--body-file",path)
   if existing["state"]!="OPEN":
    gh("issue","reopen",number,"--repo",repo)
   print("Recorded "+str(count)+" new leads in review issue #"+number)
  else:
   url=gh("issue","create","--repo",repo,"--title",ISSUE,"--body-file",path)
   print("Opened review issue "+url+" with "+str(count)+" new leads")
 finally:Path(path).unlink(missing_ok=True)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 mode=p.add_mutually_exclusive_group(required=True)
 mode.add_argument("--probe",action="store_true")
 mode.add_argument("--apply",action="store_true")
 p.add_argument("--output",type=Path)
 p.add_argument("--input",type=Path)
 p.add_argument("--intel",type=Path,default=ROOT/"data/intel.json")
 a=p.parse_args()
 if a.probe:
  payload=fetch()
  raw=payload.get("appnews",{}).get("newsitems",[])
  print("Steam API raw items:",len(raw))
  for item in raw[:3]:
   print("Sample:",{"gid":str(item.get("gid"))[:40],"title":sanitize(item.get("title")),"urlhost":urlsplit(str(item.get("url",""))).hostname,"feed":str(item.get("feedname"))[:60]})
  records=normalize(payload)
  if not records:raise ValueError("No usable news items for this app; refusing to call this source working")
  print("Steam Web API OK: "+str(len(records))+" metadata records; "+str(sum(bool(GAME.search(x["title"])) for x in records))+" mention MW4.")
  for e in records[:4]:print(e["date"],e["title"])
  if a.output:a.output.write_text(json.dumps(records),encoding="utf-8")
  return
 if not a.input or not a.input.exists():raise ValueError("--apply requires saved --probe result from same workflow")
 saved=json.loads(a.input.read_text(encoding="utf-8"))
 if not isinstance(saved,list) or len(saved)>40:raise ValueError("invalid saved feed")
 # Validate untrusted temporary feed again before using it.
 entries=normalize({"appnews":{"appid":APPID,"newsitems":[{"gid":e["gid"],"title":e["title"],"url":e["url"],"date":e["timestamp"]} for e in saved]}})
 if any(datetime.fromtimestamp(e["timestamp"],timezone.utc).date().isoformat()!=e.get("date") for e in saved):
  raise ValueError("probe timestamp/date mismatch")
 stamps=json.loads(a.intel.read_text(encoding="utf-8"))["reviewedSections"]
 for k in TOPICS:
  if not isinstance(stamps.get(k),str) or not re.fullmatch(r"\d{4}-\d\d-\d\d",stamps[k]):raise ValueError("bad review date")
 items=leads(entries,stamps)
 body=report(items)
 print(str(len(items))+" unverified news leads requiring review.")
 if os.getenv("GITHUB_STEP_SUMMARY"):
  with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:f.write(body+"\n")
 sync(items,body)

if __name__=="__main__":
 try:main()
 except Exception as ex:
  print(type(ex).__name__+": "+str(ex),file=sys.stderr)
  sys.exit(1)

#!/usr/bin/env python3
"""Read-only Steam news leads for MW4 editorial review; never publishes game data."""
import argparse, html, json, os, re, subprocess, sys
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit

APPID=1938090
API="https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
ISSUE="[War Room] Steam news leads for review"
HOSTS={"store.steampowered.com","steamcommunity.com","callofduty.com","www.callofduty.com"}
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
  result.append({"gid":gid,"title":title,"url":url,"date":datetime.fromtimestamp(stamp,timezone.utc).date().isoformat()})
 return result

def leads(entries,reviewed):
 result=[]
 for e in entries:
  if not GAME.search(e["title"]):continue
  sections=[k for k,p in TOPICS.items() if p.search(e["title"]) and e["date"]>reviewed[k]]
  if sections:result.append({**e,"sections":sections})
 return sorted(result,key=lambda e:(e["date"],e["gid"]),reverse=True)

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
  lines.append("- [ ] "+e["date"]+" — "+e["title"]+" ("+", ".join(e["sections"])+") — [Steam listing]("+e["url"]+")")
 lines+=["","Only after a genuine source review, update the curated JSON and reviewed dates through a passing PR. Close this issue manually after completion.",""]
 return "\n".join(lines)

def sync(items,body):
 if not items:
  print("No new leads; no issue changes.")
  return
 repo=os.getenv("GITHUB_REPOSITORY")
 if not repo or not os.getenv("GH_TOKEN"):raise RuntimeError("Actions GitHub token unavailable")
 matches=[x for x in json.loads(gh("issue","list","--repo",repo,"--state","all","--limit","100","--json","number,title,state")) if x["title"]==ISSUE]
 if len(matches)>1:raise RuntimeError("Duplicate review issues; refusing ambiguous edit")
 with NamedTemporaryFile("w",suffix=".md",encoding="utf-8",delete=False) as f:
  f.write(body);path=f.name
 try:
  if matches:
   n=str(matches[0]["number"])
   gh("issue","edit",n,"--repo",repo,"--body-file",path)
   if matches[0]["state"]!="OPEN":gh("issue","reopen",n,"--repo",repo)
  else:gh("issue","create","--repo",repo,"--title",ISSUE,"--body-file",path)
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
  records=normalize(fetch())
  print("Steam Web API OK: "+str(len(records))+" metadata records; "+str(sum(bool(GAME.search(x["title"])) for x in records))+" mention MW4.")
  for e in records[:4]:print(e["date"],e["title"])
  if a.output:a.output.write_text(json.dumps(records),encoding="utf-8")
  return
 if not a.input or not a.input.exists():raise ValueError("--apply requires saved --probe result from same workflow")
 saved=json.loads(a.input.read_text(encoding="utf-8"))
 if not isinstance(saved,list) or len(saved)>40:raise ValueError("invalid saved feed")
 # Validate untrusted temporary feed again before using it.
 entries=normalize({"appnews":{"appid":APPID,"newsitems":[{"gid":e["gid"],"title":e["title"],"url":e["url"],"date":int(datetime.fromisoformat(e["date"]).replace(tzinfo=timezone.utc).timestamp())} for e in saved]}})
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

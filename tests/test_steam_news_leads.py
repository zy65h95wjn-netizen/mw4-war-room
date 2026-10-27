"""Offline verification of the Steam metadata lead filter."""
import sys,unittest
from datetime import date,datetime,timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import steam_news_leads as w
TS=int(datetime(2026,10,28,13,tzinfo=timezone.utc).timestamp())
REV={"patches":"2026-10-27","events":"2026-10-27","battlePass":"2026-10-27"}
def item(gid,title,url="https://store.steampowered.com/news/app/1938090/view/123",ts=TS):
 return {"gid":gid,"title":title,"url":url,"date":ts}
def feed(items,appid=1938090):return {"appnews":{"appid":appid,"newsitems":items}}
def norm(items):return w.normalize(feed(items),today=date(2026,10,28))

class SteamNewsTests(unittest.TestCase):
 def test_documented_shape(self):
  x=norm([item("1234567","MW4 Patch Notes")])
  self.assertEqual(len(x),1)
  self.assertEqual(x[0]["date"],"2026-10-28")
 def test_wrong_app_fails(self):
  with self.assertRaises(ValueError):w.normalize(feed([],440))
 def test_bad_payload_fails(self):
  with self.assertRaises(ValueError):w.normalize({"nope":[]})
 def test_cross_title_noise_ignored(self):
  x=norm([item("1234567","Black Ops 7 patch notes"),item("1234568","MW4 Campaign Trailer")])
  self.assertEqual(w.leads(x,REV),[])
 def test_reviewed_day_included_with_precise_timestamp(self):
  exact=int(datetime(2026,10,27,20,45,tzinfo=timezone.utc).timestamp())
  entries=norm([item("1234567","MW4 Patch Notes",ts=exact)])
  self.assertEqual(entries[0]["timestamp"],exact)
  self.assertEqual(entries[0]["publishedAt"],"2026-10-27 20:45 UTC")
  self.assertEqual(len(w.leads(entries,REV)),1)
 def test_patch_and_pass(self):
  x=w.leads(norm([item("1234567","Modern Warfare 4 Patch Notes"),item("1234568","MW4 Season 1 Battle Pass")]),REV)
  self.assertEqual(len(x),2)
  self.assertIn("patches",next(e for e in x if "Patch" in e["title"])["sections"])
  self.assertIn("battlePass",next(e for e in x if "Season" in e["title"])["sections"])
 def test_allow_steam_news_cdn(self):
  x=norm([item("1234567","MW4 Patch Notes",url="https://steamstore-a.akamaihd.net/news/app/1938090/view/123")])
  self.assertEqual(len(x),1)
 def test_disallow_external_url(self):
  self.assertEqual(norm([item("1234567","MW4 Patch Notes",url="https://bad.invalid/path")]),[])
 def test_disallow_insecure_url(self):
  self.assertEqual(norm([item("1234567","MW4 Patch Notes",url="http://store.steampowered.com/news")]),[])
 def test_sanitize_title(self):
  x=norm([item("1234567","MW4 Patch Notes @all <script> [link]")])
  self.assertNotIn("@",x[0]["title"])
  self.assertNotIn("[",x[0]["title"])
  self.assertNotIn("<",x[0]["title"])
 def test_invalid_timestamp(self):
  self.assertEqual(norm([item("1234567","MW4 patch",ts=-1)]),[])
 def test_duplicate_ids(self):
  self.assertEqual(len(norm([item("1234567","MW4 Patch"),item("1234567","MW4 Update")])),1)
 def test_no_changes_no_issue_writes(self):
  with patch.object(w,"gh",side_effect=AssertionError("unexpected write")):
   w.sync([],"No news")
 def test_user_review_required(self):
  text=w.report([{"date":"2026-10-28","publishedAt":"2026-10-28 13:00 UTC","title":"MW4 patch notes","url":"https://store.steampowered.com/news/x","sections":["patches"]}])
  self.assertIn("unverified",text.lower())
  self.assertIn("No announcement is published",text)
 def test_updates_single_existing_issue_without_creating_second(self):
  import json
  entries=w.leads(norm([item("1234567","MW4 Patch Notes")]),REV)
  initial_body=w.report(entries)
  existing='{"body":"Previously reviewed human checklist"}'
  def stub(*a):
   if a[:2]==("issue","list"):return json.dumps([{"number":42,"title":w.ISSUE,"state":"OPEN"}])
   if a[:2]==("issue","view"):return existing
   return "ok"
  with patch.dict(w.os.environ,{"GITHUB_REPOSITORY":"owner/repo","GH_TOKEN":"placeholder"}):
   with patch.object(w,"gh",side_effect=stub) as fake:
    w.sync(entries,initial_body)
    names=[x.args[:2] for x in fake.call_args_list]
    self.assertIn(("issue","view"),names)
    self.assertIn(("issue","edit"),names)
    self.assertNotIn(("issue","create"),names)
    self.assertNotIn(("issue","close"),names)
 def test_duplicate_existing_issues_fail_closed(self):
  with patch.dict(w.os.environ,{"GITHUB_REPOSITORY":"owner/repo","GH_TOKEN":"placeholder"}):
   duplicate=[{"number":1,"title":w.ISSUE,"state":"OPEN"},{"number":2,"title":w.ISSUE,"state":"OPEN"}]
   with patch.object(w,"gh",return_value=__import__("json").dumps(duplicate)):
    with self.assertRaises(RuntimeError):w.sync([{"date":"2026-10-28"}],"no ambiguity")

 def test_precise_utc_timestamp_survives_normalize(self):
  first=norm([item("1234567","MW4 patch notes",ts=TS)])[0]
  self.assertEqual(first["timestamp"],TS)
  self.assertEqual(first["publishedAt"],"2026-10-28 13:00 UTC")
  self.assertEqual(first["date"],"2026-10-28")

 def test_distinct_same_day_announcements_both_detected(self):
  stamps=[int(datetime(2026,10,27,h,tzinfo=timezone.utc).timestamp()) for h in (11,22)]
  entries=norm([item("1234567","MW4 Patch Notes",ts=stamps[0]),item("1234568","MW4 Patch Notes",ts=stamps[1])])
  found=w.leads(entries,REV)
  self.assertEqual(len(found),2)
  self.assertGreater(found[0]["timestamp"],found[1]["timestamp"])

 def test_persistent_seen_ids_deduplicate_repeated_runs(self):
  one=w.leads(norm([item("1234567","MW4 Patch Notes")]),REV)
  initial=w.report(one)
  body,count=w.merge_issue_body("",one,initial)
  self.assertEqual(count,1)
  self.assertIn(w.LEDGER_START,body)
  self.assertEqual(w.parse_seen(body)[0]["gid"],"1234567")
  self.assertEqual(w.parse_seen(body)[0]["timestamp"],TS)
  updated,n=w.merge_issue_body(body,one,w.report(one))
  self.assertIsNone(updated)
  self.assertEqual(n,0)

 def test_same_day_new_gid_preserves_checked_old_item(self):
  old=w.leads(norm([item("1234567","MW4 Patch Notes")]),REV)
  old_body,_=w.merge_issue_body("",old,w.report(old))
  old_body=old_body.replace("- [ ] ","- [x] ",1)
  later=w.leads(norm([item("1234568","MW4 Season 1 Battle Pass",ts=TS+120)]),REV)
  merged,count=w.merge_issue_body(old_body,old+later,w.report(old+later))
  self.assertEqual(count,1)
  self.assertEqual(len(w.parse_seen(merged)),2)
  self.assertIn("- [x] ",merged)
  self.assertEqual(merged.count(w.LEDGER_START),1)
  self.assertIn("Additional unverified leads",merged)

 def test_headline_revised_with_same_gid_is_new_fingerprint(self):
  old=w.leads(norm([item("1234567","MW4 Patch Notes")]),REV)
  first,_=w.merge_issue_body("",old,w.report(old))
  changed=w.leads(norm([item("1234567","MW4 Patch Notes - Hotfix")]),REV)
  second,count=w.merge_issue_body(first,changed,w.report(changed))
  self.assertEqual(count,1)
  self.assertEqual(len(w.parse_seen(second)),2)

 def test_ledger_corruption_fails_closed(self):
  old=w.leads(norm([item("1234567","MW4 Patch Notes")]),REV)
  body,_=w.merge_issue_body("",old,w.report(old))
  for bad in (body.replace("war-room-steam-seen-v1","war-room-steam-seen-v2"),
              body.replace('"schema":1','"schema":9'),
              body.replace(w.LEDGER_END,"")):
   with self.subTest(body=bad[-80:]):
    with self.assertRaises(ValueError):w.merge_issue_body(bad,old,w.report(old))

 def test_existing_issue_same_payload_is_read_only(self):
  import json
  entries=w.leads(norm([item("1234567","MW4 Patch Notes")]),REV)
  body,_=w.merge_issue_body("",entries,w.report(entries))
  def stub(*a):
   if a[:2]==("issue","list"):return json.dumps([{"number":42,"title":w.ISSUE,"state":"OPEN"}])
   if a[:2]==("issue","view"):return json.dumps({"body":body})
   raise AssertionError("unexpected write "+str(a))
  with patch.dict(w.os.environ,{"GITHUB_REPOSITORY":"owner/repo","GH_TOKEN":"placeholder"}):
   with patch.object(w,"gh",side_effect=stub) as fake:
    w.sync(entries,w.report(entries))
    self.assertEqual(len(fake.call_args_list),2)

 def test_closed_issue_reopens_only_for_new_candidate(self):
  import json
  old=w.leads(norm([item("1234567","MW4 Patch Notes")]),REV)
  old_body,_=w.merge_issue_body("",old,w.report(old))
  newer=w.leads(norm([item("1234568","MW4 Season 1 Battle Pass",ts=TS+10)]),REV)
  def stub(*a):
   if a[:2]==("issue","list"):return json.dumps([{"number":42,"title":w.ISSUE,"state":"CLOSED"}])
   if a[:2]==("issue","view"):return json.dumps({"body":old_body})
   return "ok"
  with patch.dict(w.os.environ,{"GITHUB_REPOSITORY":"owner/repo","GH_TOKEN":"placeholder"}):
   with patch.object(w,"gh",side_effect=stub) as fake:
    w.sync(newer,w.report(newer))
    calls=[x.args[:2] for x in fake.call_args_list]
    self.assertIn(("issue","edit"),calls)
    self.assertIn(("issue","reopen"),calls)
    self.assertNotIn(("issue","create"),calls)

 def test_missing_candidate_fields_fail_closed(self):
  with self.assertRaises(ValueError):
   w.merge_issue_body("",[{"date":"2026-10-28"}],"No evidence")

 def test_changed_sections_are_new_candidate_fingerprint(self):
  source=w.leads(norm([item("1234567","MW4 Season 1 Patch Notes")]),REV)[0]
  body,_=w.merge_issue_body("",[source],w.report([source]))
  narrow={**source,"sections":["patches"]}
  _,count=w.merge_issue_body(body,[narrow],w.report([narrow]))
  self.assertEqual(count,1)

 def test_probe_apply_roundtrip_preserves_full_publication_timestamp(self):
  import json,sys,tempfile
  from tempfile import TemporaryDirectory
  stamp=int(datetime(2026,10,27,20,43,tzinfo=timezone.utc).timestamp())
  with TemporaryDirectory() as temp:
   saved_path=Path(temp)/"news.json"
   sample=feed([item("1234567","MW4 Patch Notes",ts=stamp)])
   with patch.object(w,"fetch",return_value=sample):
    with patch.object(sys,"argv",["steam_news_leads.py","--probe","--output",str(saved_path)]):
     w.main()
   saved=json.loads(saved_path.read_text())
   self.assertEqual(saved[0]["timestamp"],stamp)
   self.assertEqual(saved[0]["publishedAt"],"2026-10-27 20:43 UTC")
   observed=[]
   with patch.object(w,"sync",side_effect=lambda items,body:observed.extend(items)):
    with patch.object(sys,"argv",["steam_news_leads.py","--apply","--input",str(saved_path)]):
     w.main()
   self.assertEqual(observed[0]["timestamp"],stamp)
   self.assertEqual(observed[0]["date"],"2026-10-27")

if __name__=="__main__":unittest.main()

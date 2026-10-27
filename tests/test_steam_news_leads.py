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
 def test_reviewed_day_excluded(self):
  old=int(datetime(2026,10,27,tzinfo=timezone.utc).timestamp())
  self.assertEqual(w.leads(norm([item("1234567","MW4 Patch Notes",ts=old)]),REV),[])
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
  text=w.report([{"date":"2026-10-28","title":"MW4 patch notes","url":"https://store.steampowered.com/news/x","sections":["patches"]}])
  self.assertIn("unverified",text.lower())
  self.assertIn("No announcement is published",text)
 def test_updates_single_existing_issue_without_creating_second(self):
  from unittest.mock import call
  with patch.dict(w.os.environ,{"GITHUB_REPOSITORY":"owner/repo","GH_TOKEN":"placeholder"}):
   with patch.object(w,"gh",side_effect=lambda *a: '[{"number":42,"title":"'+w.ISSUE+'","state":"OPEN"}]' if a[:2]==("issue","list") else "ok") as fake:
    w.sync([{"date":"2026-10-28"}],"Review these leads")
    names=[x.args[:2] for x in fake.call_args_list]
    self.assertIn(("issue","edit"),names)
    self.assertNotIn(("issue","create"),names)
    self.assertNotIn(("issue","close"),names)
 def test_duplicate_existing_issues_fail_closed(self):
  with patch.dict(w.os.environ,{"GITHUB_REPOSITORY":"owner/repo","GH_TOKEN":"placeholder"}):
   duplicate=[{"number":1,"title":w.ISSUE,"state":"OPEN"},{"number":2,"title":w.ISSUE,"state":"OPEN"}]
   with patch.object(w,"gh",return_value=__import__("json").dumps(duplicate)):
    with self.assertRaises(RuntimeError):w.sync([{"date":"2026-10-28"}],"no ambiguity")
if __name__=="__main__":unittest.main()

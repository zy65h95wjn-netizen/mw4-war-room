import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_intel import IntelInvalid, validate, SECTION_KEYS
from review_watch import due_items, markdown


class IntelValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT / 'data/intel.json').read_text(encoding='utf-8'))

    def setUp(self):
        self.data = copy.deepcopy(self.original)

    def test_original_passes(self):
        validate(self.data, today=date(2026, 10, 27))

    def assert_invalid(self, needle=None):
        with self.assertRaises(IntelInvalid) as ctx:
            validate(self.data, today=date(2026, 10, 27))
        if needle:
            self.assertIn(needle, str(ctx.exception))

    def test_reject_new_schema(self):
        self.data['schema'] = 3
        self.assert_invalid('schema')

    def test_reject_wrong_mode(self):
        self.data['coverage'] = 'Modern Warfare 4 Warzone'
        self.assert_invalid('Multiplayer')

    def test_reject_future_review(self):
        self.data['reviewed'] = '2026-11-02'
        self.assert_invalid('future')

    def test_reject_bad_date(self):
        self.data['reviewed'] = '2026-02-30'
        self.assert_invalid('impossible')

    def test_reject_section_future_review(self):
        self.data['reviewedSections']['meta'] = '2026-10-29'
        self.assert_invalid('future')

    def test_reject_missing_review_section(self):
        del self.data['reviewedSections']['battlePass']
        self.assert_invalid('exact section keys')

    def test_reject_fudged_review_interval(self):
        self.data['reviewLimitsDays']['events'] = 365
        self.assert_invalid('expected 2')

    def test_reject_fake_official_url(self):
        self.data['sources'][0]['url'] = 'https://untrusted.example.com/patch'
        self.assert_invalid('Activision-controlled')

    def test_reject_http_url(self):
        self.data['sources'][4]['url'] = 'http://example.com'
        self.assert_invalid('HTTPS')

    def test_reject_dangling_build_source(self):
        self.data['builds'][0]['source'] = 'made-up'
        self.assert_invalid('unknown source')

    def test_reject_dangling_patch_source(self):
        self.data['patches'][0]['source'] = 'made-up'
        self.assert_invalid('unknown source')

    def test_reject_duplicate_meta_weapon(self):
        self.data['meta'][0]['entries'][1]['weapon'] = self.data['meta'][0]['entries'][0]['weapon']
        self.assert_invalid('repeated weapon')

    def test_reject_duplicate_category_rank(self):
        self.data['meta'][1]['entries'][1]['rank'] = 1
        self.assert_invalid('repeated rank')

    def test_reject_meta_not_two_sources(self):
        self.data['meta'] = self.data['meta'][:1]
        self.assert_invalid('publisher split')

    def test_reject_optic_flag_conflict(self):
        self.data['builds'][0]['optic'] = True
        self.assert_invalid('optic flag')

    def test_reject_duplicate_attachment_slot(self):
        self.data['builds'][0]['parts'][1][0] = 'Muzzle'
        self.assert_invalid('duplicate slot')

    def test_reject_6_standard_parts(self):
        self.data['builds'][0]['parts'].append(['Barrel', 'Fictional barrel'])
        self.assert_invalid('attachment count')

    def test_reject_inconsistent_weapon_category_in_builds(self):
        self.data['builds'][0]['category'] = 'SMG'
        self.assert_invalid('build category contradicts ranking')

    def test_reject_unverified_official_event_source(self):
        self.data['events'][0]['scheduleConfidence'] = 'official'
        self.assert_invalid('official schedule evidence')

    def test_reject_event_missing_schedule_evidence(self):
        self.data['events'][0].pop('scheduleConfidence')
        self.assert_invalid('explicit schedule evidence')

    def test_reject_unsorted_patches(self):
        self.data['patches'][0], self.data['patches'][1] = self.data['patches'][1], self.data['patches'][0]
        self.assert_invalid('newest')

    def test_reject_event_end_before_start(self):
        self.data['events'][0]['ends'] = '2026-10-22'
        self.assert_invalid('end precedes')

    def test_reject_fake_battlepass_source(self):
        self.data['battlePass']['verifiedSource'] = '???'
        self.assert_invalid('unknown source')

    def test_reject_missing_sections(self):
        for k in SECTION_KEYS:
            self.assertIn(k, self.data['reviewedSections'])


class ReviewWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'data/intel.json').read_text(encoding='utf-8'))

    def test_no_due_on_original_review_day(self):
        self.assertFalse(due_items(self.data, date(2026, 10, 27)))

    def test_anticipated_event_date_review(self):
        labels = [x['label'] for x in due_items(self.data, date(2026, 10, 29))]
        self.assertTrue(any('Possession' in label for label in labels))
        self.assertTrue(any('Infected' in label for label in labels))

    def test_stale_sections_do_not_reset_themselves(self):
        items = due_items(self.data, date(2026, 11, 2))
        self.assertTrue(any(i['section'] == 'meta' and i['kind'] == 'stale' for i in items))
        self.assertTrue(any(i['section'] == 'patches' and i['kind'] == 'stale' for i in items))

    def test_battlepass_rollout_flag(self):
        labels = [x['label'] for x in due_items(self.data, date(2026, 11, 4))]
        self.assertTrue(any('Season 1' in label for label in labels))

    def test_reviews_can_clear_a_stale_issue(self):
        updated = copy.deepcopy(self.data)
        updated['reviewed'] = '2026-11-08'
        updated['reviewedSections'] = dict.fromkeys(SECTION_KEYS, '2026-11-08')
        self.assertFalse(due_items(updated, date(2026, 11, 8)))
        validate(updated, today=date(2026, 11, 8))

    def test_review_report_does_not_claim_live_fetch(self):
        content = markdown(self.data, due_items(self.data, date(2026, 10, 30)))
        self.assertIn('does not poll, scrape', content)
        self.assertIn('review', content)
        self.assertIn('https://www.callofduty.com/patchnotes', content)


if __name__ == '__main__':
    unittest.main()

class GitHubReviewIssueTests(unittest.TestCase):
    """The scheduled job must reuse an issue, never create one each day."""
    def test_create_only_when_due(self):
        from unittest.mock import patch
        from sync_review_issue import sync
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'report.md'
            path.write_text('Editorial summary')
            calls = []
            def fake_gh(*args):
                calls.append(args)
                return '[]' if args[:2] == ('issue','list') else 'https://github.com/test/repo/issues/1'
            with patch('sync_review_issue.gh',fake_gh):
                sync('test/repo',True,path)
            self.assertTrue(any(c[:2] == ('issue','create') for c in calls))
            self.assertEqual(sum(c[:2] == ('issue','create') for c in calls),1)

    def test_reuse_existing_review_issue(self):
        from unittest.mock import patch
        from sync_review_issue import sync
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'report.md';path.write_text('Review today')
            calls=[]
            def fake_gh(*args):
                calls.append(args)
                if args[:2] == ('issue','list'):
                    return json.dumps([{'number':7,'title':'[War Room] Curated intelligence review due','state':'OPEN'}])
                return ''
            with patch('sync_review_issue.gh',fake_gh):
                sync('test/repo',True,path)
            self.assertEqual(sum(c[:2] == ('issue','edit') for c in calls),1)
            self.assertFalse(any(c[:2] == ('issue','create') for c in calls))

    def test_close_issue_once_reviewed(self):
        from unittest.mock import patch
        from sync_review_issue import sync
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'report.md';path.write_text('No pending reviews')
            calls=[]
            def fake_gh(*args):
                calls.append(args)
                if args[:2] == ('issue','list'):
                    return json.dumps([{'number':7,'title':'[War Room] Curated intelligence review due','state':'OPEN'}])
                return ''
            with patch('sync_review_issue.gh',fake_gh):
                sync('test/repo',False,path)
            self.assertEqual(sum(c[:2] == ('issue','close') for c in calls),1)

    def test_refuse_multiple_review_issues(self):
        from unittest.mock import patch
        from sync_review_issue import sync
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'report.md';path.write_text('Pending')
            def fake_gh(*args):
                return json.dumps([{'number':7,'title':'[War Room] Curated intelligence review due','state':'OPEN'},{'number':8,'title':'[War Room] Curated intelligence review due','state':'OPEN'}])
            with patch('sync_review_issue.gh',fake_gh):
                with self.assertRaises(RuntimeError):sync('test/repo',True,path)
"""Catch-up archive resolver regression tests, never using real provider secrets."""
import base64
import datetime as dt
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "companion"))
import catchup


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        catchup._CACHE.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "test.db"
        with sqlite3.connect(self.db) as conn:
            conn.executescript("""
                CREATE TABLE playlists (id TEXT, serverUrl TEXT, username TEXT,
                   password TEXT, userAgent TEXT, payload TEXT);
                CREATE TABLE categories (id INTEGER, playlist_id TEXT);
                CREATE TABLE content (id INTEGER, title TEXT, type TEXT,
                   xtream_id INTEGER, category_id INTEGER, epg_channel_id TEXT);
                CREATE TABLE epg_channels (id TEXT, display_name TEXT);
                CREATE TABLE epg_programs (channel_id TEXT, title TEXT,
                   start TEXT, stop TEXT);
                INSERT INTO playlists VALUES ('test-playlist','https://example.invalid',
                    'USER','SECRET',NULL,'{"serverTimezone":"UTC+00:00"}');
                INSERT INTO categories VALUES (2,'test-playlist');
                INSERT INTO content VALUES (1,'US: MeTV Toons','live',11590,2,'METV');
                INSERT INTO epg_channels VALUES ('METV','US: MeTV Toons');
            """)

    def test_xmltv_selected_earlier_program(self):
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT INTO epg_programs VALUES (?,?,?,?)", (
                'METV', 'Wait Till Your Father Gets Home',
                '2026-11-03T05:00:00Z', '2026-11-03T05:30:00Z'))
        with patch.object(catchup, "_provider_rows", side_effect=AssertionError):
            result = catchup.resolve_archive(
                self.db, 11590, "US: MeTV Toons", "2026-11-03:05-00")
        self.assertEqual(result[1], "catchup-sqlite")
        self.assertEqual(result[0]["epgTitle"], "Wait Till Your Father Gets Home")

    def test_provider_fallback_base64_and_cache(self):
        payload=[{"start":"2026-11-03 05:00:00",
                  "title":base64.b64encode(
                      b'Wait Till Your Father Gets Home').decode(),
                  "start_timestamp":"1793682000",
                  "stop_timestamp":"1793683800"}]
        with patch.object(catchup, "_provider_rows", return_value=payload) as request:
            one=catchup.resolve_archive(
                self.db,11590,"US: MeTV Toons","2026-11-03:05-00")
            two=catchup.resolve_archive(
                self.db,11590,"US: MeTV Toons","2026-11-03:05-00")
        self.assertEqual(one[1],"catchup-provider")
        self.assertEqual(one[0]["epgTitle"],"Wait Till Your Father Gets Home")
        self.assertEqual(one,two)
        self.assertEqual(request.call_count,1)
        self.assertNotIn("SECRET",str(one))

    def test_catchup_provider_wall_clock_supplies_broadcast_times(self):
        # Real provider panels frequently omit Unix timestamps entirely.
        # Programme title already resolved in RC3, but previously clocks = "".
        rows = [{'start': '2026-11-03 05:00:00',
                 'stop': '2026-11-03 05:30:00',
                 'title': 'Wait Till Your Father Gets Home'}]
        with patch.object(catchup, '_provider_rows', return_value=rows):
            got = catchup.resolve_archive(
                self.db, 11590, 'US: MeTV Toons', '2026-11-03:05-00')
        self.assertEqual(got[1], 'catchup-provider')
        self.assertEqual(got[0]['epgTitle'], 'Wait Till Your Father Gets Home')
        self.assertEqual(got[0]['epgStart'], '2026-11-03T05:00:00Z')
        self.assertEqual(got[0]['epgEnd'], '2026-11-03T05:30:00Z')
        catchup._CACHE.clear()

    def test_catchup_provider_wall_clock_converts_known_server_timezone(self):
        # A UTC+7 panel's 12:00 broadcast is 05:00Z, and must display
        # as 12:00 in IINA on a UTC+7 Mac.
        with sqlite3.connect(self.db) as db:
            db.execute('UPDATE playlists SET payload=?',
                       ('{"serverTimezone":"Asia/Ho_Chi_Minh"}',))
        with patch.object(catchup, '_provider_rows', return_value=[{
                'start': '2026-11-03 12:00:00',
                'end': '2026-11-03 12:30:00',
                'title': 'Wait Till Your Father Gets Home'}]):
            got = catchup.resolve_archive(
                self.db, 11590, 'US: MeTV Toons', '2026-11-03:12-00')
        self.assertEqual(got[0]['epgStart'], '2026-11-03T05:00:00Z')
        self.assertEqual(got[0]['epgEnd'], '2026-11-03T05:30:00Z')
        catchup._CACHE.clear()

    def test_catchup_provider_missing_end_does_not_invent_broadcast_time(self):
        with patch.object(catchup, '_provider_rows', return_value=[{
                'start': '2026-11-03 05:00:00',
                'title': 'Wait Till Your Father Gets Home'}]):
            got = catchup.resolve_archive(
                self.db, 11590, 'US: MeTV Toons', '2026-11-03:05-00')
        self.assertEqual(got[0]['epgTitle'], 'Wait Till Your Father Gets Home')
        self.assertEqual(got[0]['epgStart'], '')
        self.assertEqual(got[0]['epgEnd'], '')
        catchup._CACHE.clear()

    def test_ambiguous_provider_and_invalid_clock_fail_closed(self):
        self.assertIsNone(catchup.resolve_archive(
            self.db,11590,"US: MeTV Toons","nonsense"))
        with sqlite3.connect(self.db) as db:
            db.executescript("""
                INSERT INTO playlists VALUES ('other','https://else.invalid',
                    'u','p',NULL,'{}');
                INSERT INTO categories VALUES (3,'other');
                INSERT INTO content VALUES (2,'US: MeTV Toons','live',11590,3,'METV');
            """)
        with patch.object(catchup, "_provider_rows", side_effect=AssertionError):
            self.assertIsNone(catchup.resolve_archive(
                self.db,11590,"US: MeTV Toons","2026-11-03:05-00"))

    def test_live_schedule_rolls_over_without_new_ip_tvnator_remote(self):
        catchup._LIVE_CACHE.clear()
        # Two programme windows delivered once by the provider; select each
        # by the actual wall clock without requiring a UI click.
        items = [
            {'start': '2026-11-03 05:00:00', 'stop': '2026-11-03 05:30:00',
             'title': 'First Show'},
            {'start': '2026-11-03 05:30:00', 'stop': '2026-11-03 06:00:00',
             'title': 'Second Show'}
        ]
        with patch.object(catchup, '_provider_rows', return_value=items) as fetch:
            one = catchup.resolve_live(
                self.db, 11590, 'US: MeTV Toons',
                dt.datetime(2026, 11, 3, 5, 29, tzinfo=dt.timezone.utc))
            two = catchup.resolve_live(
                self.db, 11590, 'US: MeTV Toons',
                dt.datetime(2026, 11, 3, 5, 30, tzinfo=dt.timezone.utc))
        self.assertEqual(one[0]['epgTitle'], 'First Show')
        self.assertEqual(two[0]['epgTitle'], 'Second Show')
        self.assertEqual(fetch.call_count, 1)
        catchup._LIVE_CACHE.clear()

    def test_live_provider_cache_refreshes_when_last_show_expires(self):
        catchup._LIVE_CACHE.clear()
        first = [{'start': '2026-11-03 05:00:00',
                  'stop': '2026-11-03 05:30:00', 'title': 'First Show'}]
        second = [{'start': '2026-11-03 05:30:00',
                   'stop': '2026-11-03 06:00:00', 'title': 'Second Show'}]
        with patch.object(catchup, '_provider_rows', side_effect=[first, second]) as fetch:
            with patch.object(catchup.time, 'monotonic', return_value=1000):
                one = catchup.resolve_live(
                    self.db, 11590, 'US: MeTV Toons',
                    dt.datetime(2026, 11, 3, 5, 29, tzinfo=dt.timezone.utc))
            with patch.object(catchup.time, 'monotonic', return_value=1041):
                two = catchup.resolve_live(
                    self.db, 11590, 'US: MeTV Toons',
                    dt.datetime(2026, 11, 3, 5, 30, tzinfo=dt.timezone.utc))
        self.assertEqual(one[0]['epgTitle'], 'First Show')
        self.assertEqual(two[0]['epgTitle'], 'Second Show')
        self.assertEqual(fetch.call_count, 2)
        catchup._LIVE_CACHE.clear()

    def test_live_provider_schedule_rejects_ambiguous_clock_without_zone(self):
        catchup._LIVE_CACHE.clear()
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE playlists SET payload='{}'")
        with patch.object(catchup, '_provider_rows',
                          return_value=[{'start':'2026-11-03 05:00:00',
                                         'stop':'2026-11-03 05:30:00',
                                         'title':'Ambiguous Show'}]):
            found=catchup.resolve_live(
                self.db, 11590, 'US: MeTV Toons',
                dt.datetime(2026, 11, 3, 5, 15, tzinfo=dt.timezone.utc))
        self.assertIsNone(found)
        catchup._LIVE_CACHE.clear()

    def test_panel_wall_clock_without_timezone(self):
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE playlists SET payload='{}'")
        with patch.object(catchup,"_provider_rows",
                          return_value=[{"start":"2026-11-03 05:00:00",
                                         "title":"Archived Show"}]):
            result=catchup.resolve_archive(
                self.db,11590,"US: MeTV Toons","2026-11-03:05-00")
        self.assertEqual(result[0]["epgTitle"],"Archived Show")
        self.assertEqual(result[0]["epgStart"],"")


if __name__=="__main__":
    unittest.main()

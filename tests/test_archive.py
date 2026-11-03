"""Catch-up archive resolver regression tests, never using real provider secrets."""
import base64
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

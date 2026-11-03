"""Unit tests: no actual Xtream requests or credential logs."""
from __future__ import annotations
import importlib.util
import json
import sqlite3
import sys
import struct
import zlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "companion"))
from unittest.mock import patch
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location("server", Path(__file__).resolve().parents[1] / "companion/server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class CompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "iptvnator.db"
        with sqlite3.connect(self.db_path) as db:
            db.executescript("""
                CREATE TABLE content (id INTEGER PRIMARY KEY, title TEXT,
                                      poster_url TEXT, type TEXT, xtream_id INTEGER);
                INSERT INTO content VALUES (1, 'US: A&E East', 'https://images.example.org/channel.png', 'live', 120);
                INSERT INTO content VALUES (2, 'Some Movie', 'https://images.example.org/film.png', 'movie', 120);
                INSERT INTO content VALUES (3, 'US: A&E East', '', 'live', 121);
                ALTER TABLE content ADD COLUMN epg_channel_id TEXT;
                UPDATE content SET epg_channel_id='AE.us' WHERE id=1;
                CREATE TABLE epg_channels (id TEXT, display_name TEXT);
                INSERT INTO epg_channels VALUES ('AE.us', 'US: A&E East');
                CREATE TABLE epg_programs (channel_id TEXT, title TEXT, start TEXT, stop TEXT);
                INSERT INTO epg_programs VALUES ('AE.us', 'Local Show', '2020-01-01T00:00:00Z', '2100-01-01T00:00:00Z');
            """)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.CompanionHandler)
        self.httpd.database_path = self.db_path
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def url(self, suffix):
        return f'http://127.0.0.1:{self.httpd.server_port}{suffix}'

    def test_lookup_exact_stream_name(self):
        self.assertEqual(server.lookup_channel(self.db_path, 120, 'us: a&e east')['title'], 'US: A&E East')
        self.assertIsNone(server.lookup_channel(self.db_path, 120, 'US: Cartoon Network'))
        self.assertIsNone(server.lookup_channel(self.db_path, 122, 'US: A&E East'))

    def test_status_does_not_return_logo_credentials(self):
        status = {'portal':'xtream','isLiveView':True,'channelName':'US: A&E East',
                  'epgTitle':'Storage Wars','epgStart':'2026-11-02T15:30:00Z','epgEnd':'2026-11-02T16:00:00Z'}
        with patch.object(server,'remote_status',return_value=status):
            body = urllib.request.urlopen(self.url('/status?stream_id=120')).read().decode()
            value = json.loads(body)
            self.assertEqual(value['epgTitle'],'Storage Wars')
            self.assertTrue(value['matched'])
            self.assertTrue(value['hasLogo'])
            self.assertNotIn('images.example.org',body)
            self.assertNotIn('username',body)
            bad = json.load(urllib.request.urlopen(self.url('/status?stream_id=122')))
            self.assertFalse(bad['matched'])

    def test_status_disabled_on_vod(self):
        with patch.object(server,'remote_status',return_value={'portal':'xtream','isLiveView':False,'channelName':'US: A&E East'}):
            out = json.load(urllib.request.urlopen(self.url('/status?stream_id=120')))
            self.assertFalse(out['matched'])

    def test_launch_title_hint_survives_remote_channel_switch(self):
        with patch.object(server, 'remote_status', return_value={
            'portal': 'xtream', 'isLiveView': True, 'channelName': 'US: Another Channel'
        }):
            body = json.load(urllib.request.urlopen(self.url(
                '/status?stream_id=120&title_hint=US%3A%20A%26E%20East%20%C2%B7%20Storage%20Wars')))
            self.assertTrue(body['matched'])
            self.assertEqual(body['source'], 'sqlite')
            self.assertEqual(body['epgTitle'], 'Local Show')
            self.assertTrue(body['hasLogo'])
            # Fail closed for an unrelated title with same numeric Xtream ID.
            body = json.load(urllib.request.urlopen(self.url(
                '/status?stream_id=120&title_hint=US%3A%20Cartoon%20Network')))
            self.assertFalse(body['matched'])

    def test_catchup_title_matching(self):
        self.assertEqual(server.catchup_program_title('US: A&E East', 'US: A&E East - Storage Wars'), 'Storage Wars')
        self.assertEqual(server.catchup_program_title('US: A&E East', 'US: A&E East'), '')
        self.assertEqual(server.lookup_channel(self.db_path, 120, title_hint='US: A&E East - Storage Wars')['title'], 'US: A&E East')

    def test_catchup_never_uses_live_epg(self):
        remote={'portal':'xtream','isLiveView':True,'channelName':'US: A&E East',
                'epgTitle':'WRONG LIVE PROGRAM'}
        with patch.object(server,'remote_status',return_value=remote):
            url=self.url('/status?stream_id=120&playback=catchup&title_hint=US%3A%20A%26E%20East%20-%20Storage%20Wars')
            info=json.load(urllib.request.urlopen(url))
            self.assertTrue(info['matched'])
            self.assertEqual(info['mode'],'catchup')
            self.assertEqual(info['source'],'catchup-title')
            self.assertEqual(info['epgTitle'],'Storage Wars')
            self.assertTrue(info['hasLogo'])

    def test_catchup_survives_nonlive_remote(self):
        with patch.object(server,'remote_status',return_value={'portal':'xtream','isLiveView':False}):
            info=json.load(urllib.request.urlopen(self.url(
                '/status?stream_id=120&playback=catchup&title_hint=US%3A%20A%26E%20East%20-%20Storage%20Wars')))
            self.assertTrue(info['matched'])
            self.assertEqual(info['epgTitle'],'Storage Wars')

    def test_invalid_mode_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(self.url('/status?stream_id=120&playback=movie'))
        self.assertEqual(err.exception.code,400)

    def test_black_background_rgba_png(self):
        from logo import flatten_png_black
        def chunk(kind, data):
            import binascii
            return (struct.pack('>I', len(data)) + kind + data +
                    struct.pack('>I', binascii.crc32(kind+data) & 0xffffffff))
        raw = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, 6, 0, 0, 0)) +
               chunk(b'IDAT', zlib.compress(b'\x00' + bytes([255,255,255,0,255,255,255,255]))) +
               chunk(b'IEND', b''))
        out = flatten_png_black(raw)
        self.assertEqual(out[25], 2)  # PNG type 2 = opaque RGB
        payload = out[41:]
        # Parse and decompress output first IDAT chunk.
        data_len = struct.unpack('>I', out[33:37])[0]
        pixel = zlib.decompress(out[41:41+data_len])
        self.assertEqual(pixel[1:4], b'\x00\x00\x00')
        self.assertEqual(pixel[4:7], b'\xff\xff\xff')

    def test_private_logos_blocked(self):
        self.assertFalse(server.public_image_url('http://127.0.0.1:8765/secret'))
        self.assertFalse(server.public_image_url('file:///etc/passwd'))
        self.assertFalse(server.public_image_url('http://user:pass@example.com/logo.png'))
        self.assertFalse(server.public_image_url('http://169.254.169.254/a'))


if __name__ == '__main__':
    unittest.main()

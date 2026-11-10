import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from anistream import backend

class SourceTests(unittest.TestCase):
    @patch('anistream.backend.fetch')
    def test_playback_sources_exclude_downloads(self, fetch):
        fetch.return_value = b'embeds:{SUB:[{server:"Voe",url:"https://voe.sx/e/a"}]},downloads:{SUB:[{server:"MP4Upload",url:"https://www.mp4upload.com/not-embed"}]}'
        self.assertEqual(backend.sources({'path':'/media/test'}, 1), [{'name':'Voe','embed':'https://voe.sx/e/a'}])

    @patch('anistream.backend.fetch')
    def test_missing_sources_is_explicit(self, fetch):
        fetch.return_value = b'<html>Unavailable</html>'
        with self.assertRaisesRegex(RuntimeError, 'servidores'):
            backend.sources({'path':'/media/test'}, 1)

    @patch('anistream.backend.fetch')
    def test_ad_script_is_not_video(self, fetch):
        fetch.return_value = b'<script src="https://ads.example/script.js"></script>'
        with self.assertRaisesRegex(RuntimeError, 'enlace de v'):
            backend.resolve({'name':'MP4Upload','embed':'https://www.mp4upload.com/embed-test.html'})

    @patch('anistream.backend.sources')
    @patch('anistream.backend.resolve')
    def test_failed_host_uses_alternative(self, resolve, sources):
        sources.return_value = [{'name':'MP4Upload'}, {'name':'Voe'}]
        resolve.side_effect = [RuntimeError('Unavailable'), {'url':'https://video.example/master.m3u8'}]
        self.assertEqual(backend.stream({'path':'/media/test'},1),'https://video.example/master.m3u8')
        self.assertEqual(resolve.call_count, 2)

if __name__ == '__main__': unittest.main()

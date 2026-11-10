import json
from pathlib import Path
import tempfile
import unittest
from anistream.library import Library

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'library.json'
        self.library = Library(self.path)

    def test_existing_library_keeps_history_and_adds_missing_sections(self):
        self.path.write_text(json.dumps({'history': {'/media/example': {'episode': 3}}}))
        state = self.library.load()
        self.assertEqual(state['history']['/media/example']['episode'], 3)
        self.assertEqual(state['favorites'], {})
        self.assertEqual(state['positions'], {})

    def test_invalid_library_is_preserved(self):
        self.path.write_text('broken json')
        with self.assertLogs(level='ERROR'):
            self.assertEqual(self.library.load()['favorites'], {})
        self.assertEqual(self.path.with_suffix('.json.invalid').read_text(), 'broken json')

    def test_failed_write_preserves_previous_state(self):
        self.library.save({'favorites': {'example': 'original'}})
        with self.assertRaises(ValueError):
            self.library.save({'position': float('nan')})
        self.assertEqual(self.library.load()['favorites']['example'], 'original')
        self.assertEqual(list(self.path.parent.glob('.library-*')), [])

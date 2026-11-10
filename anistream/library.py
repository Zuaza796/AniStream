"""Persistence of favorites, history and playback positions (no media URLs)."""
import json
import logging
import os
from pathlib import Path
import tempfile
import uuid

KEYS = ('favorites', 'history', 'positions', 'durations')

class Library:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        state = {}
        try:
            state = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(state, dict): raise ValueError('Library must be an object')
            if any(k in state and not isinstance(state[k], dict) for k in KEYS):
                raise ValueError('Library sections must be objects')
        except FileNotFoundError:
            pass
        except (ValueError, UnicodeError):
            logging.exception('Invalid library; preserving original as library.json.invalid')
            backup = self.path.with_suffix('.json.invalid')
            if backup.exists(): backup = backup.with_name(backup.name + '.' + uuid.uuid4().hex)
            self.path.replace(backup)
            state = {}
        for key in KEYS: state.setdefault(key, {})
        return state

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Unique temporary file on the same filesystem, then atomic replacement.
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent, prefix='.library-', delete=False) as f:
                name = f.name
                json.dump(state, f, ensure_ascii=False, allow_nan=False)
                f.flush(); os.fsync(f.fileno())
            os.replace(name, self.path)
        finally:
            if name and os.path.exists(name): os.unlink(name)
